import pytest
import re
from datetime import timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from authentication.models import EmailVerificationOTP, ApprovedStudentDirectory
from catalogue.models import Department

User = get_user_model()


@pytest.mark.django_db
class TestStudentEmailOwnershipAndOTPVerification:
    def setup_method(self):
        self.client = APIClient()
        mail.outbox = []

        # Create CSE Department for testing
        self.dept_cse, _ = Department.objects.get_or_create(
            code='CSE',
            defaults={
                'name': 'Computer Science and Engineering',
                'description': 'Department of CSE at FXEC'
            }
        )

    def _extract_otp_from_outbox(self):
        """Helper to extract 6-digit OTP from outbox email body."""
        assert len(mail.outbox) > 0, "No email was dispatched to outbox!"
        latest_email = mail.outbox[-1]
        match = re.search(r'(?:VERIFICATION CODE:\s*|code is:\s*)(\d{6})', latest_email.body)
        assert match, f"Could not find 6-digit OTP in email body:\n{latest_email.body}"
        return match.group(1)

    # =========================================================================
    # 1. Successful student registration initiates OTP and sets PENDING status
    # =========================================================================
    def test_01_student_registration_dispatches_otp_and_sets_pending_status(self):
        reg_url = reverse('register')
        payload = {
            'name': 'Praveen Kumar',
            'email': 'praveen.cs@francisxavier.ac.in',
            'register_number': '951322104010',
            'department': self.dept_cse.id,
            'year': 2,
            'password': 'StudentSecurePass123!'
        }
        res = self.client.post(reg_url, payload, format='json')
        assert res.status_code == 201, res.data
        assert res.data['status'] == 'PENDING_EMAIL_VERIFICATION'
        assert res.data['requires_otp'] is True
        assert res.data['email'] == 'praveen.cs@francisxavier.ac.in'
        # Crucial security invariant: token must NOT be issued before email verification
        assert 'token' not in res.data

        # Verify DB state: User is INACTIVE and PENDING
        user = User.objects.get(email='praveen.cs@francisxavier.ac.in')
        assert user.is_active is False
        assert user.verification_status == 'PENDING_EMAIL_VERIFICATION'
        assert user.role == 'STUDENT'

        # Verify OTP record in DB: exists and is NOT stored in plain text
        otp_record = EmailVerificationOTP.objects.filter(email='praveen.cs@francisxavier.ac.in', is_used=False).first()
        assert otp_record is not None
        assert otp_record.is_expired() is False
        assert not otp_record.otp_hash.isdigit(), "OTP must be cryptographically hashed, not plaintext!"
        assert otp_record.otp_hash.startswith('pbkdf2_')

        # Verify email was sent to the exact institutional mailbox
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ['praveen.cs@francisxavier.ac.in']
        assert 'francisxavier.ac.in' in mail.outbox[0].to[0]

    # =========================================================================
    # 2. Unverified student cannot login
    # =========================================================================
    def test_02_unverified_student_cannot_login(self):
        reg_url = reverse('register')
        payload = {
            'name': 'Meena Kumari',
            'email': 'meena.it@francisxavier.ac.in',
            'register_number': '951322104011',
            'department': self.dept_cse.id,
            'year': 1,
            'password': 'Password123!'
        }
        self.client.post(reg_url, payload, format='json')

        # Attempt to log in with correct email & password
        login_url = reverse('login')
        res_login = self.client.post(login_url, {
            'username': 'meena.it@francisxavier.ac.in',
            'password': 'Password123!'
        })
        assert res_login.status_code == 400
        # Exact message required by institutional specification
        assert 'Please verify your institutional email first.' in str(res_login.data)

    # =========================================================================
    # 3. Wrong password rejected on login
    # =========================================================================
    def test_03_login_wrong_password_rejected(self):
        # Create verified student
        user = User.objects.create_user(
            username='active_student',
            email='active.student@francisxavier.ac.in',
            password='CorrectPassword123!',
            role='STUDENT',
            is_active=True,
            verification_status='VERIFIED'
        )
        login_url = reverse('login')
        res = self.client.post(login_url, {
            'username': user.email,
            'password': 'WrongPassword123!'
        })
        assert res.status_code == 400
        assert 'Invalid username or password.' in str(res.data)

    # =========================================================================
    # 4. Wrong OTP rejected
    # =========================================================================
    def test_04_wrong_otp_rejected(self):
        reg_url = reverse('register')
        self.client.post(reg_url, {
            'name': 'Rahul Sharma',
            'email': 'rahul.s@francisxavier.ac.in',
            'register_number': '951322104012',
            'department': self.dept_cse.id,
            'year': 2,
            'password': 'Password123!'
        }, format='json')

        verify_url = reverse('verify_otp')
        res = self.client.post(verify_url, {
            'email': 'rahul.s@francisxavier.ac.in',
            'otp': '000000'
        }, format='json')

        assert res.status_code == 400
        assert 'Invalid verification code' in str(res.data)

        # Check failed attempts count incremented
        otp_rec = EmailVerificationOTP.objects.get(email='rahul.s@francisxavier.ac.in', is_used=False)
        assert otp_rec.attempts_count == 1

    # =========================================================================
    # 5. Max incorrect OTP attempts locks out / invalidates OTP
    # =========================================================================
    def test_05_max_incorrect_otp_attempts_locked_out(self):
        reg_url = reverse('register')
        self.client.post(reg_url, {
            'name': 'Anita Roy',
            'email': 'anita.r@francisxavier.ac.in',
            'register_number': '951322104013',
            'department': self.dept_cse.id,
            'year': 3,
            'password': 'Password123!'
        }, format='json')

        verify_url = reverse('verify_otp')
        for i in range(5):
            res = self.client.post(verify_url, {
                'email': 'anita.r@francisxavier.ac.in',
                'otp': f'11111{i}'
            }, format='json')
            assert res.status_code == 400

        assert 'Too many incorrect attempts' in str(res.data)
        otp_rec = EmailVerificationOTP.objects.get(email='anita.r@francisxavier.ac.in')
        assert otp_rec.is_used is True, "Exceeded attempts must invalidate the OTP record!"

    # =========================================================================
    # 6. Expired OTP rejected
    # =========================================================================
    def test_06_expired_otp_rejected(self):
        reg_url = reverse('register')
        self.client.post(reg_url, {
            'name': 'Deepak Raj',
            'email': 'deepak.r@francisxavier.ac.in',
            'register_number': '951322104014',
            'department': self.dept_cse.id,
            'year': 4,
            'password': 'Password123!'
        }, format='json')

        otp_code = self._extract_otp_from_outbox()

        # Simulate expiration
        otp_rec = EmailVerificationOTP.objects.get(email='deepak.r@francisxavier.ac.in', is_used=False)
        otp_rec.expires_at = timezone.now() - timedelta(minutes=5)
        otp_rec.save(update_fields=['expires_at'])

        verify_url = reverse('verify_otp')
        res = self.client.post(verify_url, {
            'email': 'deepak.r@francisxavier.ac.in',
            'otp': otp_code
        }, format='json')

        assert res.status_code == 400
        assert 'expired' in str(res.data).lower()

    # =========================================================================
    # 7. Successful OTP verification activates account and enables login
    # =========================================================================
    def test_07_successful_otp_verification_activates_account_and_login_succeeds(self):
        reg_url = reverse('register')
        res_reg = self.client.post(reg_url, {
            'name': 'Suresh Kumar',
            'email': 'suresh.k@francisxavier.ac.in',
            'register_number': '951322104015',
            'department': self.dept_cse.id,
            'year': 2,
            'password': 'Password123!'
        }, format='json')
        assert res_reg.status_code == 201

        # Extract OTP sent to institutional mailbox
        otp_code = self._extract_otp_from_outbox()

        # Submit valid OTP
        verify_url = reverse('verify_otp')
        res_verify = self.client.post(verify_url, {
            'email': 'suresh.k@francisxavier.ac.in',
            'otp': otp_code
        }, format='json')

        assert res_verify.status_code == 200, res_verify.data
        assert 'token' in res_verify.data
        assert res_verify.data['user']['email'] == 'suresh.k@francisxavier.ac.in'
        assert res_verify.data['user']['verification_status'] == 'VERIFIED'
        assert res_verify.data['user']['is_active'] is True

        # Check DB
        user = User.objects.get(email='suresh.k@francisxavier.ac.in')
        assert user.is_active is True
        assert user.verification_status == 'VERIFIED'

        # Now login must succeed seamlessly
        login_url = reverse('login')
        res_login = self.client.post(login_url, {
            'username': 'suresh.k@francisxavier.ac.in',
            'password': 'Password123!'
        })
        assert res_login.status_code == 200
        assert res_login.data['user']['role'] == 'STUDENT'

    # =========================================================================
    # 8. Rate-limiting OTP resends (60-sec cooldown, max 3 resends)
    # =========================================================================
    def test_08_resend_otp_rate_limiting_and_max_attempts(self):
        reg_url = reverse('register')
        self.client.post(reg_url, {
            'name': 'Kavita M',
            'email': 'kavita.m@francisxavier.ac.in',
            'register_number': '951322104016',
            'department': self.dept_cse.id,
            'year': 1,
            'password': 'Password123!'
        }, format='json')

        resend_url = reverse('resend_otp')

        # Immediate resend attempt must be blocked by cooldown (HTTP 429)
        res_immediate = self.client.post(resend_url, {'email': 'kavita.m@francisxavier.ac.in'}, format='json')
        assert res_immediate.status_code == 429
        assert 'wait' in str(res_immediate.data).lower()

        # Simulate passage of 65 seconds
        otp_rec = EmailVerificationOTP.objects.get(email='kavita.m@francisxavier.ac.in', is_used=False)
        otp_rec.last_resend_at = timezone.now() - timedelta(seconds=65)
        otp_rec.save(update_fields=['last_resend_at'])

        # Resend 1 succeeds
        res_1 = self.client.post(resend_url, {'email': 'kavita.m@francisxavier.ac.in'}, format='json')
        assert res_1.status_code == 200
        assert res_1.data['resend_count'] == 1

        # Simulate resends up to limit
        otp_rec = EmailVerificationOTP.objects.get(email='kavita.m@francisxavier.ac.in', is_used=False)
        otp_rec.last_resend_at = timezone.now() - timedelta(seconds=65)
        otp_rec.save(update_fields=['last_resend_at'])
        res_2 = self.client.post(resend_url, {'email': 'kavita.m@francisxavier.ac.in'}, format='json')
        assert res_2.status_code == 200
        assert res_2.data['resend_count'] == 2

        otp_rec = EmailVerificationOTP.objects.get(email='kavita.m@francisxavier.ac.in', is_used=False)
        otp_rec.last_resend_at = timezone.now() - timedelta(seconds=65)
        otp_rec.save(update_fields=['last_resend_at'])
        res_3 = self.client.post(resend_url, {'email': 'kavita.m@francisxavier.ac.in'}, format='json')
        assert res_3.status_code == 200
        assert res_3.data['resend_count'] == 3

        # 4th resend exceeds maximum allowed (HTTP 429)
        otp_rec = EmailVerificationOTP.objects.get(email='kavita.m@francisxavier.ac.in', is_used=False)
        otp_rec.last_resend_at = timezone.now() - timedelta(seconds=65)
        otp_rec.save(update_fields=['last_resend_at'])
        res_4 = self.client.post(resend_url, {'email': 'kavita.m@francisxavier.ac.in'}, format='json')
        assert res_4.status_code == 429
        assert 'Maximum verification code resends reached' in str(res_4.data)

    # =========================================================================
    # 9. External and unauthorized email domains strictly rejected
    # =========================================================================
    def test_09_external_emails_strictly_rejected(self):
        reg_url = reverse('register')
        for bad_email in [
            'student@gmail.com',
            'student@yahoo.com',
            'student@outlook.com',
            'student@hotmail.com',
            'student@protonmail.com',
            'student@somedomain.edu'
        ]:
            res = self.client.post(reg_url, {
                'name': 'Attacker',
                'email': bad_email,
                'register_number': '951322104999',
                'department': self.dept_cse.id,
                'year': 2,
                'password': 'Password123!'
            }, format='json')
            assert res.status_code == 400
            assert 'francisxavier.ac.in' in str(res.data)

    # =========================================================================
    # 10. Approved Student Directory enforcement when directory is populated
    # =========================================================================
    def test_10_approved_student_directory_enforcement(self):
        # Populate approved student directory
        ApprovedStudentDirectory.objects.create(
            register_number='951322104050',
            email='approved.student@francisxavier.ac.in',
            full_name='Approved Student',
            department=self.dept_cse,
            year=3,
            is_active_student=True
        )

        reg_url = reverse('register')

        # Attempt to register with fake institutional email not in directory
        res_fake = self.client.post(reg_url, {
            'name': 'Fake Person',
            'email': 'unapproved.fake@francisxavier.ac.in',
            'register_number': '951322104051',
            'department': self.dept_cse.id,
            'year': 3,
            'password': 'Password123!'
        }, format='json')
        assert res_fake.status_code == 400
        assert 'approved' in str(res_fake.data).lower() or 'directory' in str(res_fake.data).lower()

        # Attempt to register with approved credentials: must succeed
        res_approved = self.client.post(reg_url, {
            'name': 'Approved Student',
            'email': 'approved.student@francisxavier.ac.in',
            'register_number': '951322104050',
            'department': self.dept_cse.id,
            'year': 3,
            'password': 'Password123!'
        }, format='json')
        assert res_approved.status_code == 201
        assert res_approved.data['status'] == 'PENDING_EMAIL_VERIFICATION'

    # =========================================================================
    # 11. Duplicate email and register number rejected for verified accounts
    # =========================================================================
    def test_11_duplicate_verified_student_rejected(self):
        User.objects.create_user(
            username='verified_student_1',
            email='existing.student@francisxavier.ac.in',
            register_number='951322104077',
            password='Password123!',
            role='STUDENT',
            is_active=True,
            verification_status='VERIFIED'
        )

        reg_url = reverse('register')
        # Duplicate email
        res_dup_email = self.client.post(reg_url, {
            'name': 'Duplicate Email Student',
            'email': 'existing.student@francisxavier.ac.in',
            'register_number': '951322104078',
            'department': self.dept_cse.id,
            'year': 2,
            'password': 'Password123!'
        }, format='json')
        assert res_dup_email.status_code == 400
        assert 'already exists' in str(res_dup_email.data)

        # Duplicate register number
        res_dup_reg = self.client.post(reg_url, {
            'name': 'Duplicate Reg Student',
            'email': 'different.student@francisxavier.ac.in',
            'register_number': '951322104077',
            'department': self.dept_cse.id,
            'year': 2,
            'password': 'Password123!'
        }, format='json')
        assert res_dup_reg.status_code == 400
        assert 'already exists' in str(res_dup_reg.data)

    # =========================================================================
    # 12. Blocked student account cannot login
    # =========================================================================
    def test_12_blocked_student_cannot_login(self):
        User.objects.create_user(
            username='blocked_student',
            email='blocked.student@francisxavier.ac.in',
            password='Password123!',
            role='STUDENT',
            is_active=False,
            verification_status='BLOCKED'
        )

        login_url = reverse('login')
        res = self.client.post(login_url, {
            'username': 'blocked.student@francisxavier.ac.in',
            'password': 'Password123!'
        })
        assert res.status_code == 400
        assert 'blocked' in str(res.data).lower()
