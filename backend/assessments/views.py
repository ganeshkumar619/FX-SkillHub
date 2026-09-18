import datetime
from django.utils import timezone
from django.db.models import Q
from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from .serializers import (
    AssessmentBriefSerializer,
    AssessmentAttemptDetailSerializer,
    AssessmentResultSerializer
)
from .skill_gap_service import SkillGapService
from .question_bank_service import QuestionBankService
from proctoring.models import ProctoringEvent, RiskScore
from learning.models import Enrollment
from audit.models import AuditLog

class CoursePreAssessmentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        pre_assess = Assessment.objects.filter(
            course_id=course_id,
            assessment_type='PRE_ASSESSMENT',
            is_published=True
        ).first()
        if not pre_assess:
            return Response({'error': 'No pre-assessment available for this course'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AssessmentBriefSerializer(pre_assess).data)


class CourseFinalAssessmentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        final_assess = Assessment.objects.filter(
            course_id=course_id,
            assessment_type='FINAL_ASSESSMENT',
            is_published=True
        ).first()
        if not final_assess:
            return Response({'error': 'No final assessment configured for this course'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AssessmentBriefSerializer(final_assess).data)


class AssessmentEligibilityCheckView(views.APIView):
    """
    Checks if authenticated user is eligible to take a specific assessment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, assessment_id):
        try:
            assessment = Assessment.objects.select_related('course').get(id=assessment_id, is_published=True)
        except Assessment.DoesNotExist:
            return Response({'error': 'Assessment not found'}, status=status.HTTP_404_NOT_FOUND)

        if assessment.assessment_type != 'FINAL_ASSESSMENT':
            return Response({
                'eligible': True,
                'course_id': assessment.course.id,
                'course_slug': assessment.course.slug,
                'course_title': assessment.course.title,
                'reason': None
            })

        enrollment = Enrollment.objects.filter(student=request.user, course=assessment.course).first()
        if not enrollment:
            req_mods = assessment.course.modules.filter(is_required=True, status='PUBLISHED').count()
            return Response({
                'eligible': False,
                'course_id': assessment.course.id,
                'course_slug': assessment.course.slug,
                'course_title': assessment.course.title,
                'course_progress': 0.0,
                'completed_modules': 0,
                'total_required_modules': req_mods,
                'reason': 'Complete all required modules before starting the assessment.'
            })

        eligible, progress, completed_req, total_req, reason = enrollment.is_assessment_eligible()
        return Response({
            'eligible': eligible,
            'course_id': assessment.course.id,
            'course_slug': assessment.course.slug,
            'course_title': assessment.course.title,
            'course_progress': progress,
            'completed_modules': completed_req,
            'total_required_modules': total_req,
            'reason': reason or ('Complete all required modules before starting the assessment.' if not eligible else None)
        })


class StartAttemptView(views.APIView):
    """
    Initializes a secure, server-authoritative assessment attempt.
    Calculates server_deadline = now + duration_minutes.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, assessment_id):
        try:
            assessment = Assessment.objects.get(id=assessment_id, is_published=True)
        except Assessment.DoesNotExist:
            return Response({'error': 'Assessment not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check existing active attempt
        existing = AssessmentAttempt.objects.filter(
            assessment=assessment,
            student=request.user,
            status='IN_PROGRESS'
        ).first()

        if existing:
            if not existing.is_expired():
                return Response(AssessmentAttemptDetailSerializer(existing).data)
            else:
                existing.status = 'EXPIRED'
                existing.evaluate()
                existing.save()

        # Enforce server-authoritative eligibility lock for FINAL_ASSESSMENT
        enrollment = Enrollment.objects.filter(student=request.user, course=assessment.course).first()
        if assessment.assessment_type == 'FINAL_ASSESSMENT':
            if not enrollment:
                return Response({
                    'error': 'Enrollment required. You must enroll and complete all required course modules before taking the final assessment.',
                    'eligible': False,
                    'course_progress': 0.0,
                    'completed_modules': 0,
                    'total_required_modules': assessment.course.modules.filter(is_required=True, status='PUBLISHED').count()
                }, status=status.HTTP_403_FORBIDDEN)

            eligible, progress, completed_req, total_req, reason = enrollment.is_assessment_eligible()
            if not eligible:
                return Response({
                    'error': reason or 'Complete all required modules before starting the assessment.',
                    'eligible': False,
                    'course_progress': progress,
                    'completed_modules': completed_req,
                    'total_required_modules': total_req
                }, status=status.HTTP_403_FORBIDDEN)
        
        now = timezone.now()
        deadline = now + datetime.timedelta(minutes=assessment.duration_minutes)

        selected_ids, option_orders_map = QuestionBankService.prepare_attempt_questions(
            assessment=assessment,
            randomize_options=assessment.randomize_options
        )

        attempt = AssessmentAttempt.objects.create(
            assessment=assessment,
            student=request.user,
            enrollment=enrollment,
            status='IN_PROGRESS',
            server_deadline=deadline,
            selected_question_ids=selected_ids,
            question_option_orders=option_orders_map,
            is_demo=getattr(request.user, 'is_demo', False)
        )

        AuditLog.log_action(
            action='ASSESSMENT_STARTED',
            resource_type='AssessmentAttempt',
            resource_id=attempt.id,
            user=request.user,
            metadata={'assessment': assessment.title, 'deadline': deadline.isoformat()}
        )

        return Response(AssessmentAttemptDetailSerializer(attempt).data, status=status.HTTP_201_CREATED)


class AttemptDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id, student=request.user)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status == 'IN_PROGRESS' and attempt.is_expired():
            attempt.status = 'EXPIRED'
            attempt.evaluate()
            attempt.save()

        return Response(AssessmentAttemptDetailSerializer(attempt).data)


class AutosaveAnswerView(views.APIView):
    """
    Autosaves student answers in real-time as choices are selected.
    Uses database Option IDs as authoritative source of truth.
    Strictly validates:
    - Question belongs to this assessment or attempt's question pool.
    - Selected option(s) belong strictly to the target question (rejects mismatched IDs).
    - Strictly rejects updates if attempt was terminated for security violations.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id, student=request.user)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status == 'TERMINATED_SECURITY_VIOLATION':
            return Response({
                'error': 'Assessment attempt has been terminated for a security violation. Further answer modifications are strictly rejected.',
                'status': 'TERMINATED_SECURITY_VIOLATION',
                'termination_reason': attempt.termination_reason
            }, status=status.HTTP_403_FORBIDDEN)

        if attempt.status not in ('IN_PROGRESS', 'WARNING') or attempt.is_expired():
            return Response({'error': 'Attempt is no longer in progress.'}, status=status.HTTP_400_BAD_REQUEST)

        question_id = request.data.get('question_id')
        if not question_id:
            return Response({'error': 'question_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Accept either selected_option_id, option_ids, or selected_option_ids
        selected_option_id = request.data.get('selected_option_id')
        option_ids = request.data.get('option_ids')
        if option_ids is None and request.data.get('selected_option_ids') is not None:
            option_ids = request.data.get('selected_option_ids')

        if option_ids is None:
            option_ids = [selected_option_id] if selected_option_id is not None else []
        elif selected_option_id is not None and selected_option_id not in option_ids:
            option_ids.append(selected_option_id)

        # 1. Validate Question belongs to this attempt (either explicitly sampled or linked to assessment/course)
        question = None
        if attempt.selected_question_ids and int(question_id) in [int(x) for x in attempt.selected_question_ids]:
            question = Question.objects.filter(id=question_id).first()
        elif attempt.assessment:
            question = Question.objects.filter(
                Q(id=question_id, assessment=attempt.assessment) | 
                Q(id=question_id, course=attempt.assessment.course)
            ).first()

        if not question:
            return Response({'error': 'Question does not belong to this assessment'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Validate Selected Options belong strictly to this question (Section 7)
        if option_ids:
            # Check for any option that does not belong to this question
            mismatched = QuestionOption.objects.filter(id__in=option_ids).exclude(question=question)
            if mismatched.exists():
                return Response({
                    'error': f'Selected option ID(s) do not belong to question {question_id}. Mismatched option submission rejected.'
                }, status=status.HTTP_400_BAD_REQUEST)

            valid_options = list(QuestionOption.objects.filter(id__in=option_ids, question=question))
            if len(valid_options) != len(option_ids):
                return Response({'error': 'One or more invalid option IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            valid_options = []

        ans, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question=question)
        ans.selected_options.set(valid_options)
        ans.save()

        return Response({
            'status': 'saved', 
            'question_id': question.id,
            'selected_option_ids': [o.id for o in valid_options]
        })


class LogProctoringEventView(views.APIView):
    """
    Processes proctoring events via server-authoritative AssessmentSecurityEngine.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id, student=request.user)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        event_type = request.data.get('event_type')
        severity = request.data.get('severity', 'MEDIUM')
        details = request.data.get('details', {})

        if not event_type:
            return Response({'error': 'event_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        from proctoring.security_engine import AssessmentSecurityEngine
        engine_result = AssessmentSecurityEngine.process_security_event(
            attempt=attempt,
            student=request.user,
            event_type=event_type,
            severity=severity,
            details=details
        )

        return Response(engine_result)


class SubmitAssessmentView(views.APIView):
    """
    Evaluates answers, computes pass/fail and topic mastery,
    computes final proctoring risk score, and records completion.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id, student=request.user)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status == 'TERMINATED_SECURITY_VIOLATION':
            return Response(AssessmentResultSerializer(attempt).data, status=status.HTTP_200_OK)

        if attempt.status not in ('IN_PROGRESS', 'WARNING', 'EXPIRED'):
            return Response(AssessmentResultSerializer(attempt).data)

        # If payload contains final answers, persist them authoritatively before evaluation
        submitted_answers = request.data.get('answers')
        if submitted_answers and isinstance(submitted_answers, (dict, list)):
            items = submitted_answers.items() if isinstance(submitted_answers, dict) else [
                (item.get('question_id'), item.get('selected_option_id') or item.get('option_ids'))
                for item in submitted_answers if isinstance(item, dict)
            ]
            for q_id, opt_data in items:
                if not q_id:
                    continue
                q_obj = Question.objects.filter(id=q_id).first()
                if not q_obj:
                    continue
                if isinstance(opt_data, (int, str)):
                    opt_list = [opt_data]
                elif isinstance(opt_data, list):
                    opt_list = opt_data
                else:
                    opt_list = []
                
                valid_opts = list(QuestionOption.objects.filter(id__in=opt_list, question=q_obj))
                ans_obj, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question=q_obj)
                ans_obj.selected_options.set(valid_opts)
                ans_obj.save()

        attempt.submitted_at = timezone.now()
        attempt.evaluate()

        # Compute risk score
        risk = RiskScore.compute_for_attempt(attempt)

        # If this was a diagnostic pre-assessment, run skill-gap diagnosis
        skill_gap_result = None
        if attempt.assessment.assessment_type == 'PRE_ASSESSMENT':
            skill_gap_result = SkillGapService.analyze_skill_gap(attempt)

        AuditLog.log_action(
            action='ASSESSMENT_SUBMITTED',
            resource_type='AssessmentAttempt',
            resource_id=attempt.id,
            user=request.user,
            metadata={
                'score': attempt.score,
                'percentage': attempt.percentage,
                'passed': attempt.passed,
                'risk_tier': risk.tier
            }
        )

        resp_data = AssessmentResultSerializer(attempt).data
        if skill_gap_result:
            resp_data['skill_gap_analysis'] = skill_gap_result

        return Response(resp_data)


class AssessmentAttemptResultView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id, student=request.user)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        resp_data = AssessmentResultSerializer(attempt).data
        if attempt.assessment.assessment_type == 'PRE_ASSESSMENT':
            resp_data['skill_gap_analysis'] = SkillGapService.analyze_skill_gap(attempt)

        return Response(resp_data)
