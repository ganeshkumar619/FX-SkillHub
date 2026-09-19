import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from catalogue.models import (
    Department,
    SkillCategory,
    SkillDomain,
    Skill,
    Course,
    Module
)
from learning.models import Enrollment
from assessments.models import (
    Assessment,
    Question,
    QuestionOption,
    AssessmentAttempt,
    StudentAnswer
)
from assessments.code_execution_service import CodeExecutionService
from assessments.ai_coding_service import AICodingQuestionService
from assessments.serializers import QuestionSafeSerializer, QuestionAdminSerializer
from assessments.question_bank_service import QuestionBankService

User = get_user_model()


@pytest.mark.django_db
class TestCodingAssessmentArchitecture:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        dept, _ = Department.objects.get_or_create(code='CSE', defaults={'name': 'Computer Science and Engineering'})
        cat = SkillCategory.objects.create(name='Software Engineering')
        domain = SkillDomain.objects.create(category=cat, name='Programming Languages')
        
        # 1. Programming skill and course (Python)
        py_skill = Skill.objects.create(name='Python Programming', slug='python-programming', category=cat, domain=domain, department=dept)
        py_course = Course.objects.create(
            title="Python Mastery",
            slug="python-mastery",
            skill=py_skill,
            programming_language='python',
            status="PUBLISHED"
        )
        
        # 2. Programming skill and course (C)
        c_skill = Skill.objects.create(name='C Programming', slug='c-programming', category=cat, domain=domain, department=dept)
        c_course = Course.objects.create(
            title="Systems Programming in C",
            slug="systems-programming-c",
            skill=c_skill,
            programming_language='c',
            status="PUBLISHED"
        )
        
        # 3. Non-programming course (Project Management)
        mgmt_skill = Skill.objects.create(name='Agile Project Management', slug='agile-mgmt', category=cat, domain=domain, department=dept)
        mgmt_course = Course.objects.create(
            title="Agile Delivery",
            slug="agile-delivery",
            skill=mgmt_skill,
            programming_language='',
            status="PUBLISHED"
        )

        # Faculty and Student users
        faculty = User.objects.create_user(
            username="prof_coding",
            email="prof_coding@fx.edu",
            password="Password123!",
            role="FACULTY"
        )
        student = User.objects.create_user(
            username="student_coder",
            email="student_coder@fx.edu",
            password="Password123!",
            role="STUDENT"
        )

        # Final Assessment for Python
        py_assessment = Assessment.objects.create(
            course=py_course,
            title="Python Final Certification Assessment",
            assessment_type="FINAL_ASSESSMENT",
            duration_minutes=60,
            pass_percentage=70.0,
            is_published=True
        )

        # Final Assessment for Non-programming course
        mgmt_assessment = Assessment.objects.create(
            course=mgmt_course,
            title="Agile Final Certification Assessment",
            assessment_type="FINAL_ASSESSMENT",
            duration_minutes=30,
            pass_percentage=70.0,
            is_published=True
        )

        return {
            'py_course': py_course,
            'c_course': c_course,
            'mgmt_course': mgmt_course,
            'faculty': faculty,
            'student': student,
            'py_assessment': py_assessment,
            'mgmt_assessment': mgmt_assessment,
        }

    def test_course_programming_language_detection(self, setup_env):
        env = setup_env
        assert env['py_course'].get_programming_language() == 'python'
        assert env['c_course'].get_programming_language() == 'c'
        assert env['mgmt_course'].get_programming_language() is None

    def test_code_execution_service_python_success(self):
        code = "a, b = map(int, input().split())\nprint(a + b)"
        sample_cases = [
            {'input': '3 5', 'output': '8'},
            {'input': '10 20', 'output': '30'}
        ]
        res = CodeExecutionService.evaluate_code('python', code, sample_cases, is_submission=False)
        assert res['all_sample_passed'] is True
        assert res['sample_passed'] == 2
        assert len(res['sample_results']) == 2
        assert res['sample_results'][0]['actual_output'] == '8'
        assert res['sample_results'][0]['passed'] is True

    def test_code_execution_service_timeout(self):
        infinite_code = "while True:\n    pass"
        sample_cases = [{'input': '1', 'output': '1'}]
        res = CodeExecutionService.evaluate_code('python', infinite_code, sample_cases, is_submission=False)
        assert res['all_sample_passed'] is False
        assert 'TIME_LIMIT_EXCEEDED' in res['sample_results'][0]['status']

    def test_ai_coding_service_easy_question_generation(self, setup_env):
        env = setup_env
        # Generate question for Python course
        q_data, err = AICodingQuestionService.generate_and_validate_question(
            course_id=env['py_course'].id,
            preferred_language='python'
        )
        assert err is None
        assert q_data is not None
        assert q_data['difficulty'] == 'EASY'
        assert q_data['programming_language'] == 'python'
        assert len(q_data['sample_test_cases']) == 2
        assert len(q_data['hidden_test_cases']) == 4
        assert q_data['reference_solution'] is not None

        # Verify reference solution passes all 6 test cases in sandbox
        val_success, val_err = CodeExecutionService.validate_reference_solution(
            language='python',
            reference_solution=q_data['reference_solution'],
            sample_test_cases=q_data['sample_test_cases'],
            hidden_test_cases=q_data['hidden_test_cases']
        )
        assert val_success is True
        assert val_err is None

    def test_safe_serialization_strictly_hides_hidden_cases(self, setup_env):
        env = setup_env
        q = Question.objects.create(
            course=env['py_course'],
            assessment=env['py_assessment'],
            text="Sum of Two Numbers",
            title="Sum of Two Numbers",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            problem_statement="Read two integers and print their sum.",
            sample_test_cases=[
                {'input': '1 2', 'output': '3'},
                {'input': '5 10', 'output': '15'}
            ],
            hidden_test_cases=[
                {'input': '100 200', 'output': '300'},
                {'input': '0 0', 'output': '0'},
                {'input': '-5 5', 'output': '0'},
                {'input': '9999 1', 'output': '10000'}
            ],
            reference_solution="a, b = map(int, input().split())\nprint(a + b)",
            marks=10
        )

        safe_data = QuestionSafeSerializer(q).data
        # Safe serializer must include visible sample test cases
        assert len(safe_data['sample_test_cases']) == 2
        assert safe_data['problem_statement'] == "Read two integers and print their sum."
        # Safe serializer MUST strictly NOT contain hidden_test_cases or reference_solution
        assert 'hidden_test_cases' not in safe_data
        assert 'reference_solution' not in safe_data

        # Admin serializer contains everything for faculty
        admin_data = QuestionAdminSerializer(q).data
        assert len(admin_data['hidden_test_cases']) == 4
        assert admin_data['reference_solution'] is not None

    def test_run_code_api_sample_test_cases_only(self, setup_env):
        env = setup_env
        q = Question.objects.create(
            course=env['py_course'],
            assessment=env['py_assessment'],
            text="Double the Number",
            title="Double the Number",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            sample_test_cases=[
                {'input': '4', 'output': '8'},
                {'input': '10', 'output': '20'}
            ],
            hidden_test_cases=[
                {'input': '0', 'output': '0'},
                {'input': '-3', 'output': '-6'},
                {'input': '50', 'output': '100'},
                {'input': '1000', 'output': '2000'}
            ],
            reference_solution="print(int(input()) * 2)",
            marks=10
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])

        attempt = AssessmentAttempt.objects.create(
            assessment=env['py_assessment'],
            student=env['student'],
            status='IN_PROGRESS',
            server_deadline=timezone.now() + timedelta(hours=1),
            selected_question_ids=[q.id]
        )

        # Run valid Python code
        run_res = client.post(
            f"/api/assessments/attempts/{attempt.id}/run-code/",
            data={'question_id': q.id, 'code': 'n = int(input())\nprint(n * 2)', 'language': 'python'},
            format='json'
        )
        assert run_res.status_code == 200
        assert run_res.data['sample_passed'] == 2
        assert run_res.data['all_sample_passed'] is True
        # Run code does NOT return hidden test cases
        assert 'hidden_summary' not in run_res.data

    def test_run_code_language_mismatch_rejected(self, setup_env):
        env = setup_env
        q = Question.objects.create(
            course=env['py_course'],
            assessment=env['py_assessment'],
            text="Double the Number",
            question_type="CODING",
            programming_language="python",
            sample_test_cases=[{'input': '1', 'output': '2'}, {'input': '2', 'output': '4'}],
            hidden_test_cases=[{'input': '3', 'output': '6'}, {'input': '4', 'output': '8'}, {'input': '5', 'output': '10'}, {'input': '6', 'output': '12'}],
            marks=10
        )
        client = APIClient()
        client.force_authenticate(user=env['student'])
        attempt = AssessmentAttempt.objects.create(
            assessment=env['py_assessment'],
            student=env['student'],
            status='IN_PROGRESS',
            server_deadline=timezone.now() + timedelta(hours=1),
            selected_question_ids=[q.id]
        )

        # Send Java for a Python question
        run_res = client.post(
            f"/api/assessments/attempts/{attempt.id}/run-code/",
            data={'question_id': q.id, 'code': 'System.out.println(1);', 'language': 'java'},
            format='json'
        )
        assert run_res.status_code == 400
        assert "Language mismatch" in run_res.data['error']

    def test_submit_code_evaluates_all_six_cases_and_proportional_marks(self, setup_env):
        env = setup_env
        q = Question.objects.create(
            course=env['py_course'],
            assessment=env['py_assessment'],
            text="Absolute Difference",
            title="Absolute Difference",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            sample_test_cases=[
                {'input': '5 3', 'output': '2'},
                {'input': '10 20', 'output': '10'}
            ],
            hidden_test_cases=[
                {'input': '100 100', 'output': '0'},
                {'input': '0 7', 'output': '7'},
                {'input': '-5 -10', 'output': '5'},
                {'input': '50 20', 'output': '30'}
            ],
            marks=10
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])
        attempt = AssessmentAttempt.objects.create(
            assessment=env['py_assessment'],
            student=env['student'],
            status='IN_PROGRESS',
            server_deadline=timezone.now() + timedelta(hours=1),
            selected_question_ids=[q.id]
        )

        # 1. Submit fully correct solution
        correct_code = "a, b = map(int, input().split())\nprint(abs(a - b))"
        submit_res = client.post(
            f"/api/assessments/attempts/{attempt.id}/submit-code/",
            data={'question_id': q.id, 'code': correct_code, 'language': 'python'},
            format='json'
        )
        assert submit_res.status_code == 200
        assert submit_res.data['total_passed'] == 6
        assert submit_res.data['total_count'] == 6
        assert submit_res.data['passed'] is True
        assert submit_res.data['marks_obtained'] == 10.0
        # Check hidden test cases summary: does not leak input or expected output
        hidden_results = submit_res.data['hidden_summary']['results']
        assert len(hidden_results) == 4
        for hr in hidden_results:
            assert 'input' not in hr
            assert 'expected_output' not in hr
            assert hr['passed'] is True

        # Check StudentAnswer recorded in database
        attempt.refresh_from_db()
        ans = StudentAnswer.objects.get(attempt=attempt, question=q)
        assert ans.test_cases_passed == 6
        assert ans.total_test_cases == 6
        assert ans.marks_obtained == 10.0
        assert ans.is_correct is True

    def test_partial_marks_for_partial_pass(self, setup_env):
        env = setup_env
        # Question with test cases where faulty solution fails on negative numbers
        q = Question.objects.create(
            course=env['py_course'],
            assessment=env['py_assessment'],
            text="Positive Difference",
            title="Positive Difference",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            sample_test_cases=[
                {'input': '10 5', 'output': '5'},
                {'input': '20 10', 'output': '10'}
            ],
            hidden_test_cases=[
                {'input': '30 10', 'output': '20'},
                {'input': '5 10', 'output': '5'},  # a - b gives -5 if no abs()
                {'input': '0 10', 'output': '10'}, # a - b gives -10 if no abs()
                {'input': '100 50', 'output': '50'}
            ],
            marks=12
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])
        attempt = AssessmentAttempt.objects.create(
            assessment=env['py_assessment'],
            student=env['student'],
            status='IN_PROGRESS',
            server_deadline=timezone.now() + timedelta(hours=1),
            selected_question_ids=[q.id]
        )

        # Code without abs() will pass 4 cases (sample 1, sample 2, hidden 1, hidden 4) and fail 2 cases
        faulty_code = "a, b = map(int, input().split())\nprint(a - b)"
        submit_res = client.post(
            f"/api/assessments/attempts/{attempt.id}/submit-code/",
            data={'question_id': q.id, 'code': faulty_code, 'language': 'python'},
            format='json'
        )
        assert submit_res.status_code == 200
        assert submit_res.data['total_passed'] == 4
        assert submit_res.data['total_count'] == 6
        assert submit_res.data['passed'] is False
        # 4/6 * 12 = 8.0 marks
        assert submit_res.data['marks_obtained'] == 8.0

    def test_question_bank_service_includes_coding_question_for_programming_course(self, setup_env):
        env = setup_env
        # Create MCQ questions
        for i in range(3):
            q_mcq = Question.objects.create(
                course=env['py_course'],
                assessment=env['py_assessment'],
                text=f"Python Concept MCQ {i+1}",
                question_type="MCQ_SINGLE",
                difficulty="EASY",
                marks=1,
                status="ACTIVE",
                is_bank_question=True
            )
            QuestionOption.objects.create(question=q_mcq, text="Option A", is_correct=True, order=1)
            QuestionOption.objects.create(question=q_mcq, text="Option B", is_correct=False, order=2)

        # Create Coding Question
        q_code = Question.objects.create(
            course=env['py_course'],
            assessment=env['py_assessment'],
            text="Python Coding Challenge",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            sample_test_cases=[{'input': '1', 'output': '1'}, {'input': '2', 'output': '2'}],
            hidden_test_cases=[{'input': '3', 'output': '3'}, {'input': '4', 'output': '4'}, {'input': '5', 'output': '5'}, {'input': '6', 'output': '6'}],
            marks=10,
            status="ACTIVE",
            is_bank_question=True
        )

        # Prepare attempt questions
        selected_ids, _ = QuestionBankService.prepare_attempt_questions(env['py_assessment'])
        assert q_code.id in selected_ids

    def test_question_bank_service_does_not_force_coding_for_non_programming_course(self, setup_env):
        env = setup_env
        for i in range(3):
            q_mcq = Question.objects.create(
                course=env['mgmt_course'],
                assessment=env['mgmt_assessment'],
                text=f"Agile Concept MCQ {i+1}",
                question_type="MCQ_SINGLE",
                difficulty="EASY",
                marks=1,
                status="ACTIVE",
                is_bank_question=True
            )
            QuestionOption.objects.create(question=q_mcq, text="Option A", is_correct=True, order=1)
            QuestionOption.objects.create(question=q_mcq, text="Option B", is_correct=False, order=2)

        selected_ids, _ = QuestionBankService.prepare_attempt_questions(env['mgmt_assessment'])
        questions = Question.objects.filter(id__in=selected_ids)
        assert all(q.question_type != 'CODING' for q in questions)

    def test_ai_coding_question_requires_faculty_review_before_publishing(self, setup_env):
        env = setup_env
        client = APIClient()
        client.force_authenticate(user=env['faculty'])

        # 1. Faculty generates AI coding question for Python course
        gen_res = client.post(
            "/api/assessments/coding-questions/ai-generate/",
            data={'course_id': env['py_course'].id, 'programming_language': 'python'},
            format='json'
        )
        assert gen_res.status_code == 201
        q_id = gen_res.data['id']
        assert gen_res.data['difficulty'] == 'EASY'
        assert gen_res.data['approval_status'] == 'PENDING_REVIEW'
        assert len(gen_res.data['sample_test_cases']) == 2
        assert len(gen_res.data['hidden_test_cases']) == 4

        # 2. Verify QuestionBankService does NOT select this unapproved AI question
        selected_ids, _ = QuestionBankService.prepare_attempt_questions(env['py_assessment'])
        assert q_id not in selected_ids

        # 3. Faculty reviews and publishes the question
        pub_res = client.post(f"/api/assessments/coding-questions/{q_id}/publish/", format='json')
        assert pub_res.status_code == 200
        assert pub_res.data['question']['approval_status'] == 'APPROVED'

        # 4. QuestionBankService now selects the approved coding question for the final assessment!
        selected_ids, _ = QuestionBankService.prepare_attempt_questions(env['py_assessment'])
        assert q_id in selected_ids

    def test_manual_coding_question_enforces_exact_two_sample_and_four_hidden_cases(self, setup_env):
        env = setup_env
        client = APIClient()
        client.force_authenticate(user=env['faculty'])

        # Invalid: only 1 sample test case
        invalid_res_1 = client.post(
            f"/api/assessments/courses/{env['py_course'].id}/coding-questions/",
            data={
                'title': 'Invalid Sample Count',
                'problem_statement': 'Print 1',
                'programming_language': 'python',
                'sample_test_cases': [{'input': '1', 'output': '1'}],
                'hidden_test_cases': [{'input': '2', 'output': '2'}, {'input': '3', 'output': '3'}, {'input': '4', 'output': '4'}, {'input': '5', 'output': '5'}],
                'reference_solution': 'print(input())'
            },
            format='json'
        )
        assert invalid_res_1.status_code == 400
        assert 'Exactly 2 sample test cases required' in str(invalid_res_1.data)

        # Invalid: only 3 hidden test cases
        invalid_res_2 = client.post(
            f"/api/assessments/courses/{env['py_course'].id}/coding-questions/",
            data={
                'title': 'Invalid Hidden Count',
                'problem_statement': 'Print 1',
                'programming_language': 'python',
                'sample_test_cases': [{'input': '1', 'output': '1'}, {'input': '2', 'output': '2'}],
                'hidden_test_cases': [{'input': '3', 'output': '3'}, {'input': '4', 'output': '4'}, {'input': '5', 'output': '5'}],
                'reference_solution': 'print(input())'
            },
            format='json'
        )
        assert invalid_res_2.status_code == 400
        assert 'Exactly 4 hidden test cases required' in str(invalid_res_2.data)

        # Valid: exactly 2 sample + 4 hidden
        valid_res = client.post(
            f"/api/assessments/courses/{env['py_course'].id}/coding-questions/",
            data={
                'title': 'Square of Number',
                'problem_statement': 'Read an integer and print its square.',
                'programming_language': 'python',
                'sample_test_cases': [{'input': '2', 'output': '4'}, {'input': '3', 'output': '9'}],
                'hidden_test_cases': [{'input': '4', 'output': '16'}, {'input': '5', 'output': '25'}, {'input': '0', 'output': '0'}, {'input': '10', 'output': '100'}],
                'reference_solution': 'n = int(input())\nprint(n * n)'
            },
            format='json'
        )
        assert valid_res.status_code == 201
        assert valid_res.data['approval_status'] == 'APPROVED'
        assert len(valid_res.data['sample_test_cases']) == 2
        assert len(valid_res.data['hidden_test_cases']) == 4

    def test_hidden_test_cases_strictly_unexposed_to_student(self, setup_env):
        env = setup_env
        q = Question.objects.create(
            course=env['py_course'],
            assessment=env['py_assessment'],
            text="Cube of Number",
            title="Cube of Number",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            sample_test_cases=[
                {'input': '2', 'output': '8'},
                {'input': '3', 'output': '27'}
            ],
            hidden_test_cases=[
                {'input': '4', 'output': '64'},
                {'input': '5', 'output': '125'},
                {'input': '0', 'output': '0'},
                {'input': '1', 'output': '1'}
            ],
            reference_solution="n = int(input())\nprint(n ** 3)",
            marks=10,
            approval_status='APPROVED'
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])

        attempt = AssessmentAttempt.objects.create(
            assessment=env['py_assessment'],
            student=env['student'],
            status='IN_PROGRESS',
            server_deadline=timezone.now() + timedelta(hours=1),
            selected_question_ids=[q.id]
        )

        # Attempt detail endpoint (student examination)
        res = client.get(f"/api/assessments/attempts/{attempt.id}/")
        assert res.status_code == 200
        questions_payload = res.data['questions']
        target_q = next(item for item in questions_payload if item['id'] == q.id)

        # Strict checks:
        assert 'sample_test_cases' in target_q
        assert len(target_q['sample_test_cases']) == 2
        assert 'hidden_test_cases' not in target_q
        assert 'reference_solution' not in target_q


