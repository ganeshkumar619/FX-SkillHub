from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import User
from catalogue.models import Course, Skill, SkillCategory, Module, Lesson
from assessments.models import Assessment, Question, QuestionOption


class FinalAssessmentFacultyAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.faculty = User.objects.create_user(
            username='prof_alan',
            email='alan@institution.edu',
            password='Password123!',
            role='FACULTY'
        )
        self.other_faculty = User.objects.create_user(
            username='prof_ada',
            email='ada@institution.edu',
            password='Password123!',
            role='FACULTY'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin_boss',
            email='admin@institution.edu',
            password='Password123!'
        )

        # Category & Skill
        self.category = SkillCategory.objects.create(name='Computer Science', source_type='MANUAL')
        self.skill = Skill.objects.create(name='Python Programming', category=self.category, level='BEGINNER')

        # Course owned by self.faculty
        self.course = Course.objects.create(
            title='Industrial Python Engineering',
            description='Comprehensive enterprise Python development curriculum',
            skill=self.skill,
            level='INTERMEDIATE',
            created_by=self.faculty
        )

        # Module & Lesson
        self.module = Module.objects.create(
            course=self.course,
            title='Module 1: Generators and Iterators',
            order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Lesson 1: Yield vs Return',
            order=1,
            duration_minutes=20
        )

    def test_faculty_get_initial_assessment_status(self):
        """When no final assessment exists yet, endpoint returns exists: False with default title."""
        self.client.force_authenticate(user=self.faculty)
        res = self.client.get(f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['exists'])
        self.assertIn('Industrial Python Engineering', res.data['default_title'])

    def test_faculty_create_and_update_assessment_settings(self):
        """Faculty can configure pass score, duration, and proctoring parameters."""
        self.client.force_authenticate(user=self.faculty)
        payload = {
            'title': 'Python Engineering Certification Final Exam',
            'duration_minutes': 45,
            'pass_percentage': 75.0,
            'max_attempts': 2,
            'camera_required': True,
            'screen_share_required': True,
            'fullscreen_required': True,
            'face_detection_enabled': True
        }
        res = self.client.post(f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['exists'])
        assessment_data = res.data['assessment']
        self.assertEqual(assessment_data['title'], 'Python Engineering Certification Final Exam')
        self.assertEqual(assessment_data['duration_minutes'], 45)
        self.assertEqual(assessment_data['pass_percentage'], 75.0)
        self.assertEqual(assessment_data['max_attempts'], 2)

    def test_faculty_create_manual_question(self):
        """Faculty can manually add a question with 4 options and designated correct answer."""
        self.client.force_authenticate(user=self.faculty)
        payload = {
            'text': 'Which keyword in Python is used to define a generator function?',
            'topic_tag': 'generators',
            'difficulty': 'MEDIUM',
            'marks': 1,
            'explanation': 'The yield keyword transforms a standard function into a generator.',
            'options': [
                {'text': 'yield', 'is_correct': True},
                {'text': 'generate', 'is_correct': False},
                {'text': 'return', 'is_correct': False},
                {'text': 'emit', 'is_correct': False}
            ]
        }
        res = self.client.post(f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/questions/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        q_data = res.data['question']
        self.assertEqual(q_data['text'], payload['text'])
        self.assertEqual(len(q_data['options']), 4)

        # Check options in database
        correct_opts = [o for o in q_data['options'] if o['is_correct']]
        self.assertEqual(len(correct_opts), 1)
        self.assertEqual(correct_opts[0]['text'], 'yield')

    def test_faculty_update_manual_question(self):
        """Faculty can edit an existing question prompt and change the correct option."""
        self.client.force_authenticate(user=self.faculty)
        # 1. Create question
        assessment = Assessment.objects.create(
            course=self.course,
            assessment_type='FINAL_ASSESSMENT',
            title='Test Exam'
        )
        q = Question.objects.create(
            assessment=assessment,
            course=self.course,
            text='Initial question prompt?',
            difficulty='EASY',
            marks=1
        )
        opt1 = QuestionOption.objects.create(question=q, text='Option A', is_correct=True, order=1)
        opt2 = QuestionOption.objects.create(question=q, text='Option B', is_correct=False, order=2)

        # 2. Update question
        update_payload = {
            'text': 'Updated question prompt about Python iterators?',
            'difficulty': 'HARD',
            'marks': 2,
            'explanation': 'Updated explanation',
            'options': [
                {'text': 'Option A modified', 'is_correct': False},
                {'text': 'Option B modified', 'is_correct': True}
            ]
        }
        res = self.client.put(
            f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/questions/{q.id}/',
            data=update_payload,
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['text'], 'Updated question prompt about Python iterators?')
        self.assertEqual(res.data['difficulty'], 'HARD')
        self.assertEqual(res.data['marks'], 2)

        # Verify Option B is now the correct answer
        q.refresh_from_db()
        correct_opt = q.options.filter(is_correct=True).first()
        self.assertIsNotNone(correct_opt)
        self.assertEqual(correct_opt.text, 'Option B modified')

    def test_faculty_delete_question(self):
        """Faculty can remove questions from the assessment."""
        self.client.force_authenticate(user=self.faculty)
        assessment = Assessment.objects.create(
            course=self.course,
            assessment_type='FINAL_ASSESSMENT',
            title='Delete Test'
        )
        q = Question.objects.create(assessment=assessment, course=self.course, text='To be deleted')
        QuestionOption.objects.create(question=q, text='A', is_correct=True, order=1)

        res = self.client.delete(f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/questions/{q.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(Question.objects.filter(id=q.id).exists())

    def test_faculty_ai_generate_preview_and_batch_save(self):
        """AI generates preview questions, faculty selects them and saves in batch."""
        self.client.force_authenticate(user=self.faculty)

        # 1. Preview mode (auto_save=False)
        preview_res = self.client.post(
            f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/generate-ai-questions/',
            data={'count': 3, 'difficulty': 'ALL', 'auto_save': False},
            format='json'
        )
        self.assertEqual(preview_res.status_code, status.HTTP_200_OK)
        self.assertFalse(preview_res.data['saved'])
        candidates = preview_res.data['questions']
        self.assertEqual(len(candidates), 3)

        # 2. Batch save selected 2 questions
        batch_payload = {'questions': candidates[:2]}
        save_res = self.client.post(
            f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/questions/',
            data=batch_payload,
            format='json'
        )
        self.assertEqual(save_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(save_res.data['saved_count'], 2)

        # 3. Verify in final assessment
        get_res = self.client.get(f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/')
        self.assertEqual(get_res.data['assessment']['questions_count'], 2)

    def test_faculty_ai_generate_autosave(self):
        """1-click AI generation saves questions directly to assessment."""
        self.client.force_authenticate(user=self.faculty)
        res = self.client.post(
            f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/generate-ai-questions/',
            data={'count': 4, 'difficulty': 'MEDIUM', 'auto_save': True},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['saved'])
        self.assertEqual(res.data['generated_count'], 4)
        self.assertEqual(res.data['assessment']['questions_count'], 4)

    def test_unauthorized_faculty_cannot_modify(self):
        """A different faculty member cannot tamper with another faculty's course assessment."""
        self.client.force_authenticate(user=self.other_faculty)
        res = self.client.post(
            f'/api/catalogue/faculty/courses/{self.course.id}/final-assessment/',
            data={'title': 'Hacked'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
