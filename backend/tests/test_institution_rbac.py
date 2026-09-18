import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from catalogue.models import Course, Department, Skill, SkillCategory

User = get_user_model()

@pytest.mark.django_db
class TestInstitutionRBACAndAuthentication:
    def setup_method(self):
        self.client = APIClient()

        # Seed Department
        self.dept_cse, _ = Department.objects.get_or_create(
            code='CSE',
            defaults={'name': 'Computer Science & Engineering'}
        )
        self.dept_it, _ = Department.objects.get_or_create(
            code='IT',
            defaults={'name': 'Information Technology'}
        )

        # Category and Skill for course creation
        self.category, _ = SkillCategory.objects.get_or_create(
            name='Engineering Computing',
            defaults={'description': 'Core Engineering Skills'}
        )
        self.skill, _ = Skill.objects.get_or_create(
            name='Applied Machine Learning',
            defaults={
                'category': self.category,
                'department': self.dept_cse,
                'level': 'INTERMEDIATE'
            }
        )

        # Admin user
        self.admin = User.objects.create_user(
            username='inst_admin',
            email='admin@francisxavier.ac.in',
            password='AdminPassword123!',
            role='ADMIN',
            is_staff=True,
            is_superuser=True
        )

        # Faculty user
        self.faculty = User.objects.create_user(
            username='inst_faculty',
            email='dr.rajesh@francisxavier.ac.in',
            password='FacultyPassword123!',
            role='FACULTY',
            department=self.dept_cse,
            register_number='FX-FAC-101',
            is_staff=True
        )

        # Student user
        self.student = User.objects.create_user(
            username='inst_student',
            email='22cs101@francisxavier.ac.in',
            password='StudentPassword123!',
            role='STUDENT',
            department=self.dept_cse,
            register_number='951322104001',
            year=3
        )

    # =========================================================================
    # Scenario 1: Admin can create Faculty
    # =========================================================================
    def test_01_admin_can_create_faculty(self):
        self.client.force_authenticate(user=self.admin)
        url = '/api/admin/faculty/'
        payload = {
            'first_name': 'Anitha',
            'last_name': 'M',
            'email': 'anitha.m@francisxavier.ac.in',
            'faculty_id': 'FX-FAC-102',
            'department': self.dept_cse.id,
            'phone': '+91 9876543210',
            'password': 'SecureFaculty123!',
            'is_active': True
        }
        response = self.client.post(url, payload, format='json')
        assert response.status_code == 201, response.data
        faculty_data = response.data.get('faculty', response.data)
        assert faculty_data['email'] == 'anitha.m@francisxavier.ac.in'
        assert faculty_data['role'] == 'FACULTY'
        assert faculty_data['faculty_id'] == 'FX-FAC-102'

        # Verify created in DB
        created_user = User.objects.get(email='anitha.m@francisxavier.ac.in')
        assert created_user.role == 'FACULTY'
        assert created_user.is_staff is True
        assert created_user.check_password('SecureFaculty123!')

    # =========================================================================
    # Scenario 2: Non-admin (Student, Faculty) cannot create Faculty (HTTP 403)
    # =========================================================================
    def test_02_non_admin_cannot_create_faculty(self):
        url = '/api/admin/faculty/'
        payload = {
            'first_name': 'Hacker',
            'email': 'hacker@francisxavier.ac.in',
            'faculty_id': 'FX-HACK-01'
        }

        # Student attempt -> 403
        self.client.force_authenticate(user=self.student)
        res_student = self.client.post(url, payload, format='json')
        assert res_student.status_code == 403

        # Faculty attempt -> 403
        self.client.force_authenticate(user=self.faculty)
        res_faculty = self.client.post(url, payload, format='json')
        assert res_faculty.status_code == 403

        # Anonymous attempt -> 401 or 403
        self.client.force_authenticate(user=None)
        res_anon = self.client.post(url, payload, format='json')
        assert res_anon.status_code in [401, 403]

    # =========================================================================
    # Scenario 3: Faculty with @francisxavier.ac.in can login and access Faculty Studio
    # =========================================================================
    def test_03_faculty_can_login_and_access_faculty_studio(self):
        login_url = reverse('login')
        res_login = self.client.post(login_url, {
            'username': 'inst_faculty',
            'password': 'FacultyPassword123!'
        })
        assert res_login.status_code == 200
        assert res_login.data['user']['role'] == 'FACULTY'
        assert 'token' in res_login.data

        # Authenticate as faculty and access Faculty Studio endpoints
        self.client.force_authenticate(user=self.faculty)
        res_courses = self.client.get('/api/catalogue/faculty/my-courses/')
        assert res_courses.status_code == 200

        res_skills = self.client.get('/api/catalogue/faculty/my-skills/')
        assert res_skills.status_code == 200

    # =========================================================================
    # Scenario 4: Faculty with external email cannot be created (HTTP 400)
    # =========================================================================
    def test_04_faculty_with_external_email_rejected(self):
        self.client.force_authenticate(user=self.admin)
        url = '/api/admin/faculty/'

        for bad_email in [
            'faculty@gmail.com',
            'faculty@yahoo.com',
            'faculty@outlook.com',
            'faculty@protonmail.com',
            'faculty@randomdomain.org'
        ]:
            payload = {
                'first_name': 'Bad',
                'email': bad_email,
                'faculty_id': f'FX-{bad_email[:4]}'
            }
            res = self.client.post(url, payload, format='json')
            assert res.status_code == 400
            assert 'francisxavier.ac.in' in str(res.data)

    # =========================================================================
    # Scenario 5: Student with @francisxavier.ac.in can register and login
    # =========================================================================
    def test_05_student_with_institutional_email_can_register_and_login(self):
        reg_url = reverse('register')
        payload = {
            'name': 'Karthik Raja',
            'email': '22cs105@francisxavier.ac.in',
            'register_number': '951322104005',
            'department': self.dept_cse.id,
            'year': 3,
            'password': 'StudentRegPass123!'
        }
        res_reg = self.client.post(reg_url, payload, format='json')
        assert res_reg.status_code == 201, res_reg.data
        assert res_reg.data['status'] == 'PENDING_EMAIL_VERIFICATION'
        assert res_reg.data['requires_otp'] is True

        # Verify unverified login is rejected
        login_url = reverse('login')
        res_unverified = self.client.post(login_url, {
            'username': '22cs105@francisxavier.ac.in',
            'password': 'StudentRegPass123!'
        })
        assert res_unverified.status_code == 400
        assert 'Please verify your institutional email first.' in str(res_unverified.data)

        # Extract OTP from email outbox
        import re
        from django.core import mail
        match = re.search(r'(?:VERIFICATION CODE:\s*|code is:\s*)(\d{6})', mail.outbox[-1].body)
        assert match is not None
        otp = match.group(1)

        # Verify OTP
        verify_url = reverse('verify_otp')
        res_verify = self.client.post(verify_url, {
            'email': '22cs105@francisxavier.ac.in',
            'otp': otp
        }, format='json')
        assert res_verify.status_code == 200
        assert res_verify.data['user']['role'] == 'STUDENT'
        assert res_verify.data['user']['verification_status'] == 'VERIFIED'

        # Login with registered account now succeeds
        res_login = self.client.post(login_url, {
            'username': res_verify.data['user']['username'],
            'password': 'StudentRegPass123!'
        })
        assert res_login.status_code == 200
        assert res_login.data['user']['role'] == 'STUDENT'

    # =========================================================================
    # Scenario 6: Student with external email cannot register (HTTP 400)
    # =========================================================================
    def test_06_student_with_external_email_cannot_register(self):
        reg_url = reverse('register')
        for bad_email in [
            'student@gmail.com',
            'student@yahoo.co.in',
            'student@hotmail.com',
            'student@college.edu'
        ]:
            payload = {
                'name': 'Intruder Student',
                'email': bad_email,
                'register_number': '951322104999',
                'department': self.dept_cse.id,
                'year': 2,
                'password': 'Password123!'
            }
            res = self.client.post(reg_url, payload, format='json')
            assert res.status_code == 400
            assert 'francisxavier.ac.in' in str(res.data)

    # =========================================================================
    # Scenario 7: Backend authoritative check rejects external email even on bypass
    # =========================================================================
    def test_07_backend_strictly_rejects_external_emails_direct(self):
        from authentication.validators import validate_institutional_email

        with pytest.raises(ValidationError) as exc:
            validate_institutional_email('attacker@gmail.com')
        assert 'External email domains' in str(exc.value) or 'francisxavier.ac.in' in str(exc.value)

        # Valid institutional email passes
        clean = validate_institutional_email('student.22cs@francisxavier.ac.in')
        assert clean == 'student.22cs@francisxavier.ac.in'

    # =========================================================================
    # Scenario 8: Student cannot access Faculty dashboard or APIs (HTTP 403)
    # =========================================================================
    def test_08_student_cannot_access_faculty_apis(self):
        self.client.force_authenticate(user=self.student)

        # Attempt to access faculty course list
        res1 = self.client.get('/api/catalogue/faculty/my-courses/')
        assert res1.status_code == 403

        # Attempt to create course as faculty
        res2 = self.client.post('/api/catalogue/faculty/courses/', {
            'title': 'Unauthorized Student Course'
        }, format='json')
        assert res2.status_code == 403

    # =========================================================================
    # Scenario 9: Student cannot access Admin APIs (HTTP 403)
    # =========================================================================
    def test_09_student_cannot_access_admin_apis(self):
        self.client.force_authenticate(user=self.student)

        res_fac = self.client.get('/api/admin/faculty/')
        assert res_fac.status_code == 403

        res_overview = self.client.get('/api/admin/overview/')
        assert res_overview.status_code == 403

        res_students = self.client.get('/api/admin/students/')
        assert res_students.status_code == 403

        res_proposals = self.client.get('/api/catalogue/admin/course-proposals/')
        assert res_proposals.status_code == 403

    # =========================================================================
    # Scenario 10: Faculty cannot access Admin APIs (HTTP 403)
    # =========================================================================
    def test_10_faculty_cannot_access_admin_apis(self):
        self.client.force_authenticate(user=self.faculty)

        res_fac = self.client.get('/api/admin/faculty/')
        assert res_fac.status_code == 403

        res_overview = self.client.get('/api/admin/overview/')
        assert res_overview.status_code == 403

        res_students = self.client.get('/api/admin/students/')
        assert res_students.status_code == 403

        res_proposals = self.client.get('/api/catalogue/admin/course-proposals/')
        assert res_proposals.status_code == 403

    # =========================================================================
    # Scenario 11: Admin can review Faculty-created courses (Approve/Reject)
    # =========================================================================
    def test_11_admin_can_review_faculty_courses(self):
        # 1. Faculty creates a course proposal (in review)
        self.client.force_authenticate(user=self.faculty)
        course = Course.objects.create(
            title='Autonomous Neural Networks',
            slug='autonomous-neural-networks',
            skill=self.skill,
            department=self.dept_cse,
            created_by=self.faculty,
            approval_status='PENDING_REVIEW',
            is_published=False
        )

        # 2. Admin views pending proposals
        self.client.force_authenticate(user=self.admin)
        res_proposals = self.client.get('/api/catalogue/admin/course-proposals/')
        assert res_proposals.status_code == 200
        proposals = res_proposals.data.get('results', res_proposals.data)
        proposal_ids = [c['id'] for c in proposals]
        assert course.id in proposal_ids

        # 3. Admin approves course
        res_approve = self.client.post(
            f'/api/catalogue/admin/course-proposals/{course.id}/approve/',
            {'notes': 'Curriculum rigorously validated.'},
            format='json'
        )
        assert res_approve.status_code == 200
        assert res_approve.data['course']['approval_status'] == 'APPROVED'

        # Refresh from db
        course.refresh_from_db()
        assert course.approval_status == 'APPROVED'
        assert course.is_published is True

    # =========================================================================
    # Scenario 12: Only approved/published courses are visible to students
    # =========================================================================
    def test_12_only_approved_published_courses_visible_to_students(self):
        # Create a draft/unapproved course
        draft_course = Course.objects.create(
            title='Secret Draft Course',
            slug='secret-draft-course',
            skill=self.skill,
            department=self.dept_cse,
            created_by=self.faculty,
            approval_status='DRAFT',
            is_published=False
        )

        # Create a pending review course
        pending_course = Course.objects.create(
            title='Pending Review Course',
            slug='pending-review-course',
            skill=self.skill,
            department=self.dept_cse,
            created_by=self.faculty,
            approval_status='PENDING_REVIEW',
            is_published=False
        )

        # Create an approved & published course
        published_course = Course.objects.create(
            title='Public Approved Course',
            slug='public-approved-course',
            skill=self.skill,
            department=self.dept_cse,
            created_by=self.faculty,
            approval_status='APPROVED',
            is_published=True
        )

        # Student views courses catalogue
        self.client.force_authenticate(user=self.student)
        res_catalogue = self.client.get('/api/catalogue/courses/')
        assert res_catalogue.status_code == 200
        courses = res_catalogue.data.get('results', res_catalogue.data)
        course_ids = [c['id'] for c in courses]

        # Approved course is visible
        assert published_course.id in course_ids

        # Draft and Pending courses are NOT visible to students
        assert draft_course.id not in course_ids
        assert pending_course.id not in course_ids
