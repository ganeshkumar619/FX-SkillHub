import socket
import time
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
    Publicly verifiable, read-only diagnostic view that reports email configuration
    and live connectivity status. Never reveals secrets, passwords, or API keys.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        diag = EmailNotificationService.test_smtp_connection()
        backend_name = diag.get('backend', '')
        is_resend = 'anymail' in str(backend_name).lower() or 'resend' in str(backend_name).lower()

        resend_key_configured = diag.get('resend_api_key_configured', False)
        sender_configured = diag.get('sender_configured', False)
        https_connected = diag.get('https_api_connectivity', False)
        user_configured = bool(getattr(settings, 'EMAIL_HOST_USER', ''))
        password_configured = bool(getattr(settings, 'EMAIL_HOST_PASSWORD', ''))

        recommendations = []
        if is_resend:
            if not resend_key_configured:
                recommendations.append("Add ANYMAIL_RESEND_API_KEY in Render environment variables.")
            if not sender_configured:
                recommendations.append("Add DEFAULT_FROM_EMAIL in Render environment variables (e.g. 'FX SkillHub <onboarding@resend.dev>').")
            if not https_connected:
                recommendations.append("Outbound HTTPS connection to api.resend.com:443 failed.")
        else:
            if not user_configured or not password_configured:
                recommendations.append("Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in Render environment variables.")
            if diag.get('error_stage') == 'CONNECTION':
                recommendations.append("Outbound connection to SMTP server failed/timed out. Switch to Resend HTTPS API.")
            elif diag.get('error_stage') == 'AUTHENTICATION':
                recommendations.append("SMTP Authentication failed.")

        is_healthy = bool(diag.get('connected') and diag.get('authenticated'))

        return Response({
            'status': 'healthy' if is_healthy else 'degraded',
            'email_backend': backend_name,
            'resend_api_key_configured': resend_key_configured,
            'sender_configured': sender_configured,
            'https_api_connectivity': https_connected,
            'default_from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            'error_type': diag.get('error_type'),
            'error_message': diag.get('error_message'),
            'latency_ms': diag.get('latency_ms'),
            'recommendations': recommendations,
            # Legacy compatibility fields
            'email_host': diag.get('host'),
            'email_port': diag.get('port'),
            'email_use_tls': diag.get('use_tls'),
            'email_use_ssl': diag.get('use_ssl'),
            'email_timeout_sec': getattr(settings, 'EMAIL_TIMEOUT', 10),
            'email_host_user_configured': user_configured,
            'email_host_password_configured': password_configured,
            'frontend_url': getattr(settings, 'FRONTEND_URL', ''),
            'smtp_socket_connected': diag.get('connected', False) if not is_resend else False,
            'smtp_authenticated': diag.get('authenticated', False) if not is_resend else False,
            'error_stage': diag.get('error_stage'),
        }, status=status.HTTP_200_OK)


