from django.urls import path
from .views import (
    CoursePreAssessmentView,
    CourseFinalAssessmentView,
    AssessmentEligibilityCheckView,
    StartAttemptView,
    AttemptDetailView,
    AutosaveAnswerView,
    LogProctoringEventView,
    SubmitAssessmentView,
    AssessmentAttemptResultView,
    RunCodeView,
    SubmitCodeView,
    CourseCodingQuestionListView,
    CodingQuestionDetailView,
    CodingQuestionValidateView,
    AICodingQuestionGenerateView,
    CodingQuestionPublishView
)

urlpatterns = [
    path('course/<int:course_id>/pre-assessment/', CoursePreAssessmentView.as_view(), name='course_pre_assessment'),
    path('course/<int:course_id>/final-assessment/', CourseFinalAssessmentView.as_view(), name='course_final_assessment'),
    path('<int:assessment_id>/eligibility/', AssessmentEligibilityCheckView.as_view(), name='assessment_eligibility'),
    path('<int:assessment_id>/start/', StartAttemptView.as_view(), name='start_assessment'),
    path('attempts/<uuid:attempt_id>/', AttemptDetailView.as_view(), name='attempt_detail'),
    path('attempts/<uuid:attempt_id>/answers/', AutosaveAnswerView.as_view(), name='autosave_answer'),
    path('attempts/<uuid:attempt_id>/events/', LogProctoringEventView.as_view(), name='log_proctoring_event'),
    path('attempts/<uuid:attempt_id>/submit/', SubmitAssessmentView.as_view(), name='submit_assessment'),
    path('attempts/<uuid:attempt_id>/result/', AssessmentAttemptResultView.as_view(), name='assessment_result'),
    
    # Coding Question Examination Endpoints
    path('attempts/<uuid:attempt_id>/run-code/', RunCodeView.as_view(), name='attempt_run_code'),
    path('attempts/<uuid:attempt_id>/submit-code/', SubmitCodeView.as_view(), name='attempt_submit_code'),
    
    # Faculty & AI Coding Question Builder Endpoints
    path('courses/<int:course_id>/coding-questions/', CourseCodingQuestionListView.as_view(), name='course_coding_questions'),
    path('coding-questions/<int:question_id>/', CodingQuestionDetailView.as_view(), name='coding_question_detail'),
    path('coding-questions/<int:question_id>/validate/', CodingQuestionValidateView.as_view(), name='coding_question_validate'),
    path('coding-questions/<int:question_id>/publish/', CodingQuestionPublishView.as_view(), name='coding_question_publish'),
    path('coding-questions/ai-generate/', AICodingQuestionGenerateView.as_view(), name='ai_coding_question_generate'),
]
