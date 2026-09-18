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
    Module,
    VideoResource,
    StudyMaterial
)
from assessments.models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from assessments.wrong_answer_service import WrongAnswerReviewService
from assessments.question_bank_service import QuestionBankService
from assessments.serializers import AssessmentResultSerializer

User = get_user_model()

@pytest.mark.django_db
class TestWrongAnswerReviewAndDistribution:
    @pytest.fixture
    def setup_assessment_environment(self):
        user = User.objects.create_user(
            username="test_student",
            email="test_student@example.com",
            password="Password123!",
            role="STUDENT"
        )
        dept = Department.objects.create(code='CSE', name='Computer Science and Engineering')
        cat = SkillCategory.objects.create(name='Core Engineering')
        domain = SkillDomain.objects.create(category=cat, name='Programming')
        skill = Skill.objects.create(name='DSA', slug='dsa-core', category=cat, domain=domain, department=dept)
        
        course = Course.objects.create(
            title="Data Structures & Algorithms",
            slug="data-structures-algorithms",
            skill=skill,
            description="Deep dive into core DSA",
            status="PUBLISHED"
        )
        mod1 = Module.objects.create(
            course=course,
            title="Arrays and Memory Allocation",
            topic_tag="arrays_memory",
            order=1
        )
        mod2 = Module.objects.create(
            course=course,
            title="Linked Lists & Pointers",
            topic_tag="linked_lists",
            order=2
        )
        # Add real verified resources
        res1 = VideoResource.objects.create(
            module=mod1,
            title="Array Memory & Cache Locality",
            video_type="YOUTUBE",
            youtube_video_id="pmN9ExVY3gQ",
            youtube_url="https://www.youtube.com/watch?v=pmN9ExVY3gQ",
            channel_name="Corey Schafer",
            duration_seconds=840,
            status="PUBLISHED"
        )
        res2 = StudyMaterial.objects.create(
            module=mod1,
            title="Arrays Deep Dive Notes",
            resource_type="AI_STUDY_NOTES",
            text_content="Detailed notes on contiguous arrays.",
            status="PUBLISHED"
        )

        assessment = Assessment.objects.create(
            course=course,
            title="DSA Benchmark Assessment",
            pass_percentage=60.0
        )

        # Create question 1
        q1 = Question.objects.create(
            assessment=assessment,
            course=course,
            text="What is the time complexity of accessing an element in an array by index?",
            topic_tag="arrays_memory",
            question_type="MCQ_SINGLE",
            difficulty="EASY",
            marks=1,
            explanation="Array elements occupy contiguous memory blocks, allowing constant time O(1) arithmetic lookup."
        )
        q1_opt_a = QuestionOption.objects.create(question=q1, text="O(1)", is_correct=True, order=1)
        q1_opt_b = QuestionOption.objects.create(question=q1, text="O(n)", is_correct=False, order=2)

        # Create question 2
        q2 = Question.objects.create(
            assessment=assessment,
            course=course,
            text="Why are arrays cache-friendly compared to linked lists?",
            topic_tag="arrays_memory",
            question_type="MCQ_SINGLE",
            difficulty="MEDIUM",
            marks=1,
            explanation="Contiguous memory layout allows CPU prefetchers to load sequential memory lines efficiently."
        )
        q2_opt_a = QuestionOption.objects.create(question=q2, text="Arrays use pointer dereferencing", is_correct=False, order=1)
        q2_opt_b = QuestionOption.objects.create(question=q2, text="Arrays exhibit contiguous spatial locality in CPU cache lines", is_correct=True, order=2)

        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            student=user,
            score=1.0,
            percentage=50.0,
            status="EVALUATED",
            server_deadline=timezone.now() + timedelta(minutes=60),
            passed=False
        )

        # Candidate answered q1 correctly
        ans1 = StudentAnswer.objects.create(
            attempt=attempt,
            question=q1,
            is_correct=True,
            marks_obtained=1.0
        )
        ans1.selected_options.add(q1_opt_a)

        # Candidate answered q2 incorrectly (chose opt_a instead of opt_b)
        ans2 = StudentAnswer.objects.create(
            attempt=attempt,
            question=q2,
            is_correct=False,
            marks_obtained=0.0
        )
        ans2.selected_options.add(q2_opt_a)

        return {
            "user": user,
            "course": course,
            "mod1": mod1,
            "assessment": assessment,
            "q1": q1,
            "q2": q2,
            "attempt": attempt,
            "res1": res1,
            "res2": res2,
        }

    def test_wrong_answer_service_generates_detailed_reviews(self, setup_assessment_environment):
        data = setup_assessment_environment
        attempt = data["attempt"]

        review = WrongAnswerReviewService.generate_attempt_review(attempt)

        assert review is not None
        assert "detailed_questions" in review
        assert "weak_area_recommendations" in review
        assert "ai_diagnostic_summary" in review

        assert review["total_questions"] == 2
        assert review["correct_count"] == 1
        assert review["wrong_count"] == 1
        assert review["percentage"] == 50.0

        questions = review["detailed_questions"]
        assert len(questions) == 2

        # Check question 1 (correct)
        q1_rev = next(q for q in questions if q["question_id"] == data["q1"].id)
        assert q1_rev["is_correct"] is True

        # Check question 2 (wrong)
        q2_rev = next(q for q in questions if q["question_id"] == data["q2"].id)
        assert q2_rev["is_correct"] is False
        assert "Arrays use pointer dereferencing" in q2_rev["student_answers"]
        assert "Arrays exhibit contiguous spatial locality in CPU cache lines" in q2_rev["correct_answers"]
        
        # Verify AI Diagnostic components
        ai_diag = q2_rev["ai_diagnosis"]
        assert ai_diag is not None
        assert "why_incorrect" in ai_diag
        assert "why_correct" in ai_diag
        assert "simple_explanation" in ai_diag
        assert "small_example" in ai_diag
        assert "recommended_topic" in ai_diag
        assert len(ai_diag["why_incorrect"]) > 10
        assert len(ai_diag["why_correct"]) > 10

        # Verify weak area analysis
        assert review["primary_weak_area"] is not None
        assert len(review["weak_area_recommendations"]) >= 1

        rec = review["weak_area_recommendations"][0]
        assert rec["error_count"] == 1
        assert rec["video_reference"] is not None
        assert rec["video_reference"]["youtube_video_id"] == "pmN9ExVY3gQ"
        assert "https://www.youtube.com/watch?v=pmN9ExVY3gQ" in rec["video_reference"]["youtube_url"]
        assert rec["study_material"] is not None

    def test_serializer_includes_review_data(self, setup_assessment_environment):
        data = setup_assessment_environment
        attempt = data["attempt"]

        serializer = AssessmentResultSerializer(attempt)
        res_data = serializer.data

        assert "review_data" in res_data
        review_data = res_data["review_data"]
        assert review_data["wrong_count"] == 1
        assert len(review_data["detailed_questions"]) == 2

    def test_difficulty_distribution_in_question_bank(self, setup_assessment_environment):
        data = setup_assessment_environment
        assessment = data["assessment"]
        course = data["course"]

        assessment.blueprint = {
            'question_count': 10,
            'difficulty_distribution': {'EASY': 0.4, 'MEDIUM': 0.5, 'HARD': 0.1}
        }
        assessment.save()

        # Create a batch of questions of varying difficulties
        for i in range(15):
            diff = "EASY" if i < 6 else ("MEDIUM" if i < 13 else "HARD")
            q = Question.objects.create(
                assessment=assessment,
                course=course,
                text=f"Sample Bank Question {i}",
                topic_tag="arrays_memory",
                question_type="MCQ_SINGLE",
                difficulty=diff,
                is_bank_question=True
            )
            QuestionOption.objects.create(question=q, text="Opt A", is_correct=True, order=1)
            QuestionOption.objects.create(question=q, text="Opt B", is_correct=False, order=2)

        q_ids, opt_orders = QuestionBankService.prepare_attempt_questions(
            assessment=assessment,
            randomize_options=True
        )

        assert len(q_ids) == 10
        assert len(opt_orders) == 10
