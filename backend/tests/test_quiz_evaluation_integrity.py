import random
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
from assessments.models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from assessments.wrong_answer_service import WrongAnswerReviewService
from assessments.serializers import AssessmentResultSerializer

User = get_user_model()

@pytest.fixture
def env():
    user = User.objects.create_user(
        username="quiz_student",
        email="quiz_student@example.com",
        password="Password123!",
        role="STUDENT"
    )
    dept = Department.objects.create(code='CSE', name='Computer Science')
    cat = SkillCategory.objects.create(name='Computer Science')
    domain = SkillDomain.objects.create(category=cat, name='Core')
    skill = Skill.objects.create(name='Python Programming', slug='python-programming', category=cat, domain=domain, department=dept)
    course = Course.objects.create(title="Python Mastery", slug="python-mastery", skill=skill, status="PUBLISHED")
    module = Module.objects.create(course=course, title="Python Functions", topic_tag="functions", order=1)
    
    assessment = Assessment.objects.create(
        course=course,
        title="Python Fundamentals Final Exam",
        assessment_type="FINAL_ASSESSMENT",
        duration_minutes=30,
        pass_percentage=70.0
    )
    return {
        'user': user,
        'course': course,
        'module': module,
        'assessment': assessment
    }

@pytest.mark.django_db
class TestQuizEvaluationIntegrity:
    """
    Automated verification of Section 15:
    TEST 1 to TEST 10 testing the authoritative quiz answer evaluation pipeline.
    """

    def test_1_select_correct_option(self, env):
        """TEST 1: Select the correct option -> Expected: is_correct = True"""
        q = Question.objects.create(
            assessment=env['assessment'],
            text="Which keyword is used to define a function in Python?",
            question_type="SINGLE_CHOICE",
            marks=1,
            order=1
        )
        opt_wrong1 = QuestionOption.objects.create(question=q, text="function", is_correct=False, order=1)
        opt_wrong2 = QuestionOption.objects.create(question=q, text="define", is_correct=False, order=2)
        opt_correct = QuestionOption.objects.create(question=q, text="def", is_correct=True, order=3)
        opt_wrong3 = QuestionOption.objects.create(question=q, text="method", is_correct=False, order=4)

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )
        ans = StudentAnswer.objects.create(attempt=attempt, question=q)
        ans.selected_options.add(opt_correct)

        attempt.evaluate()
        review = WrongAnswerReviewService.generate_attempt_review(attempt)
        q_review = review['detailed_questions'][0]

        assert q_review['is_correct'] is True
        assert q_review['selected_option_id'] == opt_correct.id
        assert q_review['correct_option_id'] == opt_correct.id
        assert attempt.score == 1.0

    def test_2_select_wrong_option(self, env):
        """TEST 2: Select a wrong option -> Expected: is_correct = False"""
        q = Question.objects.create(
            assessment=env['assessment'],
            text="Which keyword is used to define a function in Python?",
            question_type="SINGLE_CHOICE",
            marks=1,
            order=1
        )
        opt_wrong = QuestionOption.objects.create(question=q, text="function", is_correct=False, order=1)
        opt_correct = QuestionOption.objects.create(question=q, text="def", is_correct=True, order=2)

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )
        ans = StudentAnswer.objects.create(attempt=attempt, question=q)
        ans.selected_options.add(opt_wrong)

        attempt.evaluate()
        review = WrongAnswerReviewService.generate_attempt_review(attempt)
        q_review = review['detailed_questions'][0]

        assert q_review['is_correct'] is False
        assert q_review['selected_option_id'] == opt_wrong.id
        assert q_review['correct_option_id'] == opt_correct.id
        assert attempt.score == 0.0

    def test_3_shuffle_option_order(self, env):
        """TEST 3: Shuffle option order -> Correct option must remain correct."""
        q = Question.objects.create(
            assessment=env['assessment'],
            text="Which keyword is used to define a function in Python?",
            question_type="SINGLE_CHOICE",
            marks=1,
            order=1
        )
        opt1 = QuestionOption.objects.create(question=q, text="function", is_correct=False, order=1)
        opt2 = QuestionOption.objects.create(question=q, text="define", is_correct=False, order=2)
        opt3_correct = QuestionOption.objects.create(question=q, text="def", is_correct=True, order=3)
        opt4 = QuestionOption.objects.create(question=q, text="method", is_correct=False, order=4)

        all_opts = [opt1, opt2, opt3_correct, opt4]

        # Simulate 5 distinct shuffles (changing visual order in attempt.question_option_orders)
        for _ in range(5):
            shuffled = list(all_opts)
            random.shuffle(shuffled)
            shuffled_ids = [o.id for o in shuffled]

            attempt = AssessmentAttempt.objects.create(
                assessment=env['assessment'],
                student=env['user'],
                server_deadline=timezone.now() + timedelta(minutes=30),
                status="IN_PROGRESS",
                question_option_orders={str(q.id): shuffled_ids}
            )

            # Student selects the correct option ID (opt3_correct.id) regardless of display order
            ans = StudentAnswer.objects.create(attempt=attempt, question=q)
            ans.selected_options.add(opt3_correct)

            attempt.evaluate()
            review = WrongAnswerReviewService.generate_attempt_review(attempt)
            q_review = review['detailed_questions'][0]

            assert q_review['is_correct'] is True
            assert q_review['selected_option_id'] == opt3_correct.id
            assert q_review['correct_option_id'] == opt3_correct.id

    def test_4_refresh_question_display(self, env):
        """TEST 4: Refresh question display -> Correct answer must remain correct across repeated loads."""
        q = Question.objects.create(
            assessment=env['assessment'],
            text="Which keyword is used to define a function in Python?",
            question_type="SINGLE_CHOICE",
            marks=1,
            order=1
        )
        opt_wrong = QuestionOption.objects.create(question=q, text="function", is_correct=False, order=1)
        opt_correct = QuestionOption.objects.create(question=q, text="def", is_correct=True, order=2)

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )
        ans = StudentAnswer.objects.create(attempt=attempt, question=q)
        ans.selected_options.add(opt_correct)

        # Repeated evaluations simulating refreshes
        for _ in range(3):
            attempt.evaluate()
            review = WrongAnswerReviewService.generate_attempt_review(attempt)
            assert review['detailed_questions'][0]['is_correct'] is True
            assert attempt.score == 1.0

    def test_5_submit_answer_through_api_manually(self, env):
        """TEST 5: Submit answer through API manually -> Backend must calculate correctly."""
        q = Question.objects.create(
            assessment=env['assessment'],
            text="Which keyword is used to define a function in Python?",
            question_type="SINGLE_CHOICE",
            marks=1,
            order=1
        )
        opt_wrong = QuestionOption.objects.create(question=q, text="define", is_correct=False, order=1)
        opt_correct = QuestionOption.objects.create(question=q, text="def", is_correct=True, order=2)

        client = APIClient()
        client.force_authenticate(user=env['user'])

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )

        # 1. Autosave answer using selected_option_id
        save_res = client.post(f"/api/assessments/attempts/{attempt.id}/answers/", {
            "question_id": q.id,
            "selected_option_id": opt_correct.id
        }, format="json")
        assert save_res.status_code == 200
        assert save_res.data['status'] == 'saved'

        # 2. Submit assessment
        sub_res = client.post(f"/api/assessments/attempts/{attempt.id}/submit/", format="json")
        assert sub_res.status_code == 200
        assert sub_res.data['score'] == 1.0
        assert sub_res.data['percentage'] == 100.0

    def test_6_send_selected_option_from_another_question(self, env):
        """TEST 6: Send a selected_option_id from another question -> Backend must reject it with HTTP 400."""
        q1 = Question.objects.create(
            assessment=env['assessment'],
            text="Question 1?",
            question_type="SINGLE_CHOICE",
            marks=1,
            order=1
        )
        opt1_q1 = QuestionOption.objects.create(question=q1, text="Q1 Option", is_correct=True, order=1)

        q2 = Question.objects.create(
            assessment=env['assessment'],
            text="Question 2?",
            question_type="SINGLE_CHOICE",
            marks=1,
            order=2
        )
        opt1_q2 = QuestionOption.objects.create(question=q2, text="Q2 Option", is_correct=True, order=1)

        client = APIClient()
        client.force_authenticate(user=env['user'])

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )

        # Send question_id = q1.id, but selected_option_id belonging to q2
        res = client.post(f"/api/assessments/attempts/{attempt.id}/answers/", {
            "question_id": q1.id,
            "selected_option_id": opt1_q2.id
        }, format="json")

        assert res.status_code == 400
        assert "do not belong to question" in res.data['error']

    def test_7_20_question_quiz_with_known_answer_key(self, env):
        """TEST 7: 20-question quiz with known answer key -> Verify final score and percentage exactly."""
        questions = []
        correct_options = {}

        for i in range(1, 21):
            q = Question.objects.create(
                assessment=env['assessment'],
                text=f"Sample Question #{i}?",
                question_type="SINGLE_CHOICE",
                marks=1,
                order=i
            )
            opt_w1 = QuestionOption.objects.create(question=q, text="Wrong A", is_correct=False, order=1)
            opt_c = QuestionOption.objects.create(question=q, text="Correct B", is_correct=True, order=2)
            opt_w2 = QuestionOption.objects.create(question=q, text="Wrong C", is_correct=False, order=3)
            questions.append(q)
            correct_options[q.id] = (opt_c.id, opt_w1.id)

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )

        # Answer 16 correct, 4 wrong
        for idx, q in enumerate(questions):
            c_id, w_id = correct_options[q.id]
            selected_id = c_id if idx < 16 else w_id
            ans = StudentAnswer.objects.create(attempt=attempt, question=q)
            ans.selected_options.add(QuestionOption.objects.get(id=selected_id))

        attempt.evaluate()

        assert attempt.score == 16.0
        assert attempt.percentage == 80.0
        assert attempt.passed is True  # Pass threshold is 70%

    def test_8_wrong_answer_review(self, env):
        """TEST 8: Wrong-answer review -> Only wrong questions appear in wrong-answer section."""
        q1 = Question.objects.create(assessment=env['assessment'], text="Q1?", question_type="SINGLE_CHOICE", marks=1, order=1)
        opt_c1 = QuestionOption.objects.create(question=q1, text="C1", is_correct=True, order=1)
        opt_w1 = QuestionOption.objects.create(question=q1, text="W1", is_correct=False, order=2)

        q2 = Question.objects.create(assessment=env['assessment'], text="Q2?", question_type="SINGLE_CHOICE", marks=1, order=2)
        opt_c2 = QuestionOption.objects.create(question=q2, text="C2", is_correct=True, order=1)
        opt_w2 = QuestionOption.objects.create(question=q2, text="W2", is_correct=False, order=2)

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )

        # Q1 answered correctly, Q2 answered wrongly
        ans1 = StudentAnswer.objects.create(attempt=attempt, question=q1)
        ans1.selected_options.add(opt_c1)
        ans2 = StudentAnswer.objects.create(attempt=attempt, question=q2)
        ans2.selected_options.add(opt_w2)

        attempt.evaluate()
        review = WrongAnswerReviewService.generate_attempt_review(attempt)

        assert review['correct_count'] == 1
        assert review['wrong_count'] == 1

        wrong_questions = [q for q in review['detailed_questions'] if not q['is_correct']]
        assert len(wrong_questions) == 1
        assert wrong_questions[0]['question_id'] == q2.id
        assert wrong_questions[0]['selected_option_id'] == opt_w2.id
        assert wrong_questions[0]['correct_option_id'] == opt_c2.id

    def test_9_correct_answer_review(self, env):
        """TEST 9: Correct-answer review -> Correct questions are marked correct."""
        q = Question.objects.create(assessment=env['assessment'], text="Q1?", question_type="SINGLE_CHOICE", marks=1, order=1)
        opt_c = QuestionOption.objects.create(question=q, text="C1", is_correct=True, order=1)

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )
        ans = StudentAnswer.objects.create(attempt=attempt, question=q)
        ans.selected_options.add(opt_c)

        attempt.evaluate()
        review = WrongAnswerReviewService.generate_attempt_review(attempt)
        correct_questions = [item for item in review['detailed_questions'] if item['is_correct']]

        assert len(correct_questions) == 1
        assert correct_questions[0]['is_correct'] is True
        assert correct_questions[0]['question_id'] == q.id

    def test_10_assessment_result_api(self, env):
        """TEST 10: Assessment result API -> Percentage matches number of correct answers and Result API returns stable IDs."""
        q1 = Question.objects.create(assessment=env['assessment'], text="Q1?", question_type="SINGLE_CHOICE", marks=1, order=1)
        opt_c1 = QuestionOption.objects.create(question=q1, text="C1", is_correct=True, order=1)
        opt_w1 = QuestionOption.objects.create(question=q1, text="W1", is_correct=False, order=2)

        q2 = Question.objects.create(assessment=env['assessment'], text="Q2?", question_type="SINGLE_CHOICE", marks=1, order=2)
        opt_c2 = QuestionOption.objects.create(question=q2, text="C2", is_correct=True, order=1)
        opt_w2 = QuestionOption.objects.create(question=q2, text="W2", is_correct=False, order=2)

        client = APIClient()
        client.force_authenticate(user=env['user'])

        attempt = AssessmentAttempt.objects.create(
            assessment=env['assessment'],
            student=env['user'],
            server_deadline=timezone.now() + timedelta(minutes=30),
            status="IN_PROGRESS"
        )
        ans1 = StudentAnswer.objects.create(attempt=attempt, question=q1)
        ans1.selected_options.add(opt_c1)
        ans2 = StudentAnswer.objects.create(attempt=attempt, question=q2)
        ans2.selected_options.add(opt_w2)

        attempt.evaluate()

        res = client.get(f"/api/assessments/attempts/{attempt.id}/result/")
        assert res.status_code == 200
        review_data = res.data['review_data']

        assert res.data['score'] == 1.0
        assert res.data['percentage'] == 50.0

        results = review_data.get('results', [])
        assert len(results) == 2

        # Check Result API items
        r1 = next(r for r in results if r['question_id'] == q1.id)
        assert r1['selected_option_id'] == opt_c1.id
        assert r1['correct_option_id'] == opt_c1.id
        assert r1['is_correct'] is True

        r2 = next(r for r in results if r['question_id'] == q2.id)
        assert r2['selected_option_id'] == opt_w2.id
        assert r2['correct_option_id'] == opt_c2.id
        assert r2['is_correct'] is False

    def test_11_practice_quiz_evaluation_with_correct_and_wrong_answers(self, env):
        """TEST 11: Practice task quiz -> Correct answers receive 100%, wrong answers receive 0%."""
        from catalogue.models import PracticeTask
        pt = PracticeTask.objects.create(
            module=env['module'],
            title="Module Practice Quiz",
            task_type="QUIZ",
            pass_score=70,
            content={
                "questions": [
                    {
                        "id": "q1",
                        "question": "Which keyword defines a function?",
                        "options": ["func", "def", "lambda"],
                        "correct_answer": "def"
                    },
                    {
                        "id": "q2",
                        "question": "Which is immutable?",
                        "options": ["list", "tuple", "set"],
                        "correct_option": "tuple"
                    }
                ]
            }
        )

        client = APIClient()
        client.force_authenticate(user=env['user'])

        # Case A: Correct answers submitted
        res_correct = client.post("/api/learning/practice/submit/", {
            "practice_id": pt.id,
            "answers": {
                "q1": "def",
                "q2": "tuple"
            }
        }, format="json")

        assert res_correct.status_code == 200
        assert res_correct.data['score'] == 100.0
        assert res_correct.data['is_completed'] is True

        # Case B: Wrong answers submitted
        res_wrong = client.post("/api/learning/practice/submit/", {
            "practice_id": pt.id,
            "answers": {
                "q1": "func",
                "q2": "list"
            }
        }, format="json")

        assert res_wrong.status_code == 200
        assert res_wrong.data['score'] == 0.0

    def test_faculty_mcq_practice_evaluation_letter_and_text_integrity(self, env):
        """
        Tests practice quiz added by faculty where correct_option is a letter ('B')
        and options are text strings (['scanf()', 'printf()', 'input()', 'display()']).
        Verifies student submitting 'printf()' or 'B' correctly scores 100%, and wrong option scores 0%.
        Also verifies handling when questions do not have an explicit 'id' key.
        """
        from catalogue.models import PracticeTask
        pt = PracticeTask.objects.create(
            module=env['module'],
            title="Concept Check Practice",
            task_type="MCQ_PRACTICE",
            pass_score=70.0,
            content={
                "questions": [
                    {
                        "question": "Which function is used to display output in C?",
                        "options": ["scanf()", "printf()", "input()", "display()"],
                        "correct_option": "B",
                        "explanation": "printf is the standard output function in C."
                    }
                ]
            }
        )

        client = APIClient()
        client.force_authenticate(user=env['user'])

        # Case 1: Student submits option text "printf()" (Option B)
        res_text = client.post("/api/learning/practice/submit/", {
            "practice_id": pt.id,
            "answers": {
                "0": "printf()"
            }
        }, format="json")
        assert res_text.status_code == 200
        assert res_text.data['score'] == 100.0
        assert res_text.data['is_completed'] is True

        # Case 2: Student submits option letter "B"
        res_letter = client.post("/api/learning/practice/submit/", {
            "practice_id": pt.id,
            "answers": {
                "0": "B"
            }
        }, format="json")
        assert res_letter.status_code == 200
        assert res_letter.data['score'] == 100.0
        assert res_letter.data['is_completed'] is True

        # Case 3: Student submits wrong option "scanf()" (Option A)
        res_wrong = client.post("/api/learning/practice/submit/", {
            "practice_id": pt.id,
            "answers": {
                "0": "scanf()"
            }
        }, format="json")
        assert res_wrong.status_code == 200
        assert res_wrong.data['score'] == 0.0


