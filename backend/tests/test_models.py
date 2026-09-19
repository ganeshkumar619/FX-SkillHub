import pytest
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.auth import get_user_model
from catalogue.models import Department, SkillCategory, Skill, Course, Module
from learning.models import Enrollment, ModuleProgress
from assessments.models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from proctoring.models import ProctoringEvent, RiskScore
from certificates.models import Certificate

User = get_user_model()

@pytest.mark.django_db
class TestModelIntegrityAndRules:
    def setup_method(self):
        self.dept, _ = Department.objects.get_or_create(
            code='CSE',
            defaults={
                'name': 'Computer Science and Engineering',
                'source_type': 'FXEC_OFFICIAL',
                'source_url': 'https://www.francisxavier.ac.in/departments'
            }
        )
        self.category = SkillCategory.objects.create(
            name='Foundation Course',
            source_type='FXEC_OFFICIAL'
        )
        self.skill = Skill.objects.create(
            name='Python Foundations',
            category=self.category,
            department=self.dept,
            source_type='FXEC_OFFICIAL'
        )
        self.course = Course.objects.create(
            title='Python Programming',
            slug='python-test-course',
            skill=self.skill,
            department=self.dept,
            source_type='FXEC_OFFICIAL'
        )
        self.mod1 = Module.objects.create(course=self.course, order=1, title='Mod 1', topic_tag='python_vars')
        self.mod2 = Module.objects.create(course=self.course, order=2, title='Mod 2', topic_tag='python_loops')
        
        self.student = User.objects.create_user(
            username='student1',
            email='student1@fxec.ac.in',
            password='Pass123Password!',
            role='STUDENT'
        )

    def test_enrollment_uniqueness_constraint(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        with pytest.raises(IntegrityError):
            # Duplicate enrollment must be rejected by db constraint
            Enrollment.objects.create(student=self.student, course=self.course)

    def test_progress_calculation(self):
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        assert enrollment.progress_percent == 0.0

        p1 = ModuleProgress.objects.create(enrollment=enrollment, module=self.mod1, is_completed=True)
        enrollment.update_progress()
        assert enrollment.progress_percent == 50.0

        p2 = ModuleProgress.objects.create(enrollment=enrollment, module=self.mod2, is_completed=True)
        enrollment.update_progress()
        assert enrollment.progress_percent == 100.0

    def test_assessment_evaluation_and_topic_mastery(self):
        assessment = Assessment.objects.create(
            course=self.course,
            title='Test Exam',
            pass_percentage=70.0
        )
        q1 = Question.objects.create(assessment=assessment, text='Q1?', topic_tag='python_vars', marks=5)
        opt1_corr = QuestionOption.objects.create(question=q1, text='Correct 1', is_correct=True)
        opt1_inc = QuestionOption.objects.create(question=q1, text='Wrong 1', is_correct=False)

        q2 = Question.objects.create(assessment=assessment, text='Q2?', topic_tag='python_loops', marks=5)
        opt2_corr = QuestionOption.objects.create(question=q2, text='Correct 2', is_correct=True)
        opt2_inc = QuestionOption.objects.create(question=q2, text='Wrong 2', is_correct=False)

        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            student=self.student,
            server_deadline=timezone.now() + timezone.timedelta(minutes=30)
        )
        # Answer Q1 correctly
        ans1 = StudentAnswer.objects.create(attempt=attempt, question=q1)
        ans1.selected_options.add(opt1_corr)

        # Answer Q2 incorrectly
        ans2 = StudentAnswer.objects.create(attempt=attempt, question=q2)
        ans2.selected_options.add(opt2_inc)

        attempt.evaluate()
        assert attempt.score == 5.0
        assert attempt.percentage == 50.0
        assert attempt.passed is False # 50% < 70%
        assert attempt.topic_breakdown['python_vars'] == 100.0
        assert attempt.topic_breakdown['python_loops'] == 0.0

    def test_proctoring_risk_score_calculation(self):
        assessment = Assessment.objects.create(course=self.course, title='Proctor Exam')
        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            student=self.student,
            server_deadline=timezone.now() + timezone.timedelta(minutes=30)
        )
        
        # Trigger 2 tab switches and 1 fullscreen exit
        ProctoringEvent.objects.create(attempt=attempt, event_type='TAB_SWITCH', severity='MEDIUM')
        ProctoringEvent.objects.create(attempt=attempt, event_type='TAB_SWITCH', severity='MEDIUM')
        ProctoringEvent.objects.create(attempt=attempt, event_type='FULLSCREEN_EXIT', severity='MEDIUM')

        risk = RiskScore.compute_for_attempt(attempt)
        # 15 + 15 + 20 = 50 pts => HIGH risk
        assert risk.numerical_score == 50.0
        assert risk.tier == 'HIGH'
        assert attempt.review_status == 'PENDING_REVIEW'

    def test_certificate_uniqueness_and_integrity_hash(self):
        enrollment = Enrollment.objects.create(student=self.student, course=self.course, is_completed=True)
        hash_digest = Certificate.generate_integrity_hash(
            cert_id='cert-123',
            student_username=self.student.username,
            course_title=self.course.title,
            issued_iso='2026-09-11T12:00:00'
        )
        assert len(hash_digest) == 64 # Valid SHA-256

        cert = Certificate.objects.create(
            enrollment=enrollment,
            student=self.student,
            course=self.course,
            certificate_number='FXEC-TEST-001',
            integrity_hash=hash_digest,
            qr_url='http://localhost:5173/verify-certificate/cert-123'
        )
        assert cert.certificate_number == 'FXEC-TEST-001'

        # Duplicate certificate for the same enrollment must fail
        with pytest.raises(IntegrityError):
            Certificate.objects.create(
                enrollment=enrollment,
                student=self.student,
                course=self.course,
                certificate_number='FXEC-TEST-002',
                integrity_hash=hash_digest,
                qr_url='http://localhost:5173/verify-certificate/cert-123-dup'
            )
