from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    action = models.CharField(max_length=128, db_index=True)
    resource_type = models.CharField(max_length=64, db_index=True)
    resource_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    @classmethod
    def log_action(cls, action, resource_type, resource_id="", user=None, ip_address=None, metadata=None):
        return cls.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            ip_address=ip_address,
            metadata=metadata or {}
        )

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {user_str}: {self.action} on {self.resource_type}:{self.resource_id}"
