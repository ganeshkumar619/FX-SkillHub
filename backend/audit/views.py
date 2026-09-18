from rest_framework import views, permissions
from rest_framework.response import Response
from .models import AuditLog
from authentication.permissions import IsAdmin
from catalogue.models import Course, Department

class AuditLogListView(views.APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:50]
        data = [
            {
                'id': l.id,
                'user': l.user.username if l.user else 'System',
                'action': l.action,
                'resource_type': l.resource_type,
                'resource_id': l.resource_id,
                'ip_address': l.ip_address,
                'metadata': l.metadata,
                'timestamp': l.timestamp,
            }
            for l in logs
        ]
        return Response(data)

    def delete(self, request, pk=None):
        log_id = pk or request.data.get('id')
        if log_id:
            AuditLog.objects.filter(id=log_id).delete()
            return Response({'message': f"Audit log #{log_id} deleted."}, status=200)
        else:
            count = AuditLog.objects.count()
            AuditLog.objects.all().delete()
            return Response({'message': f"All {count} audit logs cleared."}, status=200)


class ContentProvenanceAuditView(views.APIView):
    """
    Returns an institutional audit list of all courses and their provenance verification status.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        courses = Course.objects.select_related('department', 'skill').all()
        results = [
            {
                'id': c.id,
                'title': c.title,
                'department': c.department.name if c.department else 'Institutional',
                'source_type': c.source_type,
                'source_url': c.source_url,
                'source_title': c.source_title,
                'source_accessed_at': c.source_accessed_at,
                'last_verified_at': c.last_verified_at,
                'content_status': c.content_status,
                'is_demo': c.is_demo,
            }
            for c in courses
        ]
        return Response(results)
