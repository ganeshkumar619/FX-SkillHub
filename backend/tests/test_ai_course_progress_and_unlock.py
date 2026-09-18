import pytest
import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from catalogue.models import Department, SkillCategory, Course
from catalogue.ai_course_generator_service import AICourseGeneratorService
from learning.models import Enrollment, ModuleProgress
from assessments.models import Assessment, AssessmentAttempt
from certificates.models import Certificate
from authentication.authentication import generate_jwt_token

User = get_user_model()


@pytest.mark.django_db
class TestAICourseProgressAndUnlockJourney:
    """
    Authoritative test suite verifying the end-to-end fix for:
    'FACULTY AI COURSE PROGRESS NOT UPDATING AND FINAL ASSESSMENT NOT UNLOCKING'
    Flow:
    1. Faculty creates AI course via AICourseGeneratorService
    2. Normalize resources: 1 required note, 1 required practice, video
    3. Student enrolls
    4. Initial state: progress 0%, modules 0/4, assessment locked (HTTP 403)
    5. Complete Module 1 -> progress 25%, mod 1 done, assessment still locked (HTTP 403)
    6. Complete Modules 2, 3, 4 -> progress 100%, assessment unlocks
    7. Start Final Assessment succeeds (HTTP 201)
    8. Pass exam -> Certificate issued with verified ID
    """

    def setup_method(self):
        self.client = APIClient()

        # Seed Faculty (Admin/Mentor) & Student
        self.faculty = User.objects.create_user(
            username='prof_ramakrishnan',
            email='ramakrishnan@fxec.ac.in',
            password='FacultyPassword123!',
            role='ADMIN'
        )

        self.student = User.objects.create_user(
            username='selva_kumar_ai',
            email='selva@fxec.ac.in',
            password='StudentPass123!',
            role='STUDENT'
        )

        dept, _ = Department.objects.get_or_create(
            code='CSE',
            defaults={'name': 'Computer Science and Engineering', 'source_type': 'FXEC_OFFICIAL'}
        )
        cat, _ = SkillCategory.objects.get_or_create(
            name='Core Placement Technologies',
            defaults={'source_type': 'FXEC_OFFICIAL'}
        )

        # Faculty generates AI course
        self.gen_res = AICourseGeneratorService.generate_full_course(
            skill_name="Cloud Native Kubernetes Architecture",
            course_name="Kubernetes Microservices Engineering",
            level="INTERMEDIATE",
            target_audience="Final year engineers",
            learning_goal="Deploy distributed container clusters and pass certification",
            creator_user=self.faculty,
            department_code="CSE",
            module_count=4
        )
        self.course = Course.objects.get(id=self.gen_res['course_id'])
        self.final_assessment = Assessment.objects.get(id=self.gen_res['assessment_id'])

        # Authenticate as student
        token = generate_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_ai_course_full_learning_progress_and_assessment_unlock_flow(self):
        # 1. Student enrolls in the AI-generated course
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)

        # 2. Check initial progress
        res_init = self.client.get(f'/api/learning/course-progress/{self.course.slug}/')
        assert res_init.status_code == 200
        init_data = res_init.json()
        assert init_data['progress_percent'] == 0.0
        assert init_data['completed_modules'] == 0
        assert init_data['total_required_modules'] == 4
        assert init_data['assessment_unlocked'] is False
        assert init_data['current_module_id'] is not None

        # 3. Direct access to final assessment must be strictly blocked (HTTP 403)
        start_res = self.client.post(f'/api/assessments/{self.final_assessment.id}/start/')
        assert start_res.status_code == 403
        assert 'Complete all required modules' in start_res.json()['error']

        modules = list(self.course.modules.all().order_by('order'))
        assert len(modules) == 4

        # 4. Student completes Module 1 activities
        mod1 = modules[0]
        mat1 = mod1.materials.filter(is_required=True).first()
        prac1 = mod1.practice_tasks.filter(is_required=True).first()
        vid1 = mod1.videos.first()

        assert mat1 is not None, "Normalized AI module must have exactly 1 required study material"
        assert prac1 is not None, "Normalized AI module must have exactly 1 required practice task"

        # 4a. Mark Video watched
        if vid1:
            vid_res = self.client.post('/api/learning/video/progress/', {
                'video_id': vid1.id,
                'watched_seconds': 300,
                'current_seconds': 300,
                'watch_percentage': 100,
                'is_completed': True
            })
            assert vid_res.status_code == 200

        # 4b. Read Study Material
        mat_res = self.client.post('/api/learning/material/complete/', {
            'material_id': mat1.id
        })
        assert mat_res.status_code == 200

        # 4c. Submit Practice Quiz
        prac_questions = prac1.content.get('questions', [])
        answers = {q['id']: (q.get('correct_answer') or q.get('correct_option', 0)) for q in prac_questions}
        prac_res = self.client.post('/api/learning/practice/submit/', {
            'practice_id': prac1.id,
            'score': 100.0,
            'is_completed': True,
            'answers': answers
        }, format='json')
        assert prac_res.status_code == 200
        assert prac_res.json()['is_completed'] is True

        # 5. Check Module 1 completion & Course Progress increment
        p_res_1 = self.client.get(f'/api/learning/course-progress/{self.course.slug}/')
        p_data_1 = p_res_1.json()
        assert p_data_1['completed_modules'] == 1
        assert p_data_1['progress_percent'] == 25.0
        assert p_data_1['assessment_unlocked'] is False
        assert p_data_1['current_module_id'] == modules[1].id

        # Assessment is STILL strictly locked
        start_res_mid = self.client.post(f'/api/assessments/{self.final_assessment.id}/start/')
        assert start_res_mid.status_code == 403

        # 6. Complete Modules 2, 3, 4 sequentially
        for idx in [1, 2, 3]:
            m = modules[idx]
            m_mat = m.materials.filter(is_required=True).first()
            m_prac = m.practice_tasks.filter(is_required=True).first()
            m_vid = m.videos.first()

            if m_vid:
                self.client.post('/api/learning/video/progress/', {
                    'video_id': m_vid.id,
                    'watched_seconds': 300,
                    'current_seconds': 300,
                    'watch_percentage': 100,
                    'is_completed': True
                })
            self.client.post('/api/learning/material/complete/', {'material_id': m_mat.id})
            q_list = m_prac.content.get('questions', [])
            ans = {q['id']: (q.get('correct_answer') or q.get('correct_option', 0)) for q in q_list}
            self.client.post('/api/learning/practice/submit/', {
                'practice_id': m_prac.id,
                'score': 90.0,
                'is_completed': True,
                'answers': ans
            }, format='json')

        # 7. Verify 100% Course Progress & Final Assessment Unlocked!
        p_res_final = self.client.get(f'/api/learning/course-progress/{self.course.slug}/')
        p_data_final = p_res_final.json()
        assert p_data_final['completed_modules'] == 4
        assert p_data_final['progress_percent'] == 100.0
        assert p_data_final['status'] == 'COMPLETED'
        assert p_data_final['assessment_unlocked'] is True

        # Assessment eligibility endpoint check
        elig_res = self.client.get(f'/api/assessments/{self.final_assessment.id}/eligibility/')
        assert elig_res.status_code == 200
        assert elig_res.json()['eligible'] is True

        # 8. Start Final Assessment NOW SUCCEEDS (HTTP 201 Created)!
        attempt_res = self.client.post(f'/api/assessments/{self.final_assessment.id}/start/')
        assert attempt_res.status_code == 201
        attempt_data = attempt_res.json()
        assert 'id' in attempt_data
        attempt_id = attempt_data['id']

        # 9. Complete attempt with passing score
        attempt = AssessmentAttempt.objects.get(id=attempt_id)
        attempt.status = 'PASSED'
        attempt.passed = True
        attempt.score = 88.0
        attempt.submitted_at = timezone.now()
        attempt.save()

        # 10. Issue Official Certificate
        cert_res = self.client.post('/api/certificates/issue/', {'attempt_id': attempt.id})
        assert cert_res.status_code in (200, 201)
        cert_data = cert_res.json()
        assert 'certificate_number' in cert_data
        assert cert_data['certificate_number'].startswith('FXEC-SKILL-')
        assert 'verification_url' in cert_data

        cert_obj = Certificate.objects.get(id=cert_data['certificate_id'])
        assert cert_obj.student == self.student
        assert cert_obj.course == self.course
        assert cert_obj.is_revoked is False
