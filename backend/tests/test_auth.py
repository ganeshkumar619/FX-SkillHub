import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from authentication.authentication import generate_jwt_token

from catalogue.models import Department

User = get_user_model()

@pytest.mark.django_db
class TestAuthenticationAndRoles:
    def setup_method(self):
        self.client = APIClient()
        self.department, _ = Department.objects.get_or_create(
            code='CSE',
            defaults={
                'name': 'Computer Science and Engineering',
                'is_active': True,
                'source_type': 'ADMIN_CREATED',
                'approval_status': 'APPROVED',
                'content_status': 'PUBLISHED'
            }
        )
        self.student = User.objects.create_user(
            username='test_student',
            email='test.student@fxec.ac.in',
            password='Password123!',
            role='STUDENT',
            department=self.department
        )
        self.mentor = User.objects.create_user(
            username='test_mentor',
            email='test.mentor@fxec.ac.in',
            password='Password123!',
            role='MENTOR',
            department=self.department
        )
        self.admin = User.objects.create_user(
            username='test_admin',
            email='test.admin@fxec.ac.in',
            password='Password123!',
            role='ADMIN',
            is_staff=True,
            is_superuser=True
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
            'register_number': 'FXEC2026REG99',
            'department': self.department.id,
            'year': 1
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

    def test_student_registration_missing_department_fails(self):
        url = reverse('register')
        response = self.client.post(url, {
            'username': 'no_dept_student',
            'email': 'nodept@fxec.ac.in',
            'password': 'StrongPassword123!',
            'first_name': 'No',
            'last_name': 'Dept',
            'register_number': 'FXEC2026NODEPT',
            'year': 1
        })
        assert response.status_code == 400
        assert 'department' in response.data

    def test_student_registration_inactive_department_fails(self):
        inactive_dept = Department.objects.create(
            code='OLD_DEPT',
            name='Old Discontinued Department',
            is_active=False
        )
        url = reverse('register')
        response = self.client.post(url, {
            'username': 'inactive_dept_student',
            'email': 'inactivedept@fxec.ac.in',
            'password': 'StrongPassword123!',
            'first_name': 'Inactive',
            'last_name': 'Dept',
            'register_number': 'FXEC2026INACT',
            'department': inactive_dept.id,
            'year': 1
        })
        assert response.status_code == 400
        assert 'department' in response.data

    def test_public_department_list_returns_active_only(self):
        # Create an inactive department
        Department.objects.create(
            code='ARCHIVED_DEPT',
            name='Archived Engineering',
            is_active=False
        )
        url = reverse('department_list')
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        codes = [d['code'] for d in data]
        assert 'CSE' in codes
        assert 'ARCHIVED_DEPT' not in codes
        assert all(d['is_active'] is True for d in data)

    def test_admin_department_list_and_create(self):
        token = generate_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('admin_departments_list_create')

        # List departments (shows all)
        response = self.client.get(url)
        assert response.status_code == 200
        assert any(d['code'] == 'CSE' for d in response.data)

        # Create new department
        post_response = self.client.post(url, {
            'code': 'ROBOTICS',
            'name': 'Robotics and Automation',
            'description': 'Advanced robotics lab and department',
            'is_active': True
        })
        assert post_response.status_code == 201
        assert post_response.data['code'] == 'ROBOTICS'
        assert Department.objects.filter(code='ROBOTICS').exists()

    def test_admin_department_toggle_status(self):
        token = generate_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        dept = Department.objects.create(
            code='TEST_TOGGLE',
            name='Toggle Test Dept',
            is_active=True
        )
        url = reverse('admin_department_toggle_status', kwargs={'pk': dept.id})
        response = self.client.post(url)
        assert response.status_code == 200
        assert response.data['is_active'] is False

        dept.refresh_from_db()
        assert dept.is_active is False

        # Toggle back to active
        response2 = self.client.post(url)
        assert response2.status_code == 200
        assert response2.data['is_active'] is True
        dept.refresh_from_db()
        assert dept.is_active is True

    def test_admin_create_faculty_with_department(self):
        token = generate_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('admin_faculty_list')
        response = self.client.post(url, {
            'faculty_name': 'Dr. Suresh Kumar',
            'email': 'suresh.kumar@example.com',
            'faculty_id': 'FX-CSE-999',
            'department': self.department.id,
            'phone': '+91 9876543210',
            'is_active': True
        })
        assert response.status_code == 201
        faculty_user = User.objects.get(email='suresh.kumar@example.com')
        assert faculty_user.role == 'FACULTY'
        assert faculty_user.department == self.department

    def test_admin_create_faculty_without_department_fails(self):
        token = generate_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('admin_faculty_list')
        response = self.client.post(url, {
            'faculty_name': 'Dr. No Department',
            'email': 'nodept.faculty@example.com',
            'faculty_id': 'FX-NODEPT-999',
            'phone': '+91 9876543210',
            'is_active': True
        })
        assert response.status_code == 400
        assert 'department' in response.data

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

