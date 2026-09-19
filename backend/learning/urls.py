from django.urls import path
from .views import (
    EnrollmentListCreateView, 
    CourseProgressDetailView, 
    CompleteModuleView,
    VideoProgressView,
    VideoStartView,
    VideoManualConfirmView,
    ReportUnavailableVideoView,
    MaterialCompleteView,
    PracticeSubmitView,
    CourseAssessmentEligibilityView,
    LearningAnalyticsView,
    GenericResourceCompleteView
)

urlpatterns = [
    path('enroll/', EnrollmentListCreateView.as_view(), name='enroll'),
    path('enrollments/', EnrollmentListCreateView.as_view(), name='enrollments'),
    path('course-progress/<slug:course_slug>/', CourseProgressDetailView.as_view(), name='course_progress'),
    path('progress/complete/', CompleteModuleView.as_view(), name='complete_module'),
    path('modules/<int:module_id>/complete/', CompleteModuleView.as_view(), name='complete_module_by_id'),
    path('modules/<int:module_id>/progress/', CompleteModuleView.as_view(), name='module_progress_by_id'),
    path('resources/<int:resource_id>/complete/', GenericResourceCompleteView.as_view(), name='resource_complete'),
    path('video/progress/', VideoProgressView.as_view(), name='video_progress'),
    path('video/start/', VideoStartView.as_view(), name='video_start_body'),
    path('video/<int:video_id>/start/', VideoStartView.as_view(), name='video_start'),
    path('video/confirm-complete/', VideoManualConfirmView.as_view(), name='video_confirm_complete_body'),
    path('video/<int:video_id>/confirm-complete/', VideoManualConfirmView.as_view(), name='video_confirm_complete'),
    path('video/report-unavailable/', ReportUnavailableVideoView.as_view(), name='report_unavailable_video_body'),
    path('video/<int:video_id>/report-unavailable/', ReportUnavailableVideoView.as_view(), name='report_unavailable_video'),
    path('material/complete/', MaterialCompleteView.as_view(), name='material_complete'),
    path('practice/submit/', PracticeSubmitView.as_view(), name='practice_submit'),
    path('courses/<int:course_id>/assessment-eligibility/', CourseAssessmentEligibilityView.as_view(), name='course_assessment_eligibility_learning'),
    path('analytics/', LearningAnalyticsView.as_view(), name='learning_analytics'),
]
