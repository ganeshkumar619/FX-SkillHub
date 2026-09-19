import pytest
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from catalogue.models import Course, Department, Skill, SkillCategory
from assessments.models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from proctoring.models import ProctoringEvent, RiskScore
from proctoring.security_engine import AssessmentSecurityEngine
from authentication.authentication import generate_jwt_token

User = get_user_model()

@pytest.mark.django_db
class TestGoogleOAuthFlow:
    def setup_method(self):
        self.client = APIClient()

    @patch('authentication.google_auth_service.GoogleAuthService.get_client_id', return_value='test-client-id')
    def test_google_auth_url_endpoint(self, mock_client_id):
        url = reverse('google_auth_url')
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'auth_url' in data
        assert data['client_id'] == 'test-client-id'
        assert 'accounts.google.com/o/oauth2/v2/auth' in data['auth_url']

    @patch('authentication.google_auth_service.GoogleAuthService.exchange_code_for_user_info')
    def test_google_callback_creates_new_student(self, mock_exchange):
        mock_exchange.return_value = {
            'email': 'ananya.k@fxec.ac.in',
            'sub': 'google-uid-12345',
            'given_name': 'Ananya',
            'family_name': 'Krishnan',
            'email_verified': True
        }

        url = reverse('google_auth_callback')
        response = self.client.post(url, {'code': 'valid_test_auth_code'})
        assert response.status_code == 200
        data = response.json()
        assert 'token' in data
        assert data['user']['email'] == 'ananya.k@fxec.ac.in'
        assert data['user']['role'] == 'STUDENT'

        # Verify DB record
        user = User.objects.get(email='ananya.k@fxec.ac.in')
        assert user.google_id == 'google-uid-12345'
        assert user.auth_provider == 'GOOGLE'

    @patch('authentication.google_auth_service.GoogleAuthService.exchange_code_for_user_info')
    def test_google_callback_links_existing_verified_account(self, mock_exchange):
        existing_student = User.objects.create_user(
            username='priya_s',
            email='priya.sharma@fxec.ac.in',
            password='Password123!',
            first_name='Priya',
            last_name='Sharma',
            role='STUDENT',
            auth_provider='LOCAL'
        )
        initial_user_count = User.objects.count()

        mock_exchange.return_value = {
            'email': 'priya.sharma@fxec.ac.in',
            'sub': 'google-uid-99999',
            'given_name': 'Priya',
            'family_name': 'Sharma',
            'email_verified': True
        }

        url = reverse('google_auth_callback')
        response = self.client.post(url, {'code': 'valid_test_auth_code'})
        assert response.status_code == 200
        assert User.objects.count() == initial_user_count

        existing_student.refresh_from_db()
        assert existing_student.google_id == 'google-uid-99999'

    @patch('authentication.google_auth_service.GoogleAuthService.exchange_code_for_user_info')
    def test_google_callback_duplicate_request_idempotency(self, mock_exchange):
        mock_exchange.return_value = {
            'email': 'duplicate.test@fxec.ac.in',
            'sub': 'google-uid-dup-111',
            'given_name': 'Duplicate',
            'family_name': 'Tester',
            'email_verified': True
        }
        url = reverse('google_auth_callback')
        res1 = self.client.post(url, {'code': 'dup_auth_code_123'})
        assert res1.status_code == 200
        assert 'token' in res1.json()

        res2 = self.client.post(url, {'code': 'dup_auth_code_123'})
        assert res2.status_code == 200
        assert res2.json()['user']['email'] == 'duplicate.test@fxec.ac.in'



