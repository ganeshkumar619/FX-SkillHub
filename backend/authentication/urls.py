from django.urls import path
from .views import (
    HealthCheckView, 
    RegisterView, 
    VerifyOTPView,
    ResendOTPView,
    LoginView, 
    LogoutView, 
    UserProfileView,
    GoogleAuthInitView,
    GoogleAuthCallbackView,
    AdminFacultyListView,
    AdminFacultyDetailView,
    AdminFacultyStatusToggleView,
    AdminFacultyResendInvitationView,
    FacultyVerifyInvitationView,
    FacultyActivateAccountView,
    AdminStudentListView,
    AdminStudentDetailView,
    AdminSystemOverviewView
)

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', UserProfileView.as_view(), name='user_profile'),
    path('auth/google/url/', GoogleAuthInitView.as_view(), name='google_auth_url'),
    path('auth/google/callback/', GoogleAuthCallbackView.as_view(), name='google_auth_callback'),

    # Faculty Invitation & Activation
    path('auth/faculty/verify-invitation/', FacultyVerifyInvitationView.as_view(), name='faculty_verify_invitation'),
    path('auth/faculty/activate/', FacultyActivateAccountView.as_view(), name='faculty_activate_account'),

    # Admin Faculty & User Management
    path('admin/faculty/', AdminFacultyListView.as_view(), name='admin_faculty_list'),
    path('admin/faculty/<int:pk>/', AdminFacultyDetailView.as_view(), name='admin_faculty_detail'),
    path('admin/faculty/<int:pk>/toggle-status/', AdminFacultyStatusToggleView.as_view(), name='admin_faculty_toggle_status'),
    path('admin/faculty/<int:pk>/resend-invitation/', AdminFacultyResendInvitationView.as_view(), name='admin_faculty_resend_invitation'),
    path('admin/students/', AdminStudentListView.as_view(), name='admin_student_list'),
    path('admin/students/<int:pk>/', AdminStudentDetailView.as_view(), name='admin_student_detail'),
    path('admin/overview/', AdminSystemOverviewView.as_view(), name='admin_system_overview'),
]

