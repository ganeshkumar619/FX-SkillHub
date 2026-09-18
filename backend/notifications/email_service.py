import hashlib
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from .models import EmailLog


class EmailNotificationService:
    @classmethod
    def send_certificate_notification(cls, certificate):
        """
        Dispatches certificate completion email with PDF attachment and idempotency protection.
        Subject format: "Your FX SkillHub Certificate — [COURSE NAME]"
        """
        recipient = certificate.student.email
        if not recipient:
            return None

        idempotency_key = hashlib.md5(f"cert_email_{certificate.id}".encode('utf-8')).hexdigest()
        
        # Idempotency check: avoid double sends
        existing_log = EmailLog.objects.filter(idempotency_key=idempotency_key).first()
        if existing_log and existing_log.status == 'SENT':
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

            email = EmailMessage(
                subject=subject,
                body=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient]
            )
            email.attach(
                filename=f"FXEC_Certificate_{certificate.certificate_number}.pdf",
                content=pdf_bytes,
                mimetype="application/pdf"
            )
            email.send(fail_silently=False)

            email_log.status = 'SENT'
            email_log.sent_at = timezone.now()
            email_log.save(update_fields=['status', 'sent_at'])
        except Exception as e:
            email_log.status = 'FAILED'
            email_log.error_message = str(e)
            email_log.save(update_fields=['status', 'error_message'])

        return email_log

    @classmethod
    def send_otp_verification_email(cls, email: str, otp_plain: str, student_name: str = "Student"):
        """
        Dispatches time-limited 6-digit OTP to student's institutional mailbox.
        Also tracks delivery status in EmailLog and console output for verification.
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

        # Print OTP to server console for instant verification/debugging
        print(f"\n=======================================================")
        print(f" [FX SKILLHUB OTP VERIFICATION DISPATCH]")
        print(f" Recipient: {email}")
        print(f" Verification Code: {otp_plain}")
        print(f" Timestamp: {timezone.now().isoformat()}")
        print(f"=======================================================\n")

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
            email_msg = EmailMessage(
                subject=subject,
                body=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            email_msg.send(fail_silently=False)
            if email_log:
                email_log.status = 'SENT'
                email_log.sent_at = timezone.now()
                email_log.save(update_fields=['status', 'sent_at'])
            return True
        except Exception as e:
            err_str = str(e)
            if email_log:
                email_log.status = 'FAILED'
                email_log.error_message = err_str
                email_log.save(update_fields=['status', 'error_message'])
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to dispatch OTP email to {email}: {err_str}")
            return False
