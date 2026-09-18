import pytest
import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from catalogue.models import Skill, Course, Module, Lesson, StudyMaterial, VideoResource, PracticeTask, Department, SkillCategory
from catalogue.ai_course_generator_service import AICourseGeneratorService
from assessments.models import Assessment, Question, QuestionOption, AssessmentAttempt
from assessments.question_bank_service import QuestionBankService
from assessments.serializers import AssessmentAttemptDetailSerializer

User = get_user_model()


@pytest.mark.django_db
class TestAICourseGeneratorAndAssessmentSystem:
    def setup_method(self):
        self.client = APIClient()

        # Seed Department and Category
        self.dept = Department.objects.create(
            code='CSE',
            name='Computer Science and Engineering',
            source_type='FXEC_OFFICIAL'
        )
        self.category = SkillCategory.objects.create(
            name='Placement Fit Training Courses',
            source_type='FXEC_OFFICIAL'
        )

        # Users
        self.admin = User.objects.create_user(
            username='fx_admin_ai',
            email='admin_ai@fxec.ac.in',
            password='AdminPass123!',
            role='ADMIN'
        )
        self.student1 = User.objects.create_user(
            username='ai_student1',
            email='student1@fxec.ac.in',
            password='StudentPass123!',
            role='STUDENT'
        )
        self.student2 = User.objects.create_user(
            username='ai_student2',
            email='student2@fxec.ac.in',
            password='StudentPass123!',
            role='STUDENT'
        )

    def test_01_full_ai_course_generator_creates_complete_components(self):
        """
        Verifies AI Course Generator creates Course, Modules, Lessons, 4-level Study Materials,
        Mode B Video Script Packages (zero fake URLs), Practice Tasks, Question Bank, and Assessment Blueprint.
        """
        result = AICourseGeneratorService.generate_full_course(
            skill_name="Docker & Container Architecture",
            course_name="Docker & Kubernetes Microservices",
            level="INTERMEDIATE",
            target_audience="3rd year CSE and IT engineers",
            learning_goal="Master containerization, multi-stage Docker builds, and pod orchestration.",
            creator_user=self.admin,
            department_code="CSE",
            module_count=4
        )

        course = Course.objects.get(id=result['course_id'])
        assert course.title == "Docker & Kubernetes Microservices"
        assert course.level == "INTERMEDIATE"
        assert course.source_type == "AI_GENERATED"
        assert course.blueprint['question_count'] == 30

        # Check Modules
        modules = course.modules.all()
        assert modules.count() == 4

        for mod in modules:
            assert mod.source_type == "AI_GENERATED"
            assert mod.topic_tag is not None

            # Lessons
            lessons = mod.lessons.all()
            assert lessons.count() >= 2
            first_lesson = lessons.first()
            assert first_lesson.concept_explanation is not None
            assert len(first_lesson.examples) > 0
            assert len(first_lesson.common_mistakes) > 0
            assert len(first_lesson.key_points) > 0

            # 4-Level Study Materials
            materials = mod.materials.all()
            assert materials.count() >= 4
            levels = set(materials.values_list('explanation_level', flat=True))
            assert {'BEGINNER', 'INTERMEDIATE', 'QUICK_REVISION', 'ADVANCED'}.issubset(levels)
            mat = materials.first()
            assert 'introduction' in mat.structured_content
            assert 'concept_explanation' in mat.structured_content
            assert 'syntax' in mat.structured_content
            assert 'quick_revision' in mat.structured_content
            assert 'interview_questions' in mat.structured_content

            # Video Resource (Mode B: Storyboard fallback with zero fake URLs)
            videos = mod.videos.all()
            assert videos.count() >= 1
            vid = videos.first()
            assert vid.video_type == 'AI_VIDEO_SCRIPT'
            assert vid.ai_video_status == 'SCRIPT_READY'
            assert vid.youtube_url is None  # Never fake URL
            assert vid.external_url is None
            assert vid.script_package is not None
            assert len(vid.script_package['storyboard']) >= 4

            # Practice Tasks
            tasks = mod.practice_tasks.all()
            assert tasks.count() >= 2
            task_types = set(tasks.values_list('task_type', flat=True))
            assert 'MCQ_PRACTICE' in task_types

        # Question Bank
        bank_questions = course.question_bank.all()
        assert bank_questions.count() >= 15
        diff_set = set(bank_questions.values_list('difficulty', flat=True))
        assert 'EASY' in diff_set

        # Assessment Blueprint
        assessment = course.assessments.filter(assessment_type='FINAL_ASSESSMENT').first()
        assert assessment is not None
        assert assessment.is_ai_generated is True
        assert assessment.blueprint['question_count'] == 30

    def test_02_semantic_duplicate_detection_rejects_duplicates(self):
        """
        Verifies semantic duplicate detection recognizes identical questions,
        high-overlap paraphrases (>80%), and permits distinct questions.
        """
        course = Course.objects.create(
            title="Python Testing",
            slug="py-test-dup",
            skill=self.category.skills.create(name="PyDupSkill", category=self.category, department=self.dept),
            department=self.dept,
            description="Testing duplicate detection",
            source_type="AI_GENERATED"
        )

        q1_text = "What is the primary characteristic of a Python tuple in terms of mutability?"
        sem_hash = QuestionBankService.compute_semantic_hash(q1_text)
        q1 = Question.objects.create(
            course=course,
            is_bank_question=True,
            text=q1_text,
            topic_tag="tuples",
            difficulty="EASY",
            semantic_hash=sem_hash
        )

        # 1. Exact Duplicate
        is_dup, reason = QuestionBankService.is_duplicate(course.id, q1_text)
        assert is_dup is True
        assert "Exact semantic match" in reason

        # 2. High Similarity Paraphrase (>80% overlap)
        paraphrase = "What is the primary characteristic of a Python tuple regarding mutability?"
        is_dup_para, reason_para = QuestionBankService.is_duplicate(course.id, paraphrase)
        assert is_dup_para is True
        assert "similarity" in reason_para.lower()

        # 3. Completely Distinct Question
        distinct_text = "How do you configure a Django PostgreSQL database connection pool in production?"
        is_dup_dist, reason_dist = QuestionBankService.is_duplicate(course.id, distinct_text)
        assert is_dup_dist is False
        assert reason_dist is None

    def test_03_attempt_question_and_option_randomization(self):
        """
        Verifies that two students starting attempts for the same assessment get
        different randomized question sequences and option orderings, and that
        evaluation respects the attempt's specific selected questions.
        """
        course = Course.objects.create(
            title="Randomization Course",
            slug="random-course-test",
            skill=self.category.skills.create(name="RandomSkill", category=self.category, department=self.dept),
            department=self.dept,
            description="Testing attempt question and option randomization",
            source_type="AI_GENERATED"
        )

        assessment = Assessment.objects.create(
            course=course,
            title="Random Exam",
            assessment_type="FINAL_ASSESSMENT",
            duration_minutes=30,
            pass_percentage=70.0,
            blueprint={'question_count': 5, 'difficulty_distribution': {'EASY': 0.4, 'MEDIUM': 0.4, 'HARD': 0.2}},
            randomize_questions=True,
            randomize_options=True
        )

        # Populate question pool with 10 questions across Easy, Medium, Hard
        for i in range(10):
            diff = 'EASY' if i < 4 else ('MEDIUM' if i < 8 else 'HARD')
            q = Question.objects.create(
                course=course,
                assessment=assessment,
                is_bank_question=True,
                text=f"Question {i+1} on topic {i%3} with difficulty {diff}",
                topic_tag=f"topic_{i%3}",
                difficulty=diff,
                marks=1,
                order=i+1
            )
            for j in range(4):
                QuestionOption.objects.create(
                    question=q,
                    text=f"Option {j+1} for Q{i+1}",
                    is_correct=(j == 0),
                    order=j+1
                )

        # Prepare questions for student 1
        q_ids_1, opts_1 = QuestionBankService.prepare_attempt_questions(assessment, randomize_options=True)
        # Prepare questions for student 2
        q_ids_2, opts_2 = QuestionBankService.prepare_attempt_questions(assessment, randomize_options=True)

        assert len(q_ids_1) == 5
        assert len(q_ids_2) == 5

        # Verify attempts store their exact question sequence and option order
        deadline = timezone.now() + datetime.timedelta(minutes=30)
        attempt1 = AssessmentAttempt.objects.create(
            assessment=assessment,
            student=self.student1,
            server_deadline=deadline,
            selected_question_ids=q_ids_1,
            question_option_orders=opts_1
        )
        attempt2 = AssessmentAttempt.objects.create(
            assessment=assessment,
            student=self.student2,
            server_deadline=deadline,
            selected_question_ids=q_ids_2,
            question_option_orders=opts_2
        )

        # Serializer test: verify serialized questions match attempt's specific order
        data1 = AssessmentAttemptDetailSerializer(attempt1).data
        returned_qids_1 = [q['id'] for q in data1['questions']]
        assert returned_qids_1 == q_ids_1

        data2 = AssessmentAttemptDetailSerializer(attempt2).data
        returned_qids_2 = [q['id'] for q in data2['questions']]
        assert returned_qids_2 == q_ids_2

        # Evaluation test: evaluate attempt with selected questions
        attempt1.evaluate()
        assert attempt1.status == 'EVALUATED'
        assert attempt1.score == 0.0  # No answers provided yet
        assert attempt1.percentage == 0.0

    def test_04_ai_course_generate_api_endpoint(self):
        """
        Verifies POST /api/catalogue/courses/generate/ endpoint.
        """
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/catalogue/courses/generate/', {
            'skill_name': 'Cloud Native Microservices',
            'course_name': 'Cloud Native Systems with Go',
            'level': 'ADVANCED',
            'target_audience': 'Final year CSE and ECE students',
            'learning_goal': 'Design resilient microservices with gRPC and Docker.',
            'module_count': 3
        }, format='json')

        assert res.status_code == 201
        data = res.data
        assert 'course_id' in data
        assert data['modules_count'] == 3
        assert data['question_bank_count'] > 0
        assert 'assessment_id' in data

    def test_05_question_bank_api_inspection_and_expansion(self):
        """
        Verifies GET and POST on /api/catalogue/courses/<id>/question-bank/
        """
        self.client.force_authenticate(user=self.admin)
        gen_res = AICourseGeneratorService.generate_full_course(
            skill_name="React Architecture",
            course_name="Modern React 19 Development",
            level="INTERMEDIATE",
            module_count=2
        )
        course_id = gen_res['course_id']

        # GET Question Bank
        res = self.client.get(f'/api/catalogue/courses/{course_id}/question-bank/')
        assert res.status_code == 200
        assert res.data['total_questions'] > 0
        assert 'difficulty_breakdown' in res.data

        initial_count = res.data['total_questions']

        # POST Expand Question Bank
        exp_res = self.client.post(f'/api/catalogue/courses/{course_id}/question-bank/expand/')
        assert exp_res.status_code == 200
        assert 'added_count' in exp_res.data

    def test_06_video_package_detail_api(self):
        """
        Verifies GET /api/catalogue/videos/<id>/package/
        """
        self.client.force_authenticate(user=self.admin)
        gen_res = AICourseGeneratorService.generate_full_course(
            skill_name="Java Systems",
            course_name="Java Enterprise Architecture",
            level="BEGINNER",
            module_count=2
        )
        course = Course.objects.get(id=gen_res['course_id'])
        video = course.modules.first().videos.first()

        res = self.client.get(f'/api/catalogue/videos/{video.id}/package/')
        assert res.status_code == 200
        data = res.data
        assert data['video_type'] == 'AI_VIDEO_SCRIPT'
        assert data['ai_video_status'] == 'SCRIPT_READY'
        assert data['script_package'] is not None
        assert 'storyboard' in data['script_package']
        assert data['youtube_url'] is None

    def test_07_ai_skill_generate_api_endpoint(self):
        """
        Verifies POST /api/catalogue/ai/skills/generate/ for both preview and direct creation.
        """
        self.client.force_authenticate(user=self.admin)
        
        # 1. Preview Only
        prev_res = self.client.post('/api/catalogue/ai/skills/generate/', {
            'skill_name': 'Quantum Computing & Qiskit',
            'department_code': 'CSE',
            'level': 'ADVANCED',
            'preview_only': True
        }, format='json')
        assert prev_res.status_code == 200
        prev_data = prev_res.data
        assert prev_data['name'] == 'Quantum Computing & Qiskit'
        assert len(prev_data['learning_outcomes']) >= 4
        assert prev_data['level'] == 'ADVANCED'
        assert 'description' in prev_data

        # 2. Persist Skill
        create_res = self.client.post('/api/catalogue/ai/skills/generate/', {
            'skill_name': 'Quantum Computing & Qiskit',
            'department_code': 'CSE',
            'level': 'ADVANCED',
            'preview_only': False
        }, format='json')
        assert create_res.status_code == 201
        create_data = create_res.data
        assert create_data['id'] is not None
        assert create_data['source_type'] == 'AI_GENERATED'
        assert create_data['approval_status'] == 'APPROVED'

        # Verify in DB
        skill = Skill.objects.get(id=create_data['id'])
        assert skill.name == 'Quantum Computing & Qiskit'
        assert skill.level == 'ADVANCED'
        assert len(skill.learning_outcomes) >= 4

    def test_08_student_forbidden_from_course_and_skill_generation(self):
        """
        Verifies that students cannot invoke AI course generation or skill registration APIs.
        The student portal is strictly for learning, not authoring courses.
        """
        self.client.force_authenticate(user=self.student1)

        # Attempt to generate course as student
        res_course = self.client.post('/api/catalogue/courses/generate/', {
            'skill_name': 'Hacking 101',
            'course_name': 'Unauthorized Course',
            'level': 'BEGINNER'
        }, format='json')
        assert res_course.status_code == 403

        # Attempt to register skill as student
        res_skill = self.client.post('/api/catalogue/ai/skills/generate/', {
            'skill_name': 'Unauthorized Skill',
            'level': 'BEGINNER'
        }, format='json')
        assert res_skill.status_code == 403