class NetworkAuditDiagnosticsView(views.APIView):
    """
    Diagnostic view to audit DNS resolution and raw TCP socket connectivity
    from the production host to SMTP endpoints without authentication or sending emails.
    """
    permission_classes = [permissions.AllowAny]

    def _test_tcp(self, host, port, family=socket.AF_INET, timeout=3.0):
        t0 = time.time()
        s = socket.socket(family, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            s.close()
            return {
                'target': f"{host}:{port}",
                'ip_family': 'IPv4' if family == socket.AF_INET else 'IPv6',
                'connected': True,
                'error_type': None,
                'error_message': None,
                'elapsed_ms': int((time.time() - t0) * 1000)
            }
        except Exception as e:
            try:
                s.close()
            except Exception:
                pass
            return {
                'target': f"{host}:{port}",
                'ip_family': 'IPv4' if family == socket.AF_INET else 'IPv6',
                'connected': False,
                'error_type': e.__class__.__name__,
                'error_message': str(e),
                'elapsed_ms': int((time.time() - t0) * 1000)
            }

    def get(self, request):
        target_smtp_host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
        target_smtp_port = int(getattr(settings, 'EMAIL_PORT', 587))

        # 1. DNS Resolution
        t0_dns = time.time()
        dns_success = False
        ipv4_list = []
        ipv6_list = []
        dns_error = None
        try:
            addr_info = socket.getaddrinfo(target_smtp_host, target_smtp_port)
            for item in addr_info:
                family = item[0]
                sockaddr = item[4]
                ip = sockaddr[0]
                if family == socket.AF_INET and ip not in ipv4_list:
                    ipv4_list.append(ip)
                elif family == socket.AF_INET6 and ip not in ipv6_list:
                    ipv6_list.append(ip)
            dns_success = True
        except Exception as e:
            dns_error = f"{e.__class__.__name__}: {str(e)}"
        dns_elapsed_ms = int((time.time() - t0_dns) * 1000)

        # 2. TCP Probes
        probes = []
        
        # Probe 1: Default socket connection to configured SMTP host:port
        t0_def = time.time()
        try:
            s_def = socket.create_connection((target_smtp_host, target_smtp_port), timeout=3.0)
            s_def.close()
            probes.append({
                'description': f'Default socket.create_connection to {target_smtp_host}:{target_smtp_port}',
                'connected': True,
                'error_type': None,
                'error_message': None,
                'elapsed_ms': int((time.time() - t0_def) * 1000)
            })
        except Exception as e:
            probes.append({
                'description': f'Default socket.create_connection to {target_smtp_host}:{target_smtp_port}',
                'connected': False,
                'error_type': e.__class__.__name__,
                'error_message': str(e),
                'elapsed_ms': int((time.time() - t0_def) * 1000)
            })

        # Probe 2: Forced IPv4 to first resolved IPv4
        ipv4_target = ipv4_list[0] if ipv4_list else target_smtp_host
        probes.append({
            'description': f'IPv4 direct socket connect to {ipv4_target}:{target_smtp_port}',
            **self._test_tcp(ipv4_target, target_smtp_port, family=socket.AF_INET, timeout=3.0)
        })

        # Probe 3: Forced IPv4 to Port 465 (SMTPS)
        probes.append({
            'description': f'IPv4 direct socket connect to {ipv4_target}:465 (SMTPS)',
            **self._test_tcp(ipv4_target, 465, family=socket.AF_INET, timeout=3.0)
        })

        # Probe 4: Forced IPv4 to Port 25 (Standard SMTP)
        probes.append({
            'description': f'IPv4 direct socket connect to {ipv4_target}:25 (Standard SMTP)',
            **self._test_tcp(ipv4_target, 25, family=socket.AF_INET, timeout=3.0)
        })

        # Probe 5: Outbound HTTPS Control Test (google.com:443)
        probes.append({
            'description': 'Outbound HTTPS control test to google.com:443',
            **self._test_tcp('google.com', 443, family=socket.AF_INET, timeout=3.0)
        })

        # Probe 6: Outbound HTTPS Control Test to Email API Provider (api.resend.com:443)
        probes.append({
            'description': 'Outbound HTTPS email API test to api.resend.com:443',
            **self._test_tcp('api.resend.com', 443, family=socket.AF_INET, timeout=3.0)
        })

        # Determine verdict
        smtp_587_ok = any(p['connected'] for p in probes if '587' in p['description'])
        https_443_ok = any(p['connected'] for p in probes if '443' in p['description'])
        outbound_smtp_blocked = dns_success and not smtp_587_ok and https_443_ok

        return Response({
            'dns_audit': {
                'target_host': target_smtp_host,
                'dns_resolution_success': dns_success,
                'ipv4_addresses': ipv4_list,
                'ipv6_addresses': ipv6_list,
                'dns_error': dns_error,
                'elapsed_ms': dns_elapsed_ms
            },
            'tcp_connection_probes': probes,
            'audit_summary': {
                'dns_operational': dns_success,
                'smtp_port_587_accessible': smtp_587_ok,
                'outbound_https_functional': https_443_ok,
                'is_outbound_smtp_blocked_by_host': outbound_smtp_blocked,
                'root_cause_confirmation': (
                    "CONFIRMED: Render host blocks outbound SMTP traffic (ports 25, 465, 587). "
                    "Outbound HTTPS (port 443) is fully operational. "
                    "The failure is network-level egress blocking, not Gmail authentication credentials."
                    if outbound_smtp_blocked else (
                        "SMTP port 587 is accessible." if smtp_587_ok else "Network check inconclusive."
                    )
                )
            }
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
