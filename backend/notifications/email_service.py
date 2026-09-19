import time
import hashlib
import logging
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from django.utils import timezone
from .models import EmailLog

logger = logging.getLogger(__name__)


class EmailNotificationService:
    @classmethod
    def send_certificate_notification(cls, certificate, force: bool = False):
        """
        Dispatches certificate completion email with PDF attachment and idempotency protection.
        Subject format: "Your FX SkillHub Certificate — [COURSE NAME]"
        """
        recipient = certificate.student.email
        if not recipient:
            return None

        idempotency_key = hashlib.md5(f"cert_email_{certificate.id}".encode('utf-8')).hexdigest()
        
        # Idempotency check: avoid double sends unless forced
        existing_log = EmailLog.objects.filter(idempotency_key=idempotency_key).first()
        if existing_log and existing_log.status == 'SENT' and not force:
            return existing_log

        subject = f"Your FX SkillHub Certificate — {certificate.course.title}"
        student_name = certificate.student.get_full_name() or certificate.student.username
        
        message_body = (
            f"Dear {student_name},\n\n"
            f"Congratulations on successfully completing the course '{certificate.course.title}' "
            f"and passing the final assessment at Francis Xavier Engineering College (Autonomous).\n\n"
            f"Your verified digital institutional credential has been generated and is attached to this email.\n\n"
            f"Certificate ID: {certificate.certificate_number}\n"
            f"Course: {certificate.course.title}\n"
            f"Skill: {certificate.skill or 'Engineering Skill'}\n"
            f"Score: {certificate.assessment_score or 'Passed'}\n"
            f"Verification Link: {certificate.qr_url}\n"
            f"Integrity SHA-256 Digest: {certificate.integrity_hash}\n\n"
            f"You can verify this certificate online at any time by scanning the embedded QR code or visiting the verification link above.\n\n"
            f"Warm regards,\n"
            f"Centre for Training and Skills Development\n"
            f"Francis Xavier Engineering College, Tirunelveli"
        )

        email_log = existing_log
        if not email_log:
            email_log, _ = EmailLog.objects.get_or_create(
                idempotency_key=idempotency_key,
                defaults={
                    'recipient_email': recipient,
                    'subject': subject,
                    'certificate': certificate,
                    'status': 'PENDING'
                }
            )

        try:
            from certificates.pdf_service import CertificatePDFService
            pdf_bytes = CertificatePDFService.render_pdf(certificate)

            timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)
            connection = get_connection(timeout=timeout)

            email = EmailMessage(
                subject=subject,
                body=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                connection=connection
            )
            email.attach(
                filename=f"FXEC_Certificate_{certificate.certificate_number}.pdf",
                content=pdf_bytes,
                mimetype="application/pdf"
            )
            email.send(fail_silently=False)

            email_log.status = 'SENT'
            email_log.sent_at = timezone.now()
            email_log.error_message = None
            email_log.save(update_fields=['status', 'sent_at', 'error_message'])
            logger.info(f"Certificate email successfully dispatched to {recipient} for {certificate.certificate_number}")
        except Exception as e:
            err_str = str(e)
            email_log.status = 'FAILED'
            email_log.error_message = err_str
            email_log.save(update_fields=['status', 'error_message'])
            logger.error(f"Failed to dispatch certificate email to {recipient}: {err_str}")

        return email_log

    @classmethod
    def send_otp_verification_email(cls, email: str, otp_plain: str, student_name: str = "Student") -> bool:
        """
        Dispatches time-limited 6-digit OTP to student's institutional mailbox.
        Tracks delivery status in EmailLog. Plaintext OTP is NEVER logged.
        """
        if not email:
            return False

        subject = "FX SkillHub — Institutional Email Verification Code"
        
        message_body = (
            f"Dear {student_name},\n\n"
            f"Welcome to FX SkillHub at Francis Xavier Engineering College (Autonomous), Tirunelveli.\n\n"
            f"To verify that you own this official institutional email account, please enter the "
            f"one-time verification code below in your registration screen:\n\n"
            f"    VERIFICATION CODE: {otp_plain}\n\n"
            f"This code will expire in 10 minutes.\n\n"
            f"SECURITY NOTICE:\n"
            f"• Never share this verification code with anyone.\n"
            f"• College staff and mentors will NEVER ask for your code or password.\n"
            f"• If you did not request this verification code, please ignore this email.\n\n"
            f"Warm regards,\n"
            f"Centre for Training and Skills Development\n"
            f"Francis Xavier Engineering College (Autonomous)\n"
            f"Tirunelveli - 627 003, Tamil Nadu"
        )

        logger.info(f"Initiating OTP verification email dispatch to recipient: {email}")

        idempotency_key = hashlib.md5(f"otp_{email}_{timezone.now().timestamp()}_{otp_plain}".encode('utf-8')).hexdigest()
        email_log = None
        try:
            email_log = EmailLog.objects.create(
                idempotency_key=idempotency_key,
                recipient_email=email,
                subject=subject,
                status='PENDING'
            )
        except Exception:
            pass

        try:
            timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)
            connection = get_connection(timeout=timeout)
            email_msg = EmailMessage(
                subject=subject,
                body=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
                connection=connection
            )
            email_msg.send(fail_silently=False)
            if email_log:
                email_log.status = 'SENT'
                email_log.sent_at = timezone.now()
                email_log.error_message = None
                email_log.save(update_fields=['status', 'sent_at', 'error_message'])
            logger.info(f"OTP verification email successfully dispatched to {email}")
            return True
        except Exception as e:
            err_str = str(e)
            if email_log:
                email_log.status = 'FAILED'
                email_log.error_message = err_str
                email_log.save(update_fields=['status', 'error_message'])
            logger.error(f"Failed to dispatch OTP email to {email}: {err_str}")
            return False

    @classmethod
    def send_faculty_invitation_email(
        cls,
        email: str,
        faculty_name: str,
        faculty_id: str,
        activation_url: str,
        login_url: str
    ) -> bool:
        """
        Dispatches account activation invitation to the provisioned Faculty email address.
        Tracks delivery in EmailLog. Tokens are NEVER logged.
        """
        if not email:
            return False

        subject = "FX SkillHub – Faculty Account Created"
        fac_id_display = faculty_id or "Assigned by Admin"

        message_body = (
            f"Dear {faculty_name},\n\n"
            f"Your Faculty account has been successfully created on FX SkillHub\n"
            f"by the administrator.\n\n"
            f"Institution:\n"
            f"Francis Xavier Engineering College\n\n"
            f"Role:\n"
            f"Faculty\n\n"
            f"Registered Email:\n"
            f"{email}\n\n"
            f"Faculty ID:\n"
            f"{fac_id_display}\n\n"
            f"You can now activate your Faculty account using the secure link below:\n\n"
            f"{activation_url}\n\n"
            f"After activation, you can access:\n\n"
            f"{login_url}\n\n"
            f"Regards,\n"
            f"FX SkillHub\n"
            f"Francis Xavier Engineering College"
        )

        logger.info(f"Initiating Faculty invitation dispatch to recipient: {email}")

        idempotency_key = hashlib.md5(
            f"fac_invite_{email}_{timezone.now().timestamp()}".encode('utf-8')
        ).hexdigest()

        email_log = None
        try:
            email_log = EmailLog.objects.create(
                idempotency_key=idempotency_key,
                recipient_email=email,
                subject=subject,
                status='PENDING'
            )
        except Exception:
            pass

        try:
            timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)
            connection = get_connection(timeout=timeout)
            email_msg = EmailMessage(
                subject=subject,
                body=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
                connection=connection
            )
            email_msg.send(fail_silently=False)
            if email_log:
                email_log.status = 'SENT'
                email_log.sent_at = timezone.now()
                email_log.error_message = None
                email_log.save(update_fields=['status', 'sent_at', 'error_message'])
            logger.info(f"Faculty invitation email successfully dispatched to {email}")
            return True
        except Exception as e:
            err_str = str(e)
            if email_log:
                email_log.status = 'FAILED'
                email_log.error_message = err_str
                email_log.save(update_fields=['status', 'error_message'])
            logger.error(f"Failed to dispatch Faculty invitation email to {email}: {err_str}")
            return False

    @classmethod
    def test_smtp_connection(cls) -> dict:
        """
        Tests the connectivity and configuration of the active email backend.
        Supports both Anymail Resend (HTTPS port 443) and legacy SMTP.
        Never reveals secret API keys or passwords.
        """
        import socket
        start_time = time.time()
        backend_name = getattr(settings, 'EMAIL_BACKEND', '')
        is_resend = 'anymail' in backend_name.lower() or 'resend' in backend_name.lower()
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)
        
        host = getattr(settings, 'EMAIL_HOST', 'api.resend.com' if is_resend else 'smtp.gmail.com')
        port = 443 if is_resend else getattr(settings, 'EMAIL_PORT', 587)
        use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        user = getattr(settings, 'EMAIL_HOST_USER', '')
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')

        # Resend API Key check
        resend_key = getattr(settings, 'ANYMAIL', {}).get('RESEND_API_KEY', '') or getattr(settings, 'ANYMAIL_RESEND_API_KEY', '')
        resend_key_configured = bool(str(resend_key).strip())

        result = {
            'backend': backend_name,
            'host': host,
            'port': port,
            'use_tls': use_tls,
            'use_ssl': use_ssl,
            'user_configured': bool(user),
            'password_configured': bool(password),
            'resend_api_key_configured': resend_key_configured,
            'sender_configured': bool(getattr(settings, 'DEFAULT_FROM_EMAIL', '')),
            'https_api_connectivity': False,
            'connected': False,
            'authenticated': False,
            'error_stage': None,
            'error_type': None,
            'error_message': None,
            'latency_ms': None
        }

        # Handling for Resend HTTPS Backend
        if is_resend:
            # 1. Test HTTPS Socket Connectivity to api.resend.com:443
            https_connected = False
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(min(timeout, 3.0))
            try:
                sock.connect(('api.resend.com', 443))
                sock.close()
                https_connected = True
            except Exception as ex:
                try:
                    sock.close()
                except Exception:
                    pass
                result['error_type'] = ex.__class__.__name__
                result['error_message'] = str(ex)

            result['https_api_connectivity'] = https_connected

            # 2. Check API Key configuration
            if not resend_key_configured:
                result['error_stage'] = 'CONFIG'
                result['error_type'] = result['error_type'] or 'MissingApiKey'
                result['error_message'] = 'ANYMAIL_RESEND_API_KEY is not configured in environment.'
                result['connected'] = https_connected
                result['authenticated'] = False
            elif not https_connected:
                result['error_stage'] = 'CONNECTION'
                result['connected'] = False
                result['authenticated'] = False
            else:
                result['connected'] = True
                result['authenticated'] = True
                result['error_stage'] = None
                result['error_type'] = None
                result['error_message'] = None

            result['latency_ms'] = int((time.time() - start_time) * 1000)
            return result

        # Legacy SMTP Backend Check
        if 'smtp' in backend_name.lower():
            if not user or not password:
                result['error_stage'] = 'CONFIG'
                result['error_type'] = 'MissingCredentials'
                result['error_message'] = 'EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is not set in environment.'
                result['latency_ms'] = int((time.time() - start_time) * 1000)
                return result

        try:
            connection = get_connection(timeout=timeout)
            connection.open()
            result['connected'] = True
            result['authenticated'] = bool(getattr(connection, 'connection', None))
            connection.close()
        except Exception as e:
            err_cls = e.__class__.__name__
            err_msg = str(e)
            result['error_type'] = err_cls
            result['error_message'] = err_msg

            if 'auth' in err_cls.lower() or '535' in err_msg:
                result['error_stage'] = 'AUTHENTICATION'
                result['connected'] = True
            elif 'timeout' in err_cls.lower() or 'refused' in err_msg.lower():
                result['error_stage'] = 'CONNECTION'
            else:
                result['error_stage'] = 'UNKNOWN'

        result['latency_ms'] = int((time.time() - start_time) * 1000)
        return result

    @classmethod
    def send_test_email(cls, recipient: str = None) -> dict:
        """
        Dispatches a diagnostic test email to the configured recipient and returns a
        complete execution report. Routes through Resend HTTPS API in production.
        Never exposes secrets or API keys.
        """
        start_time = time.time()
        conn_diag = cls.test_smtp_connection()
        if not conn_diag['connected'] and conn_diag.get('error_stage') == 'CONFIG':
            return {
                **conn_diag,
                'send_success': False,
                'recipient': recipient or getattr(settings, 'EMAIL_HOST_USER', ''),
                'total_latency_ms': conn_diag['latency_ms']
            }

        target = recipient or getattr(settings, 'EMAIL_HOST_USER', '') or getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        if not target:
            target = 'skills@francisxavier.ac.in'

        report = {
            **conn_diag,
            'recipient': target,
            'send_success': False,
        }

        try:
            timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)
            connection = get_connection(timeout=timeout)
            now_iso = timezone.now().isoformat()
            test_msg = EmailMessage(
                subject="FX SkillHub — Email Delivery Diagnostic Test",
                body=(
                    f"This is an automated diagnostic test message from FX SkillHub.\n\n"
                    f"Timestamp: {now_iso}\n"
                    f"Backend: {conn_diag['backend']}\n"
                    f"Transport: HTTPS Port 443 (Resend)\n"
                    f"Sender: {settings.DEFAULT_FROM_EMAIL}\n"
                    f"Recipient: {target}\n\n"
                    f"If you received this message, the FX SkillHub email delivery pipeline is fully operational."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[target],
                connection=connection
            )
            test_msg.send(fail_silently=False)
            report['send_success'] = True
            report['connected'] = True
            report['authenticated'] = True
            report['error_stage'] = None
            report['error_type'] = None
            report['error_message'] = None
        except Exception as e:
            report['send_success'] = False
            report['error_stage'] = report['error_stage'] or 'DISPATCH'
            report['error_type'] = e.__class__.__name__
            report['error_message'] = str(e)

        report['total_latency_ms'] = int((time.time() - start_time) * 1000)
        return report
