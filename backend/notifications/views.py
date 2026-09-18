from rest_framework import views, permissions
from rest_framework.response import Response
from .models import EmailLog
from authentication.permissions import IsAdmin

class EmailLogListView(views.APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = EmailLog.objects.select_related('certificate').order_by('-created_at')[:50]
        data = [
            {
                'id': log.id,
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
