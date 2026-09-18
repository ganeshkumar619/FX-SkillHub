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
    AssessmentAttemptResultView
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
]
