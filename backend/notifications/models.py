import uuid
from django.db import models

class EmailLog(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Dispatch'),
        ('SENT', 'Sent Successfully'),
        ('FAILED', 'Failed to Deliver'),
        ('PENDING_RETRY', 'Pending Retry'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    certificate = models.ForeignKey('certificates.Certificate', null=True, blank=True, on_delete=models.SET_NULL, related_name='email_logs')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True, db_index=True, help_text="Prevents duplicate email deliveries for the same certificate")
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Email to {self.recipient_email} - {self.status} ({self.subject})"
