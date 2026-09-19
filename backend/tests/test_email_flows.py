import pytest
import re
from datetime import timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APIClient
from authentication.models import EmailVerificationOTP, FacultyInvitation
from catalogue.models import Department, Course
from learning.models import Enrollment
from certificates.models import Certificate
from notifications.email_service import EmailNotificationService
from notifications.models import EmailLog
from authentication.authentication import generate_jwt_token

User = get_user_model()


@pytest.mark.django_db
class TestCompleteEmailFlows:
    def setup_method(self):
        self.client = APIClient()
        mail.outbox = []

        self.dept, _ = Department.objects.get_or_create(
            code='CSE',
            defaults={
                'name': 'Computer Science and Engineering',
                'is_active': True
            }
        )

        self.admin = User.objects.create_user(
            username='admin_user',
            email='admin@fxec.ac.in',
            password='AdminPassword123!',
            role='ADMIN',
            is_staff=True,
            is_superuser=True
        )

    # =========================================================================
    # 1. Student Registration OTP Email Flow
    # =========================================================================
    def test_student_registration_email_dispatch_and_outbox(self):
        reg_url = reverse('register')
        payload = {
            'name': 'Karthik Raja',
            'email': 'karthik.r@francisxavier.ac.in',
            'register_number': '951322104888',
            'department': self.dept.id,
            'year': 2,
            'password': 'StrongPassword123!'
        }
        res = self.client.post(reg_url, payload, format='json')
        assert res.status_code == 201
        assert res.data['status'] == 'PENDING_EMAIL_VERIFICATION'
        assert res.data['email_sent'] is True
        assert 'dispatched' in res.data['message'].lower()

        # Verify email in outbox
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert sent_email.to == ['karthik.r@francisxavier.ac.in']
        assert 'Institutional Email Verification Code' in sent_email.subject
        assert 'VERIFICATION CODE:' in sent_email.body

        # Verify EmailLog
        log = EmailLog.objects.filter(recipient_email='karthik.r@francisxavier.ac.in').first()
        assert log is not None
        assert log.status == 'SENT'

    def test_student_registration_email_failure_handling(self, monkeypatch):
        # Simulate SMTP failure
        def mock_send(*args, **kwargs):
            raise ConnectionRefusedError("Simulated SMTP network failure")

        monkeypatch.setattr(
            'notifications.email_service.EmailNotificationService.send_otp_verification_email',
            lambda **kw: False
        )

        reg_url = reverse('register')
        payload = {
            'name': 'Sanjay V',
            'email': 'sanjay.v@francisxavier.ac.in',
            'register_number': '951322104889',
            'department': self.dept.id,
            'year': 3,
            'password': 'StrongPassword123!'
        }
        res = self.client.post(reg_url, payload, format='json')
        assert res.status_code == 201
        assert res.data['email_sent'] is False
        assert 'could not be delivered' in res.data['message'].lower()

        # User account is created in pending state, not lost
        user = User.objects.get(email='sanjay.v@francisxavier.ac.in')
        assert user.is_active is False
        assert user.verification_status == 'PENDING_EMAIL_VERIFICATION'

    # =========================================================================
    # 2. Resend OTP Email Flow
    # =========================================================================
    def test_resend_otp_email_dispatch(self):
        reg_url = reverse('register')
        self.client.post(reg_url, {
            'name': 'Divya S',
            'email': 'divya.s@francisxavier.ac.in',
            'register_number': '951322104890',
            'department': self.dept.id,
            'year': 1,
            'password': 'StrongPassword123!'
        }, format='json')
        assert len(mail.outbox) == 1

        # Simulate 65s elapsed for cooldown
        otp_rec = EmailVerificationOTP.objects.get(email='divya.s@francisxavier.ac.in', is_used=False)
        otp_rec.last_resend_at = timezone.now() - timedelta(seconds=65)
        otp_rec.save(update_fields=['last_resend_at'])

        resend_url = reverse('resend_otp')
        res = self.client.post(resend_url, {'email': 'divya.s@francisxavier.ac.in'}, format='json')
        assert res.status_code == 200
        assert res.data['email_sent'] is True
        assert len(mail.outbox) == 2

    # =========================================================================
    # 3. Faculty Invitation & Production URL Check
    # =========================================================================
    @override_settings(
        FRONTEND_URL='https://fx-skillhub-frontend.onrender.com',
        DEBUG=False
    )
    def test_faculty_invitation_email_uses_production_frontend_url(self):
        token = generate_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        url = reverse('admin_faculty_list')
        payload = {
            'faculty_name': 'Dr. Ramanathan',
            'email': 'ramanathan.fac@example.com',
            'faculty_id': 'FX-FAC-2026',
            'department': self.dept.id,
            'phone': '+91 9876500000',
            'is_active': True
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == 201
        assert res.data['email_sent'] is True

        # Check outbox email content
        assert len(mail.outbox) == 1
        invite_email = mail.outbox[0]
        assert invite_email.to == ['ramanathan.fac@example.com']
        assert 'Faculty Account Created' in invite_email.subject

        # Invariant: Must use production frontend URL, NEVER localhost
        assert 'https://fx-skillhub-frontend.onrender.com/activate-faculty/' in invite_email.body
        assert 'http://localhost' not in invite_email.body
        assert '127.0.0.1' not in invite_email.body

    def test_faculty_resend_invitation(self):
        token = generate_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Create faculty
        fac_user = User.objects.create_user(
            username='fac_resend',
            email='resend.fac@example.com',
            role='FACULTY',
            department=self.dept,
            is_active=False
        )
        url = reverse('admin_faculty_resend_invitation', kwargs={'pk': fac_user.id})
        res = self.client.post(url)
        assert res.status_code == 200
        assert res.data['email_sent'] is True
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ['resend.fac@example.com']

    # =========================================================================
    # 4. Certificate Email Flow
    # =========================================================================
    def test_certificate_email_generation_and_idempotency(self):
        student = User.objects.create_user(
            username='cert_student',
            email='cert.student@francisxavier.ac.in',
            password='Password123!',
            role='STUDENT',
            department=self.dept
        )
        from catalogue.models import SkillCategory, Skill
        category, _ = SkillCategory.objects.get_or_create(name='Cloud Computing')
        skill, _ = Skill.objects.get_or_create(
            name='Cloud Architecture',
            defaults={'category': category, 'department': self.dept}
        )
        course, _ = Course.objects.get_or_create(
            slug='advanced-cloud-architecture',
            defaults={
                'title': 'Advanced Cloud Architecture',
                'skill': skill,
                'department': self.dept,
                'created_by': self.admin,
                'description': 'Advanced cloud course'
            }
        )
        enrollment = Enrollment.objects.create(
            student=student,
            course=course,
            is_completed=True,
            completed_at=timezone.now()
        )

        cert = Certificate.objects.create(
            enrollment=enrollment,
            student=student,
            course=course,
            certificate_number='FXEC-2026-000101',
            integrity_hash='a'*64,
            qr_url='https://fx-skillhub-frontend.onrender.com/verify/FXEC-2026-000101',
            skill='Cloud Engineering',
            assessment_score='95 / 100',
            status='VALID'
        )

        # Dispatch certificate email
        log = EmailNotificationService.send_certificate_notification(cert)
        assert log is not None
        assert log.status == 'SENT'
        assert len(mail.outbox) == 1
        cert_email = mail.outbox[0]
        assert cert_email.to == ['cert.student@francisxavier.ac.in']
        assert 'Advanced Cloud Architecture' in cert_email.subject
        assert len(cert_email.attachments) == 1
        assert cert_email.attachments[0][0] == 'FXEC_Certificate_FXEC-2026-000101.pdf'

        # Idempotency test: duplicate call should NOT dispatch another email
        log_duplicate = EmailNotificationService.send_certificate_notification(cert)
        assert log_duplicate.id == log.id
        assert len(mail.outbox) == 1  # No duplicate send!

    # =========================================================================
    # 5. Diagnostic Email Status & Network Audit API
    # =========================================================================
    def test_email_status_diagnostic_endpoint(self):
        url = reverse('email_status_diagnostics')
        res = self.client.get(url)
        assert res.status_code == 200
        assert 'email_backend' in res.data
        assert 'resend_api_key_configured' in res.data
        assert 'sender_configured' in res.data
        assert 'https_api_connectivity' in res.data
        assert 'default_from_email' in res.data
        assert 'frontend_url' in res.data
        # Ensure passwords and secret keys are NOT exposed
        assert 'EMAIL_HOST_PASSWORD' not in res.data
        assert 'password' not in res.data
        assert 'RESEND_API_KEY' not in res.data

    @override_settings(
        EMAIL_BACKEND='anymail.backends.resend.EmailBackend',
        ANYMAIL={'RESEND_API_KEY': 're_secret_key_testing_12345'},
        DEFAULT_FROM_EMAIL='FX SkillHub <onboarding@resend.dev>'
    )
    def test_resend_status_configuration_and_key_masking(self):
        url = reverse('email_status_diagnostics')
        res = self.client.get(url)
        assert res.status_code == 200
        assert res.data['email_backend'] == 'anymail.backends.resend.EmailBackend'
        assert res.data['resend_api_key_configured'] is True
        assert res.data['sender_configured'] is True
        assert res.data['default_from_email'] == 'FX SkillHub <onboarding@resend.dev>'
        # Invariant: Secret key must NEVER appear in response
        assert 're_secret_key_testing_12345' not in str(res.data)
        assert 'secret' not in str(res.data).lower()

    def test_network_audit_diagnostic_endpoint(self):
        url = reverse('email_network_audit')
        res = self.client.get(url)
        assert res.status_code == 200
        assert 'dns_audit' in res.data
        assert 'tcp_connection_probes' in res.data
        assert 'audit_summary' in res.data
        assert res.data['dns_audit']['dns_resolution_success'] is True
        assert len(res.data['tcp_connection_probes']) >= 5
        # Ensure no passwords or credentials exposed
        assert 'EMAIL_HOST_PASSWORD' not in res.data
        assert 'password' not in str(res.data).lower()

    def test_admin_test_email_dispatch_endpoint(self, monkeypatch):
        token = generate_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        monkeypatch.setattr(
            'notifications.email_service.EmailNotificationService.send_test_email',
            lambda recipient: {
                'send_success': True,
                'backend': 'anymail.backends.resend.EmailBackend',
                'recipient': recipient,
                'total_latency_ms': 120
            }
        )

        url = reverse('email_test_dispatch')
        res = self.client.post(url, {'recipient': 'admin@fxec.ac.in'}, format='json')
        assert res.status_code == 200
        assert res.data['success'] is True
        assert res.data['report']['backend'] == 'anymail.backends.resend.EmailBackend'

