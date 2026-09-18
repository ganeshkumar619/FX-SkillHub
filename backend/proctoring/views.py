from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import ProctoringEvent, RiskScore, MentorReviewRecord
from assessments.models import AssessmentAttempt
from authentication.permissions import IsMentorOrAdmin
from audit.models import AuditLog

class MentorReviewQueueView(views.APIView):
    permission_classes = [IsMentorOrAdmin]

    def get(self, request):
        filter_mode = request.query_params.get('filter', 'all')
        
        queryset = AssessmentAttempt.objects.select_related(
            'student', 'assessment', 'assessment__course', 'risk_assessment'
        )

        if filter_mode == 'flagged':
            queryset = queryset.filter(review_status__in=['PENDING_REVIEW', 'WARNING', 'INVALID']) | queryset.filter(status='TERMINATED_SECURITY_VIOLATION')
        else:
            # show all evaluated/completed/flagged/terminated attempts
            queryset = queryset.exclude(status__in=['IN_PROGRESS', 'READY'])

        queryset = queryset.order_by('-started_at')[:50]

        results = []
        for att in queryset:
            risk = getattr(att, 'risk_assessment', None)
            results.append({
                'attempt_id': att.id,
                'student_username': att.student.username,
                'student_name': att.student.get_full_name() or att.student.username,
                'course_title': att.assessment.course.title,
                'assessment_title': att.assessment.title,
                'score': att.score,
                'percentage': att.percentage,
                'passed': att.passed,
                'status': att.status,
                'review_status': att.review_status,
                'risk_tier': risk.tier if risk else 'NORMAL',
                'risk_score': risk.numerical_score if risk else 0.0,
                'events_count': risk.event_count if risk else 0,
                'camera_violations': att.camera_warning_count,
                'multiple_face_violations': att.multiple_face_warning_count,
                'screen_share_violations': att.screen_share_warning_count,
                'fullscreen_violations': att.fullscreen_warning_count,
                'tab_switch_violations': att.tab_switch_warning_count,
                'termination_reason': att.termination_reason,
                'terminated_at': att.terminated_at,
                'started_at': att.started_at,
            })
        return Response(results)


class AttemptEventsDetailView(views.APIView):
    permission_classes = [IsMentorOrAdmin]

    def get(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.select_related('student', 'assessment').get(id=attempt_id)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        events = attempt.proctoring_events.all()
        risk = getattr(attempt, 'risk_assessment', None)
        review = getattr(attempt, 'mentor_review', None)

        events_data = [
            {
                'id': ev.id,
                'event_type': ev.event_type,
                'severity': ev.severity,
                'timestamp': ev.timestamp,
                'details': ev.details,
            }
            for ev in events
        ]

        return Response({
            'attempt_id': attempt.id,
            'student_name': attempt.student.get_full_name() or attempt.student.username,
            'assessment_title': attempt.assessment.title,
            'status': attempt.status,
            'review_status': attempt.review_status,
            'risk_tier': risk.tier if risk else 'NORMAL',
            'risk_score': risk.numerical_score if risk else 0.0,
            'camera_violations': attempt.camera_warning_count,
            'multiple_face_violations': attempt.multiple_face_warning_count,
            'screen_share_violations': attempt.screen_share_warning_count,
            'fullscreen_violations': attempt.fullscreen_warning_count,
            'tab_switch_violations': attempt.tab_switch_warning_count,
            'termination_reason': attempt.termination_reason,
            'terminated_at': attempt.terminated_at,
            'events': events_data,
            'existing_review': {
                'verdict': review.verdict,
                'notes': review.notes,
                'reviewer': review.reviewer.username,
                'reviewed_at': review.reviewed_at
            } if review else None
        })


class SubmitMentorVerdictView(views.APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        verdict = request.data.get('verdict')
        notes = request.data.get('notes', '')

        if not verdict:
            return Response({'error': 'verdict is required'}, status=status.HTTP_400_BAD_REQUEST)

        review, _ = MentorReviewRecord.objects.update_or_create(
            attempt=attempt,
            defaults={
                'reviewer': request.user,
                'verdict': verdict,
                'notes': notes
            }
        )

        AuditLog.log_action(
            action='MENTOR_REVIEW_SUBMITTED',
            resource_type='AssessmentAttempt',
            resource_id=attempt.id,
            user=request.user,
            metadata={'verdict': verdict, 'notes': notes}
        )

        return Response({
            'status': 'recorded',
            'verdict': review.verdict,
            'notes': review.notes,
            'reviewer': request.user.username,
            'reviewed_at': review.reviewed_at
        })
