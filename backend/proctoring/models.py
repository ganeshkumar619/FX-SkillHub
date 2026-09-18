from django.db import models
from django.conf import settings

class ProctoringEvent(models.Model):
    EVENT_TYPES = (
        ('TAB_SWITCH', 'Page Visibility / Tab Switched Away'),
        ('TAB_RESTORED', 'Tab Returned / Focus Restored'),
        ('FULLSCREEN_EXIT', 'Fullscreen Lock Exited'),
        ('FULLSCREEN_RESTORED', 'Fullscreen Lock Re-entered'),
        ('CAMERA_UNAVAILABLE', 'Camera Feed Lost / Inaccessible'),
        ('CAMERA_RECONNECTED', 'Camera Feed Reconnected'),
        ('CAMERA_DISCONNECTED', 'Video Track Stopped / Camera Inaccessible'),
        ('CAMERA_COVERED_BLANK', 'Camera Covered or Blank Screen Detected'),
        ('MULTIPLE_FACES_DETECTED', 'Multiple Faces Detected in View'),
        ('FACE_NOT_DETECTED', 'No Face Detected in View'),
        ('ONE_FACE_DETECTED', 'Single Verified Face in View (Normal)'),
        ('MOBILE_PHONE_DETECTED', 'Mobile Phone / Unauthorized Device Detected'),
        ('AI_ASSISTANCE_DETECTED', 'AI Assistant / External Help Tool Detected'),
        ('SCREEN_SHARE_STOPPED', 'Screen Sharing Session Disconnected'),
        ('SCREEN_SHARE_RESUMED', 'Screen Sharing Resumed'),
        ('SUSPICIOUS_KEY', 'Restricted Shortcut / Hotkey Detected'),
        ('WINDOW_BLUR', 'Window Lost Focus'),
        ('SECURITY_TERMINATION', 'Automated Session Termination for Violations'),
    )

    SEVERITY_LEVELS = (
        ('INFO', 'Informational Notice'),
        ('LOW', 'Minor Warning'),
        ('MEDIUM', 'Moderate Suspicious Signal'),
        ('HIGH', 'Major Integrity Signal'),
        ('CRITICAL', 'Severe Signal'),
    )

    attempt = models.ForeignKey('assessments.AssessmentAttempt', on_delete=models.CASCADE, related_name='proctoring_events')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name='proctoring_events')
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES, db_index=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_LEVELS, default='MEDIUM')
    current_warning_count = models.PositiveIntegerField(default=0, help_text="Warning count for this specific violation type at event time")
    action_taken = models.CharField(max_length=64, default='NONE', help_text="Action taken e.g. WARNING_ISSUED, AUTO_TERMINATE, RECORDED")
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['attempt', 'timestamp']

    def __str__(self):
        return f"[{self.severity}] {self.get_event_type_display()} on Attempt {self.attempt.id}"


class RiskScore(models.Model):
    TIER_CHOICES = (
        ('NORMAL', 'Normal Activity'),
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Moderate Risk'),
        ('HIGH', 'High Risk — Review Recommended'),
        ('CRITICAL', 'Critical Risk — Review Required'),
    )

    attempt = models.OneToOneField('assessments.AssessmentAttempt', on_delete=models.CASCADE, related_name='risk_assessment')
    numerical_score = models.FloatField(default=0.0, help_text="Calculated risk points (0 to 100)")
    tier = models.CharField(max_length=16, choices=TIER_CHOICES, default='NORMAL')
    event_count = models.PositiveIntegerField(default=0)
    evaluated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def compute_for_attempt(cls, attempt):
        """
        Calculates transparent risk score from event weights:
        - TAB_SWITCH: 15 pts
        - FULLSCREEN_EXIT: 20 pts
        - SCREEN_SHARE_STOPPED: 35 pts
        - CAMERA_DISCONNECTED: 30 pts
        - SUSPICIOUS_KEY: 10 pts
        - WINDOW_BLUR: 5 pts
        """
        weights = {
            'TAB_SWITCH': 15,
            'FULLSCREEN_EXIT': 20,
            'SCREEN_SHARE_STOPPED': 35,
            'CAMERA_DISCONNECTED': 30,
            'CAMERA_COVERED_BLANK': 25,
            'FACE_NOT_DETECTED': 20,
            'MULTIPLE_FACES_DETECTED': 25,
            'MOBILE_PHONE_DETECTED': 35,
            'AI_ASSISTANCE_DETECTED': 35,
            'SUSPICIOUS_KEY': 10,
            'WINDOW_BLUR': 5,
        }
        events = attempt.proctoring_events.all()
        total_score = 0.0
        for ev in events:
            base = weights.get(ev.event_type, 10)
            if ev.severity == 'CRITICAL':
                base *= 1.5
            total_score += base

        score = min(round(total_score, 1), 100.0)
        
        if score >= 70.0:
            tier = 'CRITICAL'
        elif score >= 50.0:
            tier = 'HIGH'
        elif score >= 25.0:
            tier = 'MEDIUM'
        elif score > 0.0:
            tier = 'LOW'
        else:
            tier = 'NORMAL'

        risk_obj, _ = cls.objects.update_or_create(
            attempt=attempt,
            defaults={
                'numerical_score': score,
                'tier': tier,
                'event_count': events.count()
            }
        )

        # If HIGH or CRITICAL, flag the attempt for human mentor review
        if tier in ('HIGH', 'CRITICAL'):
            attempt.review_status = 'PENDING_REVIEW'
            attempt.save(update_fields=['review_status'])
        return risk_obj

    def __str__(self):
        return f"Risk: {self.tier} ({self.numerical_score}/100) for Attempt {self.attempt.id}"


class MentorReviewRecord(models.Model):
    VERDICT_CHOICES = (
        ('VALID', 'Valid (Clear to issue certificate if passed)'),
        ('WARNING', 'Warning Issued (Result retained, warning recorded)'),
        ('INVALID', 'Invalidated (Misconduct confirmed by mentor)'),
        ('NEEDS_MORE_REVIEW', 'Needs Administrative Escalation'),
    )

    attempt = models.OneToOneField('assessments.AssessmentAttempt', on_delete=models.CASCADE, related_name='mentor_review')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='proctoring_reviews')
    verdict = models.CharField(max_length=24, choices=VERDICT_CHOICES)
    notes = models.TextField(help_text="Detailed audit notes explaining reviewer determination")
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Reflect reviewer verdict in attempt review_status
        self.attempt.review_status = self.verdict
        self.attempt.save(update_fields=['review_status'])

    def __str__(self):
        return f"Review by {self.reviewer.username}: {self.verdict} on Attempt {self.attempt.id}"
