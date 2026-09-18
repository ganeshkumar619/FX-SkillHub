from django.urls import path
from .views import AuditLogListView, ContentProvenanceAuditView

urlpatterns = [
    path('logs/', AuditLogListView.as_view(), name='audit_logs'),
    path('logs/<int:pk>/', AuditLogListView.as_view(), name='audit_log_detail'),
    path('provenance/', ContentProvenanceAuditView.as_view(), name='provenance_audit'),
]