@pytest.mark.django_db
class TestCodingQuestionBugFixVerification:
    @pytest.fixture
    def setup_data(self):
        dept = Department.objects.create(code='CSE2', name='Computer Science and Engineering')
        cat = SkillCategory.objects.create(name='Software Eng')
        domain = SkillDomain.objects.create(category=cat, name='Programming')

        py_skill = Skill.objects.create(name='Python Advanced', slug='python-adv', category=cat, domain=domain, department=dept)
        course_a = Course.objects.create(
            title="Programming in Python",
            slug="programming-in-python",
            skill=py_skill,
            programming_language='python',
            status="PUBLISHED"
        )

        c_skill = Skill.objects.create(name='C Embedded', slug='c-embedded', category=cat, domain=domain, department=dept)
        course_b = Course.objects.create(
            title="Systems in C",
            slug="systems-in-c",
            skill=c_skill,
            programming_language='c',
            status="PUBLISHED"
        )

        mgmt_skill = Skill.objects.create(name='Business Operations', slug='biz-ops', category=cat, domain=domain, department=dept)
        course_non_prog = Course.objects.create(
            title="Business Operations 101",
            slug="biz-ops-101",
            skill=mgmt_skill,
            programming_language='',
            status="PUBLISHED"
        )

        faculty = User.objects.create_user(
            username="faculty_lead",
            email="faculty_lead@fx.edu",
            password="Password123!",
            role="FACULTY"
        )
        course_a.created_by = faculty
        course_a.save()
        course_b.created_by = faculty
        course_b.save()
        course_non_prog.created_by = faculty
        course_non_prog.save()

        student = User.objects.create_user(
            username="student_verified",
            email="student_verified@fx.edu",
            password="Password123!",
            role="STUDENT"
        )

        # Enroll student in courses so they are assessment eligible
        Enrollment.objects.create(student=student, course=course_a)
        Enrollment.objects.create(student=student, course=course_b)
        Enrollment.objects.create(student=student, course=course_non_prog)

        return {
            'course_a': course_a,
            'course_b': course_b,
            'course_non_prog': course_non_prog,
            'faculty': faculty,
            'student': student,
        }

    def test_requirement_a_faculty_creates_coding_question_saved_with_course_id(self, setup_data):
        """Test A: Faculty creates coding question -> saved with correct course_id."""
        env = setup_data
        client = APIClient()
        client.force_authenticate(user=env['faculty'])

        res = client.post(
            f"/api/assessments/courses/{env['course_a'].id}/coding-questions/",
            data={
                'title': 'Reverse String',
                'problem_statement': 'Reverse the given string from stdin.',
                'programming_language': 'python',
                'difficulty': 'EASY',
                'input_format': 'A single line containing string S.',
                'output_format': 'Reversed string S.',
                'constraints': '1 <= |S| <= 1000',
                'sample_test_cases': [
                    {'input': 'hello', 'expected_output': 'olleh'},
                    {'input': 'world', 'expected_output': 'dlrow'}
                ],
                'hidden_test_cases': [
                    {'input': 'python', 'expected_output': 'nohtyp'},
                    {'input': 'racecar', 'expected_output': 'racecar'},
                    {'input': 'a', 'expected_output': 'a'},
                    {'input': '12345', 'expected_output': '54321'}
                ],
                'reference_solution': 'print(input()[::-1])'
            },
            format='json'
        )
        assert res.status_code == 201
        created_id = res.data['id']
        question = Question.objects.get(id=created_id)
        assert question.course_id == env['course_a'].id
        assert question.programming_language == 'python'
        assert question.approval_status == 'APPROVED'
        assert question.question_type == 'CODING'

    def test_requirement_b_published_coding_question_appears_in_final_assessment(self, setup_data):
        """Test B: Published coding question -> appears in student's Final Assessment."""
        env = setup_data
        # Faculty creates and attaches coding question to course_a
        q = Question.objects.create(
            course=env['course_a'],
            text="Square Number",
            title="Square Number",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            problem_statement="Read integer N and print N*N.",
            input_format="Integer N",
            output_format="Integer N*N",
            constraints="1 <= N <= 1000",
            sample_test_cases=[
                {'input': '2', 'expected_output': '4'},
                {'input': '5', 'expected_output': '25'}
            ],
            hidden_test_cases=[
                {'input': '3', 'expected_output': '9'},
                {'input': '10', 'expected_output': '100'},
                {'input': '0', 'expected_output': '0'},
                {'input': '12', 'expected_output': '144'}
            ],
            reference_solution="n = int(input())\nprint(n * n)",
            approval_status="APPROVED",
            status="ACTIVE",
            is_bank_question=True
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])

        # 1. Check Course Final Assessment endpoint
        res = client.get(f"/api/assessments/course/{env['course_a'].id}/final-assessment/")
        assert res.status_code == 200
        assert res.data['assessment_type'] == 'CODING'
        assert res.data['coding_question'] is not None
        assert res.data['coding_question']['id'] == q.id
        assert res.data['coding_question']['title'] == "Square Number"
        assert len(res.data['coding_question']['sample_test_cases']) == 2

        # 2. Student starts assessment attempt
        assessment_id = res.data['id']
        start_res = client.post(f"/api/assessments/{assessment_id}/start/", format='json')
        assert start_res.status_code == 201
        assert start_res.data['assessment_type'] == 'CODING'
        assert start_res.data['coding_question'] is not None
        assert start_res.data['coding_question']['id'] == q.id

        # 3. Student loads attempt detail
        attempt_id = start_res.data['id']
        attempt_res = client.get(f"/api/assessments/attempts/{attempt_id}/")
        assert attempt_res.status_code == 200
        assert attempt_res.data['assessment_type'] == 'CODING'
        assert attempt_res.data['coding_question'] is not None
        assert attempt_res.data['coding_question']['id'] == q.id
        # Questions list also contains the coding question
        questions = attempt_res.data['questions']
        assert any(item['id'] == q.id and item['question_type'] == 'CODING' for item in questions)

    def test_requirement_c_draft_coding_question_does_not_appear(self, setup_data):
        """Test C: Draft coding question -> does not appear if workflow requires publishing."""
        env = setup_data
        draft_q = Question.objects.create(
            course=env['course_a'],
            text="Unreviewed Draft Challenge",
            title="Unreviewed Draft Challenge",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            approval_status="PENDING_REVIEW",  # Not approved yet
            status="ACTIVE",
            sample_test_cases=[{'input': '1', 'expected_output': '1'}, {'input': '2', 'expected_output': '2'}],
            hidden_test_cases=[{'input': '3', 'expected_output': '3'}, {'input': '4', 'expected_output': '4'}, {'input': '5', 'expected_output': '5'}, {'input': '6', 'expected_output': '6'}]
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])

        res = client.get(f"/api/assessments/course/{env['course_a'].id}/final-assessment/")
        # Draft question must NOT appear as the active coding question
        assert res.data.get('coding_question') is None
        assert res.data.get('assessment_type') != 'CODING'

    def test_requirement_d_course_filtering_strict_isolation(self, setup_data):
        """Test D: Course filtering -> Course A gets only Course A coding question."""
        env = setup_data
        qa = Question.objects.create(
            course=env['course_a'],
            text="Question A for Python",
            title="Question A for Python",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            approval_status="APPROVED",
            status="ACTIVE",
            is_bank_question=True,
            sample_test_cases=[{'input': '1', 'expected_output': '1'}, {'input': '2', 'expected_output': '2'}],
            hidden_test_cases=[{'input': '3', 'expected_output': '3'}, {'input': '4', 'expected_output': '4'}, {'input': '5', 'expected_output': '5'}, {'input': '6', 'expected_output': '6'}]
        )

        qb = Question.objects.create(
            course=env['course_b'],
            text="Question B for C",
            title="Question B for C",
            question_type="CODING",
            difficulty="EASY",
            programming_language="c",
            approval_status="APPROVED",
            status="ACTIVE",
            is_bank_question=True,
            sample_test_cases=[{'input': 'A', 'expected_output': 'A'}, {'input': 'B', 'expected_output': 'B'}],
            hidden_test_cases=[{'input': 'C', 'expected_output': 'C'}, {'input': 'D', 'expected_output': 'D'}, {'input': 'E', 'expected_output': 'E'}, {'input': 'F', 'expected_output': 'F'}]
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])

        # Course A final assessment must get qa, NEVER qb
        res_a = client.get(f"/api/assessments/course/{env['course_a'].id}/final-assessment/")
        assert res_a.status_code == 200
        assert res_a.data['coding_question']['id'] == qa.id
        assert res_a.data['coding_question']['id'] != qb.id

        # Course B final assessment must get qb, NEVER qa
        res_b = client.get(f"/api/assessments/course/{env['course_b'].id}/final-assessment/")
        assert res_b.status_code == 200
        assert res_b.data['coding_question']['id'] == qb.id
        assert res_b.data['coding_question']['id'] != qa.id

    def test_requirement_e_non_programming_course_no_coding_question(self, setup_data):
        """Test E: Non-programming course -> no coding question shown."""
        env = setup_data
        Assessment.objects.create(
            course=env['course_non_prog'],
            title="Business Ops Certification",
            assessment_type="FINAL_ASSESSMENT",
            duration_minutes=30,
            pass_percentage=50.0,
            is_published=True
        )
        client = APIClient()
        client.force_authenticate(user=env['student'])

        res = client.get(f"/api/assessments/course/{env['course_non_prog'].id}/final-assessment/")
        assert res.status_code == 200
        assert res.data.get('coding_question') is None
        assert res.data.get('assessment_type') != 'CODING'

    def test_requirement_f_programming_course_exactly_one_coding_question(self, setup_data):
        """Test F: Programming course -> exactly one coding question shown."""
        env = setup_data
        # Create two approved coding questions for Course A
        q1 = Question.objects.create(
            course=env['course_a'],
            text="Coding Challenge 1",
            title="Coding Challenge 1",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            approval_status="APPROVED",
            status="ACTIVE",
            is_bank_question=True,
            order=1,
            sample_test_cases=[{'input': '1', 'expected_output': '1'}, {'input': '2', 'expected_output': '2'}],
            hidden_test_cases=[{'input': '3', 'expected_output': '3'}, {'input': '4', 'expected_output': '4'}, {'input': '5', 'expected_output': '5'}, {'input': '6', 'expected_output': '6'}]
        )
        q2 = Question.objects.create(
            course=env['course_a'],
            text="Coding Challenge 2",
            title="Coding Challenge 2",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            approval_status="APPROVED",
            status="ACTIVE",
            is_bank_question=True,
            order=2,
            sample_test_cases=[{'input': '1', 'expected_output': '1'}, {'input': '2', 'expected_output': '2'}],
            hidden_test_cases=[{'input': '3', 'expected_output': '3'}, {'input': '4', 'expected_output': '4'}, {'input': '5', 'expected_output': '5'}, {'input': '6', 'expected_output': '6'}]
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])

        # API returns exactly one coding question
        res = client.get(f"/api/assessments/course/{env['course_a'].id}/final-assessment/")
        assert res.status_code == 200
        assert res.data['coding_question'] is not None
        assert isinstance(res.data['coding_question'], dict)

        # In attempt start, exactly one coding question is selected
        assessment_id = res.data['id']
        start_res = client.post(f"/api/assessments/{assessment_id}/start/", format='json')
        assert start_res.status_code == 201
        selected_coding_qs = [
            q for q in start_res.data.get('questions', [])
            if q.get('question_type') == 'CODING'
        ]
        assert len(selected_coding_qs) == 1

    def test_requirement_g_and_h_hidden_tests_never_exposed_and_exactly_two_samples(self, setup_data):
        """Test G & H: Hidden tests never appear; exactly 2 sample test cases returned."""
        env = setup_data
        q = Question.objects.create(
            course=env['course_a'],
            text="Security Verification Problem",
            title="Security Verification Problem",
            question_type="CODING",
            difficulty="EASY",
            programming_language="python",
            approval_status="APPROVED",
            status="ACTIVE",
            is_bank_question=True,
            sample_test_cases=[
                {'input': 'S1', 'expected_output': 'ANS1'},
                {'input': 'S2', 'expected_output': 'ANS2'}
            ],
            hidden_test_cases=[
                {'input': 'H1_SECRET_INPUT', 'expected_output': 'H1_SECRET_OUTPUT'},
                {'input': 'H2_SECRET_INPUT', 'expected_output': 'H2_SECRET_OUTPUT'},
                {'input': 'H3_SECRET_INPUT', 'expected_output': 'H3_SECRET_OUTPUT'},
                {'input': 'H4_SECRET_INPUT', 'expected_output': 'H4_SECRET_OUTPUT'}
            ],
            reference_solution="SECRET_REFERENCE_CODE_DO_NOT_EXPOSE"
        )

        client = APIClient()
        client.force_authenticate(user=env['student'])

        # 1. Course final assessment API
        res = client.get(f"/api/assessments/course/{env['course_a'].id}/final-assessment/")
        coding_payload = res.data['coding_question']
        assert 'hidden_test_cases' not in coding_payload
        assert 'reference_solution' not in coding_payload
        assert len(coding_payload['sample_test_cases']) == 2
        for s in coding_payload['sample_test_cases']:
            assert 'input' in s
            assert 'expected_output' in s
        raw_text = str(res.data)
        assert 'SECRET' not in raw_text

        # 2. Start attempt API
        start_res = client.post(f"/api/assessments/{res.data['id']}/start/", format='json')
        raw_start = str(start_res.data)
        assert 'SECRET' not in raw_start
        assert 'hidden_test_cases' not in start_res.data.get('coding_question', {})

        # 3. Attempt details API
        attempt_id = start_res.data['id']
        detail_res = client.get(f"/api/assessments/attempts/{attempt_id}/")
        raw_detail = str(detail_res.data)
        assert 'SECRET' not in raw_detail

    def test_requirement_j_existing_normal_assessments_continue_working(self, setup_data):
        """Test J: Existing normal assessments continue working."""
        env = setup_data
        # Add normal MCQ questions to the non-programming course assessment
        assessment = Assessment.objects.create(
            course=env['course_non_prog'],
            title="Business Ops Certification",
            assessment_type="FINAL_ASSESSMENT",
            duration_minutes=30,
            pass_percentage=50.0,
            is_published=True
        )
        q_mcq = Question.objects.create(
            assessment=assessment,
            course=env['course_non_prog'],
            text="What is a KPI?",
            question_type="MCQ_SINGLE",
            difficulty="EASY",
            marks=1,
            status="ACTIVE",
            is_bank_question=True
        )
        opt1 = QuestionOption.objects.create(question=q_mcq, text="Key Performance Indicator", is_correct=True, order=1)
        opt2 = QuestionOption.objects.create(question=q_mcq, text="Known Process Index", is_correct=False, order=2)

        client = APIClient()
        client.force_authenticate(user=env['student'])

        start_res = client.post(f"/api/assessments/{assessment.id}/start/", format='json')
        assert start_res.status_code == 201
        attempt_id = start_res.data['id']

        # Save answers
        save_res = client.post(
            f"/api/assessments/attempts/{attempt_id}/answers/",
            data={'question_id': q_mcq.id, 'selected_option_id': opt1.id},
            format='json'
        )
        assert save_res.status_code == 200

        # Submit attempt
        sub_res = client.post(f"/api/assessments/attempts/{attempt_id}/submit/", format='json')
        assert sub_res.status_code == 200
        assert sub_res.data['passed'] is True


