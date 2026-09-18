import pytest
import uuid
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from catalogue.models import (
    Department,
    SkillCategory,
    SkillDomain,
    Skill,
    Course,
    Module,
    Lesson,
    VideoResource,
    StudyMaterial,
    PracticeTask
)
from learning.models import (
    Enrollment,
    ModuleProgress,
    VideoProgress,
    MaterialProgress,
    PracticeProgress
)
from assessments.models import (
    Assessment,
    AssessmentAttempt,
    Question,
    QuestionOption,
    StudentAnswer
)
from certificates.models import Certificate
from proctoring.security_engine import AssessmentSecurityEngine
from authentication.authentication import generate_jwt_token

User = get_user_model()


@pytest.mark.django_db
class TestModuleLearningAndEligibility:
    """
    Comprehensive 14-scenario automated test suite verifying:
    - Module learning completion criteria (Video 80%, Study Material, Practice 70%)
    - Strict assessment lock and server-authoritative unlock
    - Direct URL bypass blocking (HTTP 403)
    - Cross-session / refresh progress persistence
    - Proctoring violation accumulation and auto-termination
    - Idempotent certificate issuance upon passing (and denial upon failing)
    """

    def setup_method(self):
        self.client = APIClient()

        # 1. Department, Category, Domain, Skill, Course
        self.dept = Department.objects.create(
            code='CSE',
            name='Computer Science and Engineering',
            source_type='FXEC_OFFICIAL'
        )
        self.category = SkillCategory.objects.create(
            name='Core Engineering',
            source_type='FXEC_OFFICIAL'
        )
        self.domain = SkillDomain.objects.create(
            category=self.category,
            name='Programming & Software Development',
            source_type='FXEC_OFFICIAL'
        )
        self.skill = Skill.objects.create(
            name='Python Core',
            slug='python-core',
            category=self.category,
            domain=self.domain,
            department=self.dept,
            level='BEGINNER',
            status='ACTIVE'
        )
        self.course = Course.objects.create(
            title='Python Fundamentals for Engineers',
            slug='python-fundamentals-for-engineers',
            skill=self.skill,
            level='BEGINNER',
            estimated_hours=40,
            status='PUBLISHED'
        )

        # 2. Build 8 ordered modules with required activities
        self.modules = []
        for m_idx in range(1, 9):
            mod = Module.objects.create(
                course=self.course,
                title=f'Module {m_idx}: Core Concepts Part {m_idx}',
                order=m_idx,
                is_required=True,
                status='PUBLISHED'
            )
            # Required Video (300 seconds, 80% completion threshold)
            vid = VideoResource.objects.create(
                module=mod,
                title=f'Video Lecture {m_idx}',
                video_type='EXTERNAL_VIDEO',
                external_url='https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
                duration_seconds=300,
                completion_threshold_percent=80.0,
                is_required=True,
                status='PUBLISHED'
            )
            # Required Study Material (PDF guide)
            mat = StudyMaterial.objects.create(
                module=mod,
                title=f'Study Guide {m_idx}',
                resource_type='PDF',
                external_url=f'http://localhost:5173/materials/guide_{m_idx}.pdf',
                completion_method='MANUAL_COMPLETE',
                is_required=True,
                status='PUBLISHED'
            )
            # Required Practice Task (pass score 70%)
            prac = PracticeTask.objects.create(
                module=mod,
                title=f'Practice Quiz {m_idx}',
                task_type='MCQ_PRACTICE',
                pass_score=70.0,
                content={
                    'questions': [
                        {
                            'id': 'q1',
                            'question': 'What is the output of print(2 ** 3)?',
                            'options': ['6', '8', '9', '5'],
                            'correct_answer': '8'
                        }
                    ]
                },
                is_required=True,
                status='PUBLISHED'
            )
            self.modules.append({
                'module': mod,
                'video': vid,
                'material': mat,
                'practice': prac
            })

        # 3. Assessment for the course
        self.assessment = Assessment.objects.create(
            course=self.course,
            title='Python Fundamentals Final Assessment',
            assessment_type='FINAL_ASSESSMENT',
            duration_minutes=30,
            pass_percentage=70.0,
            max_attempts=3,
            is_published=True,
            camera_required=True,
            screen_share_required=True,
            fullscreen_required=True,
            max_tab_switch_warnings=2
        )
        self.q1 = Question.objects.create(
            assessment=self.assessment,
            text='What is the primary characteristic of a Python tuple?',
            question_type='MCQ_SINGLE',
            marks=10.0
        )
        self.opt1 = QuestionOption.objects.create(question=self.q1, text='Immutable', is_correct=True)
        self.opt2 = QuestionOption.objects.create(question=self.q1, text='Mutable', is_correct=False)

        # 4. Create Student
        self.student = User.objects.create_user(
            username='student_test_1',
            email='student1@fxec.ac.in',
            password='Password123!',
            first_name='Kavitha',
            last_name='S',
            role='STUDENT'
        )
        self.token = generate_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def _complete_module_activities(self, enrollment, mod_data, pass_practice=True, watch_percent=100.0, complete_material=True):
        """Helper to simulate activity completion for a module."""
        mod = mod_data['module']
        vid = mod_data['video']
        mat = mod_data['material']
        prac = mod_data['practice']

        # Video
        vp, _ = VideoProgress.objects.get_or_create(enrollment=enrollment, video=vid)
        watched_sec = int((watch_percent / 100.0) * vid.duration_seconds)
        vp.record_progress(current_seconds=watched_sec, total_duration=vid.duration_seconds)

        # Material
        mp_mat, _ = MaterialProgress.objects.get_or_create(enrollment=enrollment, material=mat)
        if complete_material:
            mp_mat.mark_completed()

        # Practice
        pp, _ = PracticeProgress.objects.get_or_create(enrollment=enrollment, practice=prac)
        score = 100.0 if pass_practice else 50.0
        pp.record_attempt(score=score)

        # Update module and enrollment
        mp, _ = ModuleProgress.objects.get_or_create(enrollment=enrollment, module=mod)
        mp.check_and_update_completion()
        enrollment.update_progress()
        return mp

    def test_01_enrollment_creates_initial_locked_state(self):
        """TEST 1: Enrollment creates initial locked state with 0% progress and locked assessment."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        assert enrollment.progress_percent == 0.0
        assert enrollment.is_completed is False
        is_eligible, _, _, _, reason = enrollment.is_assessment_eligible()
        assert is_eligible is False

        # Verify through API
        res = self.client.get(f'/api/courses/{self.course.id}/assessment-eligibility/')
        assert res.status_code == 200
        data = res.json()
        assert data['is_eligible'] is False
        assert data['can_start'] is False

    def test_02_partial_module_progress_does_not_unlock(self):
        """TEST 2: Partial module progress (only 1 of 8 modules complete) does not unlock assessment."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        self._complete_module_activities(enrollment, self.modules[0])

        enrollment.refresh_from_db()
        assert enrollment.module_progress.filter(is_completed=True).count() == 1
        assert enrollment.progress_percent < 100.0
        is_eligible, _, _, _, _ = enrollment.is_assessment_eligible()
        assert is_eligible is False

        res = self.client.get(f'/api/courses/{self.course.id}/assessment-eligibility/')
        assert res.status_code == 200
        assert res.json()['is_eligible'] is False

    def test_03_video_only_completion_does_not_complete_module(self):
        """TEST 3: Video watched 100% but material and practice omitted leaves module incomplete."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        mod_data = self.modules[0]

        vp, _ = VideoProgress.objects.get_or_create(enrollment=enrollment, video=mod_data['video'])
        vp.record_progress(current_seconds=300, total_duration=300)

        assert vp.is_completed is True
        mp, _ = ModuleProgress.objects.get_or_create(enrollment=enrollment, module=mod_data['module'])
        is_mod_done = mp.check_and_update_completion()
        assert is_mod_done is False
        is_eligible, _, _, _, _ = enrollment.is_assessment_eligible()
        assert is_eligible is False

    def test_04_video_and_material_without_practice_does_not_complete_module(self):
        """TEST 4: Video + Material completed but Practice omitted leaves module incomplete."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        mod_data = self.modules[0]

        vp, _ = VideoProgress.objects.get_or_create(enrollment=enrollment, video=mod_data['video'])
        vp.record_progress(current_seconds=300, total_duration=300)

        mat_p, _ = MaterialProgress.objects.get_or_create(enrollment=enrollment, material=mod_data['material'])
        mat_p.mark_completed()

        mp, _ = ModuleProgress.objects.get_or_create(enrollment=enrollment, module=mod_data['module'])
        is_mod_done = mp.check_and_update_completion()
        assert is_mod_done is False
        is_eligible, _, _, _, _ = enrollment.is_assessment_eligible()
        assert is_eligible is False

    def test_05_failing_practice_task_blocks_module_completion(self):
        """TEST 5: Scoring 50% on practice task (pass threshold 70%) blocks module completion."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        mod_data = self.modules[0]

        mp = self._complete_module_activities(enrollment, mod_data, pass_practice=False)
        assert mp.is_completed is False
        is_eligible, _, _, _, _ = enrollment.is_assessment_eligible()
        assert is_eligible is False

    def test_06_all_required_activities_completed_completes_module(self):
        """TEST 6: Video >= 80%, material completed, practice >= 70% completes module."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        mod_data = self.modules[0]

        # 240/300 = 80% (meets 80% threshold)
        mp = self._complete_module_activities(enrollment, mod_data, pass_practice=True, watch_percent=80.0)
        assert mp.is_completed is True
        enrollment.refresh_from_db()
        assert enrollment.module_progress.filter(module=mod_data['module'], is_completed=True).exists()

    def test_07_seven_of_eight_modules_completed_assessment_remains_locked(self):
        """TEST 7: 7 of 8 modules complete -> Assessment remains strictly locked (HTTP 403 on start)."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        for i in range(7):
            self._complete_module_activities(enrollment, self.modules[i])

        enrollment.refresh_from_db()
        assert enrollment.module_progress.filter(is_completed=True).count() == 7
        assert enrollment.progress_percent < 100.0
        is_eligible, _, _, _, _ = enrollment.is_assessment_eligible()
        assert is_eligible is False

        # Eligibility check
        res = self.client.get(f'/api/courses/{self.course.id}/assessment-eligibility/')
        assert res.json()['is_eligible'] is False

        # Attempt to start assessment directly -> HTTP 403 Forbidden
        start_res = self.client.post(f'/api/assessments/{self.assessment.id}/start/')
        assert start_res.status_code == 403
        assert 'Complete all required modules' in start_res.json()['error']

    def test_08_all_modules_completed_unlocks_assessment(self):
        """TEST 8: All 8 modules complete -> 100% progress and assessment eligibility unlocks."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        for i in range(8):
            self._complete_module_activities(enrollment, self.modules[i])

        enrollment.refresh_from_db()
        assert enrollment.module_progress.filter(is_completed=True).count() == 8
        assert enrollment.progress_percent == 100.0
        is_eligible, _, _, _, _ = enrollment.is_assessment_eligible()
        assert is_eligible is True

        res = self.client.get(f'/api/courses/{self.course.id}/assessment-eligibility/')
        assert res.status_code == 200
        data = res.json()
        assert data['is_eligible'] is True
        assert data['can_start'] is True

    def test_09_start_assessment_succeeds_when_eligible(self):
        """TEST 9: Start assessment succeeds with HTTP 201/200 when student is 100% eligible."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        for i in range(8):
            self._complete_module_activities(enrollment, self.modules[i])

        start_res = self.client.post(f'/api/assessments/{self.assessment.id}/start/')
        assert start_res.status_code in (200, 201)
        data = start_res.json()
        attempt_id = data.get('id') or data.get('attempt_id')
        assert attempt_id is not None
        assert data['status'] == 'IN_PROGRESS'

        attempt = AssessmentAttempt.objects.get(id=attempt_id)
        assert attempt.student == self.student
        assert attempt.status == 'IN_PROGRESS'

    def test_10_ineligible_student_direct_assessment_url_bypass_blocked(self):
        """TEST 10: Ineligible student attempting direct URL/API call gets HTTP 403 Forbidden."""
        other_student = User.objects.create_user(
            username='bypasser_student',
            email='bypass@fxec.ac.in',
            password='Password123!',
            role='STUDENT'
        )
        other_token = generate_jwt_token(other_student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        # Direct call to start attempt without completing modules
        res = self.client.post(f'/api/assessments/{self.assessment.id}/start/')
        assert res.status_code == 403
        assert 'Enrollment required' in res.json()['error'] or 'Complete all required modules' in res.json()['error']

    def test_11_progress_persistence_across_refresh(self):
        """TEST 11: Module and activity completion status persists across browser reload / API query."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        # Complete modules 1 and 2
        self._complete_module_activities(enrollment, self.modules[0])
        self._complete_module_activities(enrollment, self.modules[1])

        # Fetch course progress detail endpoint
        res = self.client.get(f'/api/learning/course-progress/{self.course.id}/')
        assert res.status_code == 200
        data = res.json()
        assert data['progress_percent'] == 25.0  # 2 of 8 modules = 25%

        # Verify module records in API response (JSON dict keys are strings)
        mod_prog = data['module_progress']
        m0_id = str(self.modules[0]['module'].id)
        m1_id = str(self.modules[1]['module'].id)
        m2_id = str(self.modules[2]['module'].id)
        assert mod_prog.get(m0_id) is True
        assert mod_prog.get(m1_id) is True
        assert mod_prog.get(m2_id, False) is False

    def test_12_proctoring_warning_accumulation_and_auto_termination(self):
        """TEST 12: Proctoring warning accumulation and auto-termination on 3rd tab switch."""
        attempt = AssessmentAttempt.objects.create(
            assessment=self.assessment,
            student=self.student,
            status='IN_PROGRESS',
            server_deadline=timezone.now() + timedelta(minutes=30)
        )

        # Violation 1: Tab switch
        v1 = AssessmentSecurityEngine.process_security_event(
            attempt=attempt,
            student=self.student,
            event_type='TAB_SWITCH',
            severity='HIGH'
        )
        assert v1['action_taken'] == 'WARNING_ISSUED'
        assert v1['current_warning_count'] == 1
        assert v1['is_terminated'] is False

        # Fast forward time to bypass debounce
        attempt.proctoring_events.all().update(timestamp=timezone.now() - timedelta(seconds=10))

        # Violation 2: Window blur
        v2 = AssessmentSecurityEngine.process_security_event(
            attempt=attempt,
            student=self.student,
            event_type='WINDOW_BLUR',
            severity='HIGH'
        )
        assert v2['action_taken'] == 'WARNING_ISSUED'
        assert v2['current_warning_count'] == 2
        assert v2['is_terminated'] is False

        attempt.proctoring_events.all().update(timestamp=timezone.now() - timedelta(seconds=10))

        # Violation 3: Tab switch -> Auto-termination
        v3 = AssessmentSecurityEngine.process_security_event(
            attempt=attempt,
            student=self.student,
            event_type='TAB_SWITCH',
            severity='CRITICAL'
        )
        assert v3['action_taken'] == 'AUTO_TERMINATE'
        assert v3['is_terminated'] is True

        attempt.refresh_from_db()
        assert attempt.status == 'TERMINATED_SECURITY_VIOLATION'
        assert 'exceeded allowed threshold' in attempt.termination_reason

    def test_13_passing_assessment_issues_certificate(self):
        """TEST 13: Passing final assessment (score >= 70%) generates verified certificate."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        for i in range(8):
            self._complete_module_activities(enrollment, self.modules[i])

        attempt = AssessmentAttempt.objects.create(
            assessment=self.assessment,
            student=self.student,
            status='PASSED',
            server_deadline=timezone.now() + timedelta(minutes=30),
            score=85.0,
            passed=True,
            review_status='APPROVED'
        )

        # Issue Certificate
        res = self.client.post('/api/certificates/issue/', {'attempt_id': attempt.id})
        assert res.status_code in (200, 201)
        data = res.json()
        assert 'certificate_number' in data
        assert data['certificate_number'].startswith('FXEC-SKILL-')
        assert 'verification_url' in data

        cert = Certificate.objects.get(id=data['certificate_id'])
        assert cert.student == self.student
        assert cert.course == self.course
        assert cert.integrity_hash is not None

        # Idempotency check: duplicate call returns existing certificate
        res_dup = self.client.post('/api/certificates/issue/', {'attempt_id': attempt.id})
        assert res_dup.status_code == 200
        assert res_dup.json()['certificate_number'] == cert.certificate_number

    def test_14_failing_assessment_does_not_issue_certificate(self):
        """TEST 14: Failing final assessment (score < 70%) denies certificate issuance."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        for i in range(8):
            self._complete_module_activities(enrollment, self.modules[i])

        fail_attempt = AssessmentAttempt.objects.create(
            assessment=self.assessment,
            student=self.student,
            status='FAILED',
            server_deadline=timezone.now() + timedelta(minutes=30),
            score=50.0,
            passed=False
        )

        res = self.client.post('/api/certificates/issue/', {'attempt_id': fail_attempt.id})
        assert res.status_code == 400
        assert 'Cannot issue certificate for an unpassed assessment' in res.json()['error']
        assert Certificate.objects.filter(student=self.student, course=self.course).exists() is False
