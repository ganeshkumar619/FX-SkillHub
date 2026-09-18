import logging
from django.utils import timezone
from datetime import timedelta
from .models import ProctoringEvent, RiskScore
from audit.models import AuditLog

logger = logging.getLogger(__name__)

class AssessmentSecurityEngine:
    """
    Dedicated, server-authoritative assessment security event engine.
    Enforces separate warning counters, debouncing, and automated termination policies.
    """

    VIOLATION_COUNTER_MAPPING = {
        'CAMERA_UNAVAILABLE': ('camera_warning_count', 'max_camera_warnings', 'Camera connection lost'),
        'CAMERA_DISCONNECTED': ('camera_warning_count', 'max_camera_warnings', 'Camera connection lost'),
        'CAMERA_COVERED_BLANK': ('camera_warning_count', 'max_camera_warnings', 'Camera feed is blank or covered'),
        'MULTIPLE_FACES_DETECTED': ('multiple_face_warning_count', 'max_multiple_face_warnings', 'Multiple faces detected in camera view'),
        'FACE_NOT_DETECTED': ('camera_warning_count', 'max_camera_warnings', 'Candidate face not detected in camera view'),
        'MOBILE_PHONE_DETECTED': ('tab_switch_warning_count', 'max_tab_switch_warnings', 'Mobile phone / unauthorized device detected in view'),
        'AI_ASSISTANCE_DETECTED': ('tab_switch_warning_count', 'max_tab_switch_warnings', 'Unauthorized external AI assistance detected'),
        'SCREEN_SHARE_STOPPED': ('screen_share_warning_count', 'max_screen_share_warnings', 'Screen sharing was stopped'),
        'FULLSCREEN_EXIT': ('fullscreen_warning_count', 'max_fullscreen_warnings', 'Fullscreen exam lock was exited'),
        'TAB_SWITCH': ('tab_switch_warning_count', 'max_tab_switch_warnings', 'Tab switch or browser blur detected'),
        'WINDOW_BLUR': ('tab_switch_warning_count', 'max_tab_switch_warnings', 'Exam window focus was lost'),
    }

    RECOVERY_EVENTS = {
        'CAMERA_RECONNECTED',
        'SCREEN_SHARE_RESUMED',
        'FULLSCREEN_RESTORED',
        'TAB_RESTORED',
        'ONE_FACE_DETECTED',
        'DEVICE_REMOVED',
    }

    @classmethod
    def process_security_event(cls, attempt, student, event_type, severity='MEDIUM', details=None):
        """
        Server-authoritative processing of incoming security signals.
        Returns:
            dict containing action_taken, counter stats, and current attempt status.
        """
        if details is None:
            details = {}

        now = timezone.now()
        assessment = attempt.assessment

        # If attempt is already terminated or completed, do not allow further modification
        if attempt.status == 'TERMINATED_SECURITY_VIOLATION':
            return {
                'status': 'already_terminated',
                'action_taken': 'NONE',
                'is_terminated': True,
                'termination_reason': attempt.termination_reason,
                'attempt_status': attempt.status
            }

        if attempt.status in ('SUBMITTED', 'EVALUATED', 'PASSED', 'FAILED'):
            return {
                'status': 'already_submitted',
                'action_taken': 'NONE',
                'is_terminated': False,
                'attempt_status': attempt.status
            }

        # Check for recovery events
        if event_type in cls.RECOVERY_EVENTS:
            ProctoringEvent.objects.create(
                attempt=attempt,
                student=student,
                event_type=event_type,
                severity='INFO',
                current_warning_count=0,
                action_taken='RECOVERY_RECORDED',
                details=details
            )

            # If attempt was in WARNING state, restore to IN_PROGRESS
            if attempt.status == 'WARNING':
                attempt.status = 'IN_PROGRESS'
                attempt.save(update_fields=['status'])

            RiskScore.compute_for_attempt(attempt)
            return {
                'status': 'recovered',
                'action_taken': 'RECOVERY_RECORDED',
                'is_terminated': False,
                'attempt_status': attempt.status,
                'event_type': event_type
            }

        # Check if event is a recognized security violation
        mapping = cls.VIOLATION_COUNTER_MAPPING.get(event_type)
        if not mapping:
            # General security / telemetry notice
            event = ProctoringEvent.objects.create(
                attempt=attempt,
                student=student,
                event_type=event_type,
                severity=severity,
                current_warning_count=0,
                action_taken='RECORDED',
                details=details
            )
            RiskScore.compute_for_attempt(attempt)
            return {
                'status': 'recorded',
                'action_taken': 'RECORDED',
                'is_terminated': False,
                'attempt_status': attempt.status
            }

        counter_field, max_limit_field, reason_desc = mapping
        max_allowed = getattr(assessment, max_limit_field, 2)
        auto_terminate = getattr(assessment, 'auto_terminate_on_limit', True)

        # Debounce check: Prevent duplicate count for the same physical incident within 5 seconds
        recent_cutoff = now - timedelta(seconds=5)
        recent_same_event = ProctoringEvent.objects.filter(
            attempt=attempt,
            event_type=event_type,
            timestamp__gte=recent_cutoff
        ).exists()

        current_count = getattr(attempt, counter_field)

        if recent_same_event:
            # Log event without incrementing counter again (same continuous incident)
            action_taken = 'INCIDENT_CONTINUATION'
        else:
            current_count += 1
            setattr(attempt, counter_field, current_count)

        # Check if warning limit exceeded
        # Special User Policy: MULTIPLE_FACES_DETECTED triggers continuous persistent warnings
        # and logs the infraction, but MUST NEVER auto-terminate the candidate's exam.
        can_auto_terminate = auto_terminate and (event_type != 'MULTIPLE_FACES_DETECTED')
        is_terminated = False
        termination_reason = None

        if current_count > max_allowed and can_auto_terminate:
            is_terminated = True
            action_taken = 'AUTO_TERMINATE'
            termination_reason = f"Security Violation: {reason_desc} exceeded allowed threshold ({current_count}/{max_allowed})."
            
            attempt.status = 'TERMINATED_SECURITY_VIOLATION'
            attempt.termination_reason = termination_reason
            attempt.terminated_at = now
            attempt.submitted_at = now
            # Evaluate answers submitted up to this moment
            attempt.evaluate()
            attempt.status = 'TERMINATED_SECURITY_VIOLATION'  # preserve status after evaluate()
            attempt.save()

            AuditLog.log_action(
                action='ASSESSMENT_TERMINATED_SECURITY',
                resource_type='AssessmentAttempt',
                resource_id=attempt.id,
                user=student,
                metadata={
                    'event_type': event_type,
                    'violations_count': current_count,
                    'max_allowed': max_allowed,
                    'reason': termination_reason
                }
            )
        else:
            if not recent_same_event:
                action_taken = 'WARNING_ISSUED'
                attempt.status = 'WARNING'
                attempt.save(update_fields=[counter_field, 'status'])
            else:
                action_taken = 'INCIDENT_CONTINUATION'

        # Record ProctoringEvent
        event = ProctoringEvent.objects.create(
            attempt=attempt,
            student=student,
            event_type=event_type,
            severity='CRITICAL' if is_terminated else severity,
            current_warning_count=current_count,
            action_taken=action_taken,
            details=details
        )

        # Recalculate RiskScore
        risk = RiskScore.compute_for_attempt(attempt)

        AuditLog.log_action(
            action='PROCTORING_VIOLATION_LOGGED',
            resource_type='ProctoringEvent',
            resource_id=event.id,
            user=student,
            metadata={
                'event_type': event_type,
                'counter_field': counter_field,
                'current_count': current_count,
                'max_allowed': max_allowed,
                'action_taken': action_taken,
                'risk_tier': risk.tier
            }
        )

        return {
            'status': 'recorded',
            'action_taken': action_taken,
            'warning_type': counter_field.replace('_warning_count', ''),
            'current_warning_count': current_count,
            'max_warnings': max_allowed,
            'is_terminated': is_terminated,
            'termination_reason': termination_reason,
            'attempt_status': attempt.status,
            'risk_tier': risk.tier,
            'risk_score': risk.numerical_score
        }