@pytest.mark.django_db
class TestAssessmentSecurityEngine:
    def setup_method(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username='exam_student',
            email='exam.student@fxec.ac.in',
            password='Password123!',
            role='STUDENT'
        )
        self.mentor = User.objects.create_user(
            username='faculty_mentor',
            email='mentor@fxec.ac.in',
            password='Password123!',
            role='MENTOR'
        )
        self.student_token = generate_jwt_token(self.student)
        self.mentor_token = generate_jwt_token(self.mentor)

        # Build academic catalogue structure
        category = SkillCategory.objects.create(name='AI Engineering', description='AI Skills')
        dept, _ = Department.objects.get_or_create(code='CSE', defaults={'name': 'Computer Science and Engineering'})
        skill = Skill.objects.create(name='Computer Vision', category=category, department=dept, level='INTERMEDIATE')
        course = Course.objects.create(
            title='Autonomous CV Systems',
            slug='autonomous-cv-systems',
            skill=skill,
            department=dept,
            instructor_name='Dr. Ramesh',
            is_published=True
        )

        self.assessment = Assessment.objects.create(
            course=course,
            title='CV Systems Autonomous Certification Exam',
            assessment_type='FINAL_ASSESSMENT',
            duration_minutes=30,
            pass_percentage=70.0,
            is_published=True,
            camera_required=True,
            screen_share_required=True,
            fullscreen_required=True,
            face_detection_enabled=True,
            max_camera_warnings=2,
            max_multiple_face_warnings=2,
            max_screen_share_warnings=2,
            max_fullscreen_warnings=2,
            max_tab_switch_warnings=2,
            auto_terminate_on_limit=True
        )

        self.question = Question.objects.create(
            assessment=self.assessment,
            text='What algorithm is used for optical bounding box calculation?',
            topic_tag='CV_BOUNDING',
            question_type='SINGLE_CHOICE',
            marks=5,
            order=1
        )
        self.opt1 = QuestionOption.objects.create(question=self.question, text='YOLO / SSD', is_correct=True, order=1)
        self.opt2 = QuestionOption.objects.create(question=self.question, text='Bubble Sort', is_correct=False, order=2)

        self.attempt = AssessmentAttempt.objects.create(
            assessment=self.assessment,
            student=self.student,
            status='IN_PROGRESS',
            server_deadline=timezone.now() + timedelta(minutes=30)
        )

    def test_camera_warnings_progression_and_auto_termination(self):
        """
        Tests warning 1, warning 2, and 3rd auto-termination on camera drop.
        """
        # Warning 1
        res1 = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='CAMERA_DISCONNECTED',
            severity='CRITICAL'
        )
        assert res1['action_taken'] == 'WARNING_ISSUED'
        assert res1['current_warning_count'] == 1
        assert res1['is_terminated'] is False
        self.attempt.refresh_from_db()
        assert self.attempt.status == 'WARNING'
        assert self.attempt.camera_warning_count == 1

        # Fast forward beyond 5s debounce window for next event
        ProctoringEvent.objects.filter(attempt=self.attempt).update(
            timestamp=timezone.now() - timedelta(seconds=10)
        )

        # Warning 2
        res2 = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='CAMERA_DISCONNECTED',
            severity='CRITICAL'
        )
        assert res2['action_taken'] == 'WARNING_ISSUED'
        assert res2['current_warning_count'] == 2
        assert res2['is_terminated'] is False
        self.attempt.refresh_from_db()
        assert self.attempt.camera_warning_count == 2

        ProctoringEvent.objects.filter(attempt=self.attempt).update(
            timestamp=timezone.now() - timedelta(seconds=10)
        )

        # 3rd occurrence -> auto-termination (exceeds max_camera_warnings=2)
        res3 = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='CAMERA_DISCONNECTED',
            severity='CRITICAL'
        )
        assert res3['action_taken'] == 'AUTO_TERMINATE'
        assert res3['is_terminated'] is True
        assert 'exceeded allowed threshold' in res3['termination_reason']
        self.attempt.refresh_from_db()
        assert self.attempt.status == 'TERMINATED_SECURITY_VIOLATION'
        assert self.attempt.terminated_at is not None

    def test_independent_violation_counters(self):
        """
        Verifies that camera violations and fullscreen exits use independent counters.
        """
        res_cam = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='CAMERA_DISCONNECTED',
            severity='CRITICAL'
        )
        assert res_cam['current_warning_count'] == 1
        self.attempt.refresh_from_db()
        assert self.attempt.camera_warning_count == 1
        assert self.attempt.fullscreen_warning_count == 0

        res_fs = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='FULLSCREEN_EXIT',
            severity='CRITICAL'
        )
        assert res_fs['current_warning_count'] == 1
        self.attempt.refresh_from_db()
        assert self.attempt.camera_warning_count == 1
        assert self.attempt.fullscreen_warning_count == 1

    def test_autosave_rejected_on_terminated_attempt(self):
        """
        Verifies that AutosaveAnswerView returns HTTP 403 on terminated attempts.
        """
        self.attempt.status = 'TERMINATED_SECURITY_VIOLATION'
        self.attempt.termination_reason = 'Screen share dropped 3 times.'
        self.attempt.save()

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        url = reverse('autosave_answer', kwargs={'attempt_id': self.attempt.id})
        response = self.client.post(url, {
            'question_id': self.question.id,
            'option_ids': [self.opt1.id]
        })
        assert response.status_code == 403
        data = response.json()
        assert data['status'] == 'TERMINATED_SECURITY_VIOLATION'
        assert 'strictly rejected' in data['error']

    def test_debounce_duplicate_suppression(self):
        """
        Multiple identical events within 5 seconds must not increment warning count multiple times.
        """
        res1 = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='TAB_SWITCH',
            severity='CRITICAL'
        )
        assert res1['current_warning_count'] == 1
        assert res1['action_taken'] == 'WARNING_ISSUED'

        # Send second event immediately without advancing time
        res2 = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='TAB_SWITCH',
            severity='CRITICAL'
        )
        assert res2['action_taken'] == 'INCIDENT_CONTINUATION'
        assert res2['current_warning_count'] == 1

        self.attempt.refresh_from_db()
        assert self.attempt.tab_switch_warning_count == 1

    def test_mentor_review_queue_filters_terminated_attempts(self):
        """
        Verifies MentorReviewQueueView exposes terminated attempts and violation metrics.
        """
        self.attempt.status = 'TERMINATED_SECURITY_VIOLATION'
        self.attempt.camera_warning_count = 3
        self.attempt.termination_reason = 'Camera disconnected 3 times.'
        self.attempt.save()

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.mentor_token}')
        url = reverse('mentor_review_queue') + '?filter=flagged'
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        item = next(x for x in data if x['attempt_id'] == str(self.attempt.id))
        assert item['status'] == 'TERMINATED_SECURITY_VIOLATION'
        assert item['camera_violations'] == 3
        assert item['termination_reason'] == 'Camera disconnected 3 times.'

    def test_multiple_faces_continuous_warning_does_not_terminate_exam(self):
        """
        User Requirement: Double/multiple faces detection must continuously show warnings
        and log events, but MUST NEVER auto-terminate or close the examination session.
        """
        self.assessment.max_multiple_face_warnings = 2
        self.assessment.auto_terminate_on_limit = True
        self.assessment.save()

        # Warning 1
        res1 = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='MULTIPLE_FACES_DETECTED',
            severity='HIGH',
            details={'face_count': 2}
        )
        assert res1['is_terminated'] is False
        assert res1['action_taken'] == 'WARNING_ISSUED'

        # Advance attempt state for Warning 2 & 3
        self.attempt.multiple_face_warning_count = 2
        self.attempt.save()

        # Warning 3 (Exceeds max allowed of 2)
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=10)):
            res3 = AssessmentSecurityEngine.process_security_event(
                attempt=self.attempt,
                student=self.student,
                event_type='MULTIPLE_FACES_DETECTED',
                severity='HIGH',
                details={'face_count': 3}
            )
            # Must NOT terminate
            assert res3['is_terminated'] is False
            assert res3['action_taken'] != 'AUTO_TERMINATE'

            self.attempt.refresh_from_db()
            assert self.attempt.status != 'TERMINATED_SECURITY_VIOLATION'
            assert self.attempt.status == 'WARNING'

    def test_blank_camera_mobile_and_ai_events(self):
        """
        Verify CAMERA_COVERED_BLANK, MOBILE_PHONE_DETECTED, and AI_ASSISTANCE_DETECTED
        are recognized, scored, and logged.
        """
        res_blank = AssessmentSecurityEngine.process_security_event(
            attempt=self.attempt,
            student=self.student,
            event_type='CAMERA_COVERED_BLANK',
            severity='HIGH',
            details={'reason': 'Luminance below threshold'}
        )
        assert res_blank['is_terminated'] is False
        assert res_blank['warning_type'] == 'camera'

        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=10)):
            res_mobile = AssessmentSecurityEngine.process_security_event(
                attempt=self.attempt,
                student=self.student,
                event_type='MOBILE_PHONE_DETECTED',
                severity='CRITICAL',
                details={'reason': 'Optical device detected'}
            )
            assert res_mobile['status'] == 'recorded'

        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=20)):
            res_ai = AssessmentSecurityEngine.process_security_event(
                attempt=self.attempt,
                student=self.student,
                event_type='AI_ASSISTANCE_DETECTED',
                severity='HIGH',
                details={'reason': 'Clipboard copy intercepted'}
            )
            assert res_ai['status'] == 'recorded'

        risk = RiskScore.objects.get(attempt=self.attempt)
        assert risk.numerical_score > 0

