import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from authentication.authentication import generate_jwt_token

User = get_user_model()

@pytest.mark.django_db
class TestAuthenticationAndRoles:
    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username='test_student',
            email='test.student@fxec.ac.in',
            password='Password123!',
            role='STUDENT'
        )
        self.mentor = User.objects.create_user(
            username='test_mentor',
            email='test.mentor@fxec.ac.in',
            password='Password123!',
            role='MENTOR'
        )
        self.admin = User.objects.create_user(
            username='test_admin',
            email='test.admin@fxec.ac.in',
            password='Password123!',
            role='ADMIN'
        )

    def test_root_endpoint(self):
        response = self.client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'FX SkillHub'
        assert data['status'] == 'running'
        assert data['frontend'] == 'http://localhost:5173'
        assert data['api'] == '/api/'
        assert data['health'] == '/api/health/'

    def test_health_check_endpoint(self):
        url = reverse('health_check')
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data['status'] == 'ok'
        assert response.data['service'] == 'FX SkillHub Backend'
        assert response.data['version'] == '1.0.0'

    def test_student_login_success(self):
        url = reverse('login')
        response = self.client.post(url, {
            'username': 'test_student',
            'password': 'Password123!'
        })
        assert response.status_code == 200
        assert 'token' in response.data
        assert response.data['user']['role'] == 'STUDENT'

    def test_student_login_invalid_password(self):
        url = reverse('login')
        response = self.client.post(url, {
            'username': 'test_student',
            'password': 'WrongPassword!'
        })
        assert response.status_code == 400
        assert 'Invalid username or password' in str(response.data)

    def test_student_registration(self):
        url = reverse('register')
        response = self.client.post(url, {
            'username': 'new_student',
            'email': 'new.student@fxec.ac.in',
            'password': 'StrongPassword123!',
            'first_name': 'New',
            'last_name': 'Student',
            'register_number': 'FXEC2026REG99'
        })
        assert response.status_code == 201
        assert response.data['status'] == 'PENDING_EMAIL_VERIFICATION'
        assert response.data['requires_otp'] is True
        assert User.objects.filter(username='new_student').exists()

        # Extract OTP from email outbox and verify
        import re
        from django.core import mail
        match = re.search(r'(?:VERIFICATION CODE:\s*|code is:\s*)(\d{6})', mail.outbox[-1].body)
        assert match is not None
        otp = match.group(1)

        verify_res = self.client.post(reverse('verify_otp'), {
            'email': 'new.student@fxec.ac.in',
            'otp': otp
        })
        assert verify_res.status_code == 200
        assert 'token' in verify_res.data
        assert verify_res.data['user']['role'] == 'STUDENT'
        assert verify_res.data['user']['verification_status'] == 'VERIFIED'

    def test_authenticated_profile_access(self):
        token = generate_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('user_profile')
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data['username'] == 'test_student'

    def test_unauthenticated_profile_access_rejected(self):
        url = reverse('user_profile')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
