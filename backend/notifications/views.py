from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.conf import settings
from .models import EmailLog
from .email_service import EmailNotificationService
from authentication.permissions import IsAdmin


class EmailLogListView(views.APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = EmailLog.objects.select_related('certificate').order_by('-created_at')[:50]
        data = [
            {
                'id': str(log.id),
                'recipient_email': log.recipient_email,
                'subject': log.subject,
                'certificate_number': log.certificate.certificate_number if log.certificate else None,
                'status': log.status,
                'sent_at': log.sent_at,
                'error_message': log.error_message,
                'created_at': log.created_at,
            }
            for log in logs
        ]
        return Response(data)

    def delete(self, request, pk=None):
        log_id = pk or request.data.get('id')
        if log_id:
            EmailLog.objects.filter(id=log_id).delete()
            return Response({'message': f"Notification log #{log_id} deleted."}, status=200)
        else:
            count = EmailLog.objects.count()
            EmailLog.objects.all().delete()
            return Response({'message': f"All {count} notification logs cleared."}, status=200)


class EmailStatusDiagnosticsView(views.APIView):
    """
    Publicly verifiable, read-only diagnostic view that reports SMTP configuration
    and live connectivity status. Never reveals secrets or passwords.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        diag = EmailNotificationService.test_smtp_connection()
        user_configured = bool(getattr(settings, 'EMAIL_HOST_USER', ''))
        password_configured = bool(getattr(settings, 'EMAIL_HOST_PASSWORD', ''))

        recommendations = []
        if not user_configured or not password_configured:
            recommendations.append("Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in Render environment variables.")
        if diag.get('error_stage') == 'CONNECTION':
            recommendations.append("Outbound connection to SMTP server failed/timed out. Ensure port 587 is accessible from the container.")
        elif diag.get('error_stage') == 'AUTHENTICATION':
            recommendations.append("SMTP Authentication failed. For Gmail, use an active 16-character App Password without spaces.")

        return Response({
            'status': 'healthy' if (diag.get('connected') and diag.get('authenticated')) else 'degraded',
            'email_backend': diag.get('backend'),
            'email_host': diag.get('host'),
            'email_port': diag.get('port'),
            'email_use_tls': diag.get('use_tls'),
            'email_use_ssl': diag.get('use_ssl'),
            'email_timeout_sec': getattr(settings, 'EMAIL_TIMEOUT', 10),
            'email_host_user_configured': user_configured,
            'email_host_password_configured': password_configured,
            'default_from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            'frontend_url': getattr(settings, 'FRONTEND_URL', ''),
            'smtp_socket_connected': diag.get('connected', False),
            'smtp_authenticated': diag.get('authenticated', False),
            'error_stage': diag.get('error_stage'),
            'error_type': diag.get('error_type'),
            'error_message': diag.get('error_message'),
            'latency_ms': diag.get('latency_ms'),
            'recommendations': recommendations
        }, status=status.HTTP_200_OK)


class EmailTestDispatchView(views.APIView):
    """
    Admin-protected endpoint to dispatch a real diagnostic email to a specified recipient.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        recipient = request.data.get('recipient')
        if not recipient:
            recipient = request.user.email or getattr(settings, 'EMAIL_HOST_USER', '')

        report = EmailNotificationService.send_test_email(recipient=recipient)
        http_status = status.HTTP_200_OK if report.get('send_success') else status.HTTP_502_BAD_GATEWAY

        return Response({
            'success': report.get('send_success', False),
            'report': report
        }, status=http_status)
