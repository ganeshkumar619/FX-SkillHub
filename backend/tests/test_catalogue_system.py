import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from catalogue.models import (
    Department, 
    SkillCategory, 
    SkillDomain, 
    Skill, 
    Course, 
    Module, 
    Lesson,
    CourseApproval,
    AISkillSuggestion
)
from catalogue.duplicate_detector import check_skill_duplicate
from catalogue.ai_service import AISkillDiscoveryService
from learning.models import Enrollment
from assessments.models import Assessment, AssessmentAttempt, Question, QuestionOption, StudentAnswer
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestCatalogueSystem:
    def setup_method(self):
        self.client = APIClient()
        now = timezone.now()

        # Create Departments
        self.dept_cse = Department.objects.create(
            code='CSE',
            name='Computer Science and Engineering',
            source_type='FXEC_OFFICIAL',
            source_url='https://www.francisxavier.ac.in/departments'
        )
        self.dept_aids = Department.objects.create(
            code='AIDS',
            name='Artificial Intelligence & Data Science',
            source_type='FXEC_OFFICIAL',
            source_url='https://www.francisxavier.ac.in/departments'
        )
        self.dept_mech = Department.objects.create(
            code='MECH',
            name='Mechanical Engineering',
            source_type='FXEC_OFFICIAL',
            source_url='https://www.francisxavier.ac.in/departments'
        )

        # Create Category & Domain
        self.category = SkillCategory.objects.create(
            name='Foundation Course',
            source_type='FXEC_OFFICIAL'
        )
        self.domain = SkillDomain.objects.create(
            category=self.category,
            name='Programming & Computational Logic',
            source_type='FXEC_OFFICIAL'
        )

        # Create Users
        self.admin = User.objects.create_superuser(
            username='admin_test',
            email='admin@fxec.ac.in',
            password='AdminPassword123!',
            role='ADMIN'
        )
        self.faculty = User.objects.create_user(
            username='faculty_test',
            email='faculty@fxec.ac.in',
            password='FacultyPassword123!',
            role='MENTOR'
        )
        self.student = User.objects.create_user(
            username='student_test',
            email='student@fxec.ac.in',
            password='StudentPassword123!',
            role='STUDENT',
            department=self.dept_cse
        )

        # Create Approved Skill & Course
        self.skill = Skill.objects.create(
            name='Python Foundations',
            category=self.category,
            domain=self.domain,
            department=self.dept_cse,
            level='BEGINNER',
            approval_status='APPROVED',
            content_status='PUBLISHED',
            source_type='FXEC_OFFICIAL'
        )

        self.course = Course.objects.create(
            title='Python Programming Mastery',
            slug='python-mastery-test',
            skill=self.skill,
            department=self.dept_cse,
            level='BEGINNER',
            is_published=True,
            approval_status='APPROVED',
            content_status='PUBLISHED',
            source_type='FXEC_OFFICIAL'
        )
        self.course.departments.add(self.dept_cse, self.dept_aids)

        self.mod = Module.objects.create(
            course=self.course,
            order=1,
            title='Variables & Scope',
            topic_tag='python_vars',
            duration_minutes=30
        )
        self.lesson = Lesson.objects.create(
            module=self.mod,
            order=1,
            title='Understanding Dynamic Typing',
            content_type='TEXT'
        )

    # -------------------------------------------------------------
    # 1. Duplicate Detection Tests
    # -------------------------------------------------------------
    def test_duplicate_skill_detection(self):
        # Exact match test
        res_exact = check_skill_duplicate('Python Foundations')
        assert res_exact['is_duplicate'] is True
        assert res_exact['has_exact_match'] is True
        assert res_exact['matches'][0]['match_type'] == 'EXACT'

        # Case-insensitive normalized match
        res_case = check_skill_duplicate('python foundations')
        assert res_case['has_exact_match'] is True

        # Token overlap match (e.g. 'Python Advanced Foundations')
        res_token = check_skill_duplicate('Python Advanced Foundations')
        assert res_token['is_duplicate'] is True
        assert any(m['match_type'] in ['TOKEN_SIMILARITY', 'SUBSTRING'] for m in res_token['matches'])

        # Unique skill should have no duplicates
        res_unique = check_skill_duplicate('Quantum Cryptography Networks')
        assert res_unique['is_duplicate'] is False

    # -------------------------------------------------------------
    # 2. Interdisciplinary & Cross-Department Course Filtering
    # -------------------------------------------------------------
    def test_interdisciplinary_course_filtering(self):
        # Filtering by CSE should return our course
        res_cse = self.client.get('/api/catalogue/courses/?department=CSE')
        assert res_cse.status_code == 200
        titles_cse = [c['title'] for c in res_cse.data.get('results', res_cse.data)]
        assert 'Python Programming Mastery' in titles_cse

        # Filtering by AIDS (second associated department) should also return our course
        res_aids = self.client.get('/api/catalogue/courses/?department=AIDS')
        assert res_aids.status_code == 200
        titles_aids = [c['title'] for c in res_aids.data.get('results', res_aids.data)]
        assert 'Python Programming Mastery' in titles_aids

        # Filtering by MECH should NOT return our course
        res_mech = self.client.get('/api/catalogue/courses/?department=MECH')
        assert res_mech.status_code == 200
        titles_mech = [c['title'] for c in res_mech.data.get('results', res_mech.data)]
        assert 'Python Programming Mastery' not in titles_mech

    # -------------------------------------------------------------
    # 3. Student Permission & Unpublished Visibility Enforcement
    # -------------------------------------------------------------
    def test_student_cannot_see_unpublished_or_draft_courses(self):
        # Create a faculty draft course
        draft_course = Course.objects.create(
            title='Secret Advanced AI Workshop',
            slug='secret-ai-workshop',
            skill=self.skill,
            department=self.dept_aids,
            is_published=False,
            approval_status='DRAFT',
            source_type='FACULTY_CREATED',
            created_by=self.faculty
        )

        # Anonymous/Student list query
        res = self.client.get('/api/catalogue/courses/')
        titles = [c['title'] for c in res.data.get('results', res.data)]
        assert 'Secret Advanced AI Workshop' not in titles

        # Anonymous/Student detail query should 404
        res_detail = self.client.get('/api/catalogue/courses/secret-ai-workshop/')
        assert res_detail.status_code == 404

        # Admin CAN see it
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.get('/api/catalogue/courses/')
        admin_titles = [c['title'] for c in res_admin.data.get('results', res_admin.data)]
        assert 'Secret Advanced AI Workshop' in admin_titles

    # -------------------------------------------------------------
    # 4. Faculty Course Creation, Submit, & Admin Approval Workflow
    # -------------------------------------------------------------
    def test_faculty_course_builder_and_admin_approval_lifecycle(self):
        # 1. Faculty creates draft course with modules & lessons
        self.client.force_authenticate(user=self.faculty)
        payload = {
            'title': 'Applied Cloud Computing',
            'skill_id': self.skill.id,
            'department_id': self.dept_cse.id,
            'description': 'Comprehensive cloud infrastructure course.',
            'estimated_hours': 14,
            'modules': [
                {
                    'order': 1,
                    'title': 'Virtualization & Containers',
                    'lessons': [
                        {'order': 1, 'title': 'Intro to Docker', 'content_type': 'TEXT'}
                    ]
                }
            ]
        }
        res_create = self.client.post('/api/catalogue/faculty/courses/', payload, format='json')
        assert res_create.status_code == 201
        course_id = res_create.data['id']
        assert res_create.data['approval_status'] == 'DRAFT'
        assert res_create.data['is_published'] is False

        # 2. Faculty submits course for review
        res_submit = self.client.post(f'/api/catalogue/faculty/courses/{course_id}/submit-review/', {'notes': 'Ready for review'})
        assert res_submit.status_code == 200
        assert res_submit.data['approval_status'] == 'PENDING_REVIEW'

        # 3. Student still cannot see it
        self.client.force_authenticate(user=self.student)
        res_student = self.client.get('/api/catalogue/courses/')
        titles = [c['title'] for c in res_student.data.get('results', res_student.data)]
        assert 'Applied Cloud Computing' not in titles

        # 4. Admin reviews and approves course
        self.client.force_authenticate(user=self.admin)
        res_approve = self.client.post(f'/api/catalogue/admin/course-proposals/{course_id}/approve/', {'notes': 'Verified and approved'})
        assert res_approve.status_code == 200

        # Verify course is now approved and published
        approved_course = Course.objects.get(id=course_id)
        assert approved_course.approval_status == 'APPROVED'
        assert approved_course.is_published is True
        assert approved_course.approved_by == self.admin

        # 5. Now student CAN see it in public catalogue
        self.client.force_authenticate(user=self.student)
        res_pub = self.client.get('/api/catalogue/courses/')
        pub_titles = [c['title'] for c in res_pub.data.get('results', res_pub.data)]
        assert 'Applied Cloud Computing' in pub_titles

    # -------------------------------------------------------------
    # 5. AI Skill Discovery & Gap Analysis Tests
    # -------------------------------------------------------------
    def test_ai_skill_discovery_and_admin_approval(self):
        # AI discovery creates pending suggestions
        suggestions = AISkillDiscoveryService.discover_skills('Full Stack Web Development')
        assert len(suggestions) > 0
        first_sugg = suggestions[0]
        assert first_sugg['source_type'] == 'AI_SUGGESTED'
        assert first_sugg['approval_status'] == 'PENDING_REVIEW'

        # Admin approves AI suggestion
        self.client.force_authenticate(user=self.admin)
        res_appr = self.client.post(f'/api/catalogue/admin/ai-suggestions/{first_sugg["id"]}/approve/')
        assert res_appr.status_code == 200

        sugg_obj = AISkillSuggestion.objects.get(id=first_sugg['id'])
        assert sugg_obj.approval_status == 'APPROVED'
        assert Skill.objects.filter(name=first_sugg['title']).exists()

    def test_evidence_grounded_skill_gap_analysis(self):
        # Setup assessment attempt for student with genuine topic score
        assessment = Assessment.objects.create(
            course=self.course,
            title='Diagnostic Assessment',
            pass_percentage=70.0
        )
        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            student=self.student,
            status='EVALUATED',
            score=40.0,
            percentage=40.0,
            passed=False,
            topic_breakdown={'python_vars': 40.0},
            server_deadline=timezone.now() + timezone.timedelta(minutes=20)
        )

        analysis = AISkillDiscoveryService.analyze_student_skill_gaps(self.student)
        assert len(analysis['needs_improvement']) > 0
        weak_topic = analysis['needs_improvement'][0]
        assert 'Python Vars' in weak_topic['topic']
        assert weak_topic['average_score'] == 40.0
        assert "Scored 40.0% in Python Vars" in analysis['evidence_summary']
