from django.urls import path
from .views import (
    EmailLogListView,
    EmailStatusDiagnosticsView,
    EmailTestDispatchView
)

urlpatterns = [
    path('logs/', EmailLogListView.as_view(), name='email_logs'),
    path('logs/<str:pk>/', EmailLogListView.as_view(), name='email_log_detail'),
    path('status/', EmailStatusDiagnosticsView.as_view(), name='email_status_diagnostics'),
    path('test-email/', EmailTestDispatchView.as_view(), name='email_test_dispatch'),
]
