from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from authentication.views import HealthCheckView
from learning.views import CourseAssessmentEligibilityView, LearningAnalyticsView
from .views import root_view, api_root_view

from catalogue.faculty_builder_views import (
    FacultyCourseCreateOrUpdateView,
    FacultyModuleCreateView,
    FacultyModuleDetailView,
    FacultyLessonCreateView,
    FacultyLessonDetailView,
    FacultyLessonAINotesView,
    FacultyLessonManualNotesView,
    FacultyLessonYouTubeView,
    FacultyLessonPracticeView,
    FacultyResourceDetailView,
    FacultyCourseValidateView,
    FacultyCourseSubmitReviewView,
    FacultyCoursePreviewView,
    AIYouTubeSuggestionsView,
    AIStudyMaterialPreviewView,
    AdminCourseReviewsListView,
    AdminCourseReviewActionView,
    StudentCourseDetailByIdView,
    StudentCourseProgressByIdView
)

urlpatterns = [
    path('', root_view, name='root'),
    path('api/', api_root_view, name='api_root'),
    path('api/health/', HealthCheckView.as_view(), name='api_health'),
    path('api/courses/<int:course_id>/assessment-eligibility/', CourseAssessmentEligibilityView.as_view(), name='root_assessment_eligibility'),
    path('api/analytics/learning/', LearningAnalyticsView.as_view(), name='root_learning_analytics'),
    
    # Section 30 Faculty API Routes
    path('api/faculty/courses/', FacultyCourseCreateOrUpdateView.as_view(), name='root_faculty_courses'),
    path('api/faculty/courses/<int:pk>/', FacultyCourseCreateOrUpdateView.as_view(), name='root_faculty_course_detail'),
    path('api/faculty/courses/<int:course_id>/modules/', FacultyModuleCreateView.as_view(), name='root_faculty_create_module'),
    path('api/faculty/modules/<int:pk>/', FacultyModuleDetailView.as_view(), name='root_faculty_module_detail'),
    path('api/faculty/modules/<int:module_id>/lessons/', FacultyLessonCreateView.as_view(), name='root_faculty_create_lesson'),
    path('api/faculty/lessons/<int:pk>/', FacultyLessonDetailView.as_view(), name='root_faculty_lesson_detail'),
    path('api/faculty/lessons/<int:pk>/ai-notes/', FacultyLessonAINotesView.as_view(), name='root_faculty_lesson_ai_notes'),
    path('api/faculty/lessons/<int:pk>/notes/', FacultyLessonManualNotesView.as_view(), name='root_faculty_lesson_notes'),
    path('api/faculty/lessons/<int:pk>/youtube/', FacultyLessonYouTubeView.as_view(), name='root_faculty_lesson_youtube'),
    path('api/faculty/lessons/<int:pk>/practice/', FacultyLessonPracticeView.as_view(), name='root_faculty_lesson_practice'),
    path('api/faculty/resources/<int:pk>/', FacultyResourceDetailView.as_view(), name='root_faculty_resource_detail'),
    path('api/faculty/courses/<int:pk>/validate/', FacultyCourseValidateView.as_view(), name='root_faculty_course_validate'),
    path('api/faculty/courses/<int:pk>/submit-review/', FacultyCourseSubmitReviewView.as_view(), name='root_faculty_course_submit_review'),
    path('api/faculty/courses/<int:pk>/preview/', FacultyCoursePreviewView.as_view(), name='root_faculty_course_preview'),

    # Section 30 AI API Routes
    path('api/ai/youtube-suggestions/', AIYouTubeSuggestionsView.as_view(), name='root_ai_youtube_suggestions'),
    path('api/ai/study-material/', AIStudyMaterialPreviewView.as_view(), name='root_ai_study_material'),

    # Section 30 Admin Review API Routes
    path('api/admin/course-reviews/', AdminCourseReviewsListView.as_view(), name='root_admin_course_reviews'),
    path('api/admin/course-reviews/<int:pk>/approve/', AdminCourseReviewActionView.as_view(), {'action': 'APPROVE'}, name='root_admin_course_review_approve'),
    path('api/admin/course-reviews/<int:pk>/reject/', AdminCourseReviewActionView.as_view(), {'action': 'REJECT'}, name='root_admin_course_review_reject'),

    # Section 30 Student Course Detail & Progress API Routes
    path('api/courses/<int:pk>/', StudentCourseDetailByIdView.as_view(), name='root_student_course_by_id'),
    path('api/courses/<int:pk>/progress/', StudentCourseProgressByIdView.as_view(), name='root_student_course_progress'),

    path('admin/', admin.site.urls),
    path('api/', include('authentication.urls')),
    path('api/catalogue/', include('catalogue.urls')),
    path('api/learning/', include('learning.urls')),
    path('api/assessments/', include('assessments.urls')),
    path('api/certificates/', include('certificates.urls')),
    path('api/proctoring/', include('proctoring.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/audit/', include('audit.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
