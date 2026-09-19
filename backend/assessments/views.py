import datetime
from django.utils import timezone
from django.db.models import Q
from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from .serializers import (
    AssessmentBriefSerializer,
    AssessmentAttemptDetailSerializer,
    AssessmentResultSerializer,
    QuestionAdminSerializer,
    CodingQuestionCreateSerializer
)
from .skill_gap_service import SkillGapService
from .question_bank_service import QuestionBankService
from .code_execution_service import CodeExecutionService
from .ai_coding_service import AICodingQuestionService
from proctoring.models import ProctoringEvent, RiskScore
from learning.models import Enrollment
from audit.models import AuditLog
from catalogue.models import Course


def normalize_language_name(lang: str) -> str:
    if not lang:
        return ''
    l = lang.lower().strip()
    if l in ('python', 'py', 'python3'):
        return 'python'
    if l in ('c++', 'cpp'):
        return 'cpp'
    if l in ('java',):
        return 'java'
    if l in ('c',):
        return 'c'
    return l

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
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        final_assess = Assessment.objects.filter(
            course=course,
            assessment_type='FINAL_ASSESSMENT',
            is_published=True
        ).first()

        if not final_assess:
            # Check if faculty has added coding questions for this course
            has_coding = Question.objects.filter(course=course, question_type='CODING', approval_status='APPROVED').exists()
            if has_coding:
                final_assess = Assessment.objects.create(
                    course=course,
                    title=f"{course.title} Final Certification Assessment",
                    assessment_type='FINAL_ASSESSMENT',
                    duration_minutes=30,
                    pass_percentage=70.0,
                    is_published=True
                )
                Question.objects.filter(course=course, question_type='CODING', assessment__isnull=True).update(assessment=final_assess)
            else:
                return Response({'error': 'No final assessment configured for this course'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Ensure any approved coding questions for this course are linked to the final assessment
            Question.objects.filter(course=course, question_type='CODING', assessment__isnull=True).update(assessment=final_assess)

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

        # Handle coding question draft autosave
        if question.question_type == 'CODING':
            ans, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question=question)
            if 'submitted_code' in request.data:
                ans.submitted_code = request.data.get('submitted_code', '')
            if 'code_language' in request.data:
                ans.code_language = request.data.get('code_language', '')
            ans.save(update_fields=['submitted_code', 'code_language'])
            return Response({
                'status': 'saved',
                'question_id': question.id,
                'submitted_code': ans.submitted_code,
                'code_language': ans.code_language
            })

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

        # If payload contains coding answers, persist and evaluate them server-side if not yet evaluated
        coding_answers = request.data.get('coding_answers')
        if coding_answers and isinstance(coding_answers, dict):
            for q_id, c_data in coding_answers.items():
                if not q_id:
                    continue
                q_obj = Question.objects.filter(id=q_id, question_type='CODING').first()
                if q_obj and isinstance(c_data, dict):
                    code = c_data.get('code') or c_data.get('submitted_code')
                    lang = c_data.get('language') or c_data.get('code_language') or q_obj.programming_language
                    if code:
                        ans_obj, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question=q_obj)
                        if not ans_obj.total_test_cases or ans_obj.submitted_code != code:
                            eval_res = CodeExecutionService.evaluate_code(
                                language=normalize_language_name(lang),
                                code=code,
                                sample_test_cases=q_obj.sample_test_cases,
                                hidden_test_cases=q_obj.hidden_test_cases,
                                is_submission=True
                            )
                            ans_obj.submitted_code = code
                            ans_obj.code_language = normalize_language_name(lang)
                            ans_obj.test_cases_passed = eval_res.get('total_passed', 0)
                            ans_obj.total_test_cases = eval_res.get('total_count', 6)
                            ans_obj.is_correct = eval_res.get('passed', False)
                            ans_obj.marks_obtained = round((ans_obj.test_cases_passed / float(ans_obj.total_test_cases)) * q_obj.marks, 1) if ans_obj.total_test_cases > 0 else 0.0
                            ans_obj.code_execution_details = {
                                'sample_passed': eval_res.get('sample_passed', 0),
                                'sample_total': eval_res.get('sample_total', 2),
                                'hidden_passed': eval_res.get('hidden_passed', 0),
                                'hidden_total': eval_res.get('hidden_total', 4),
                                'total_passed': eval_res.get('total_passed', 0),
                                'total_count': eval_res.get('total_count', 6),
                                'passed': eval_res.get('passed', False),
                                'sample_results': eval_res.get('sample_results', []),
                                'hidden_summary': eval_res.get('hidden_summary', {})
                            }
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


class RunCodeView(views.APIView):
    """
    Executes student code against the 2 visible sample test cases only.
    Returns detailed input, expected output, actual output, and pass/fail for each sample.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id, student=request.user)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status == 'TERMINATED_SECURITY_VIOLATION':
            return Response({
                'error': 'Assessment attempt has been terminated for a security violation.',
                'status': 'TERMINATED_SECURITY_VIOLATION'
            }, status=status.HTTP_403_FORBIDDEN)

        if attempt.status not in ('IN_PROGRESS', 'WARNING') or attempt.is_expired():
            return Response({'error': 'Attempt is no longer in progress.'}, status=status.HTTP_400_BAD_REQUEST)

        question_id = request.data.get('question_id')
        code = request.data.get('code', '')
        language = request.data.get('language', '')

        if not question_id:
            return Response({'error': 'question_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not code or not code.strip():
            return Response({'error': 'Code cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

        question = Question.objects.filter(id=question_id).first()
        if not question:
            return Response({'error': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)

        if question.question_type != 'CODING':
            return Response({'error': 'Target question is not a coding question'}, status=status.HTTP_400_BAD_REQUEST)

        req_lang = normalize_language_name(question.programming_language)
        sub_lang = normalize_language_name(language)

        if req_lang and sub_lang != req_lang:
            return Response({
                'error': f"Language mismatch: This question requires {req_lang.upper()}, but you selected {sub_lang.upper()}."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Execute strictly against 2 sample test cases
        result = CodeExecutionService.evaluate_code(
            language=sub_lang,
            code=code,
            sample_test_cases=question.sample_test_cases,
            is_submission=False
        )

        return Response(result)


class SubmitCodeView(views.APIView):
    """
    Server-authoritatively evaluates student code against ALL 6 test cases (2 sample + 4 hidden).
    Saves student answer, calculates score, and returns test case summary WITHOUT leaking hidden data.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        try:
            attempt = AssessmentAttempt.objects.get(id=attempt_id, student=request.user)
        except AssessmentAttempt.DoesNotExist:
            return Response({'error': 'Attempt not found'}, status=status.HTTP_404_NOT_FOUND)

        if attempt.status == 'TERMINATED_SECURITY_VIOLATION':
            return Response({
                'error': 'Assessment attempt has been terminated for a security violation.',
                'status': 'TERMINATED_SECURITY_VIOLATION'
            }, status=status.HTTP_403_FORBIDDEN)

        if attempt.status not in ('IN_PROGRESS', 'WARNING') or attempt.is_expired():
            return Response({'error': 'Attempt is no longer in progress.'}, status=status.HTTP_400_BAD_REQUEST)

        question_id = request.data.get('question_id')
        code = request.data.get('code', '')
        language = request.data.get('language', '')

        if not question_id:
            return Response({'error': 'question_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not code or not code.strip():
            return Response({'error': 'Code cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

        question = Question.objects.filter(id=question_id).first()
        if not question:
            return Response({'error': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)

        if question.question_type != 'CODING':
            return Response({'error': 'Target question is not a coding question'}, status=status.HTTP_400_BAD_REQUEST)

        req_lang = normalize_language_name(question.programming_language)
        sub_lang = normalize_language_name(language)

        if req_lang and sub_lang != req_lang:
            return Response({
                'error': f"Language mismatch: This question requires {req_lang.upper()}, but you selected {sub_lang.upper()}."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Server-side execution against all 6 test cases
        result = CodeExecutionService.evaluate_code(
            language=sub_lang,
            code=code,
            sample_test_cases=question.sample_test_cases,
            hidden_test_cases=question.hidden_test_cases,
            is_submission=True
        )

        ans, _ = StudentAnswer.objects.get_or_create(attempt=attempt, question=question)
        ans.submitted_code = code
        ans.code_language = sub_lang
        ans.test_cases_passed = result.get('total_passed', 0)
        ans.total_test_cases = result.get('total_count', 6)
        ans.is_correct = result.get('passed', False)
        ans.marks_obtained = round((ans.test_cases_passed / float(ans.total_test_cases)) * question.marks, 1) if ans.total_test_cases > 0 else 0.0
        ans.code_execution_details = {
            'sample_passed': result.get('sample_passed', 0),
            'sample_total': result.get('sample_total', 2),
            'hidden_passed': result.get('hidden_passed', 0),
            'hidden_total': result.get('hidden_total', 4),
            'total_passed': result.get('total_passed', 0),
            'total_count': result.get('total_count', 6),
            'passed': result.get('passed', False),
            'sample_results': result.get('sample_results', []),
            'hidden_summary': result.get('hidden_summary', {})
        }
        ans.save()

        result['marks_obtained'] = ans.marks_obtained
        result['max_marks'] = question.marks

        return Response(result)


class CourseCodingQuestionListView(views.APIView):
    """
    List and create course-specific coding questions (Faculty & Admin).
    Enforces exactly 2 sample test cases + 4 hidden test cases.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        questions = Question.objects.filter(
            Q(course=course) | Q(assessment__course=course),
            question_type='CODING'
        ).distinct().order_by('-id')

        serializer = QuestionAdminSerializer(questions, many=True)
        return Response({
            'course_id': course.id,
            'course_title': course.title,
            'programming_language': course.get_programming_language(),
            'total_coding_questions': questions.count(),
            'questions': serializer.data
        })

    def post(self, request, course_id):
        if not (request.user.is_faculty() or request.user.role == 'ADMIN' or request.user.is_staff):
            return Response({'error': 'Only authorized faculty and mentors can create coding questions.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['course'] = course.id
        data['question_type'] = 'CODING'

        # Infer programming language if omitted
        if not data.get('programming_language'):
            data['programming_language'] = course.get_programming_language() or 'python'
        else:
            data['programming_language'] = normalize_language_name(data['programming_language'])

        # Set default text if omitted
        if not data.get('text') and data.get('problem_statement'):
            data['text'] = f"{data.get('title', 'Coding Question')}\n\n{data.get('problem_statement')}"

        serializer = CodingQuestionCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Check for semantic duplicates in this course
        statement = data.get('problem_statement') or data.get('text', '')
        is_dup, dup_msg = QuestionBankService.is_duplicate(course_id, statement)
        if is_dup:
            return Response({'error': f"Duplicate question detected: {dup_msg}"}, status=status.HTTP_400_BAD_REQUEST)

        # Optional reference solution validation
        ref_sol = data.get('reference_solution')
        if ref_sol and ref_sol.strip():
            is_valid, val_err = CodeExecutionService.validate_reference_solution(
                language=data['programming_language'],
                reference_solution=ref_sol,
                sample_test_cases=data.get('sample_test_cases', []),
                hidden_test_cases=data.get('hidden_test_cases', [])
            )
            if not is_valid:
                return Response({'error': f"Reference solution validation failed: {val_err}"}, status=status.HTTP_400_BAD_REQUEST)

        approval = data.get('approval_status') or 'APPROVED'
        question = serializer.save(
            is_bank_question=True,
            status='ACTIVE',
            question_type='CODING',
            approval_status=approval
        )

        # Set course.programming_language if missing
        if not course.programming_language and question.programming_language:
            course.programming_language = question.programming_language
            course.save(update_fields=['programming_language'])

        # Ensure course's FINAL_ASSESSMENT exists and link question
        final_assess = Assessment.objects.filter(course=course, assessment_type='FINAL_ASSESSMENT').first()
        if not final_assess:
            final_assess = Assessment.objects.create(
                course=course,
                title=f"{course.title} Final Certification Assessment",
                assessment_type='FINAL_ASSESSMENT',
                duration_minutes=30,
                pass_percentage=70.0,
                is_published=True
            )
        question.assessment = final_assess
        question.save(update_fields=['assessment'])

        return Response(QuestionAdminSerializer(question).data, status=status.HTTP_201_CREATED)


class CodingQuestionDetailView(views.APIView):
    """
    Retrieve, update, or delete a coding question (Faculty & Admin).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, question_id):
        return Question.objects.filter(id=question_id, question_type='CODING').first()

    def get(self, request, question_id):
        question = self.get_object(question_id)
        if not question:
            return Response({'error': 'Coding question not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionAdminSerializer(question).data)

    def put(self, request, question_id):
        if not (request.user.is_faculty() or request.user.role == 'ADMIN' or request.user.is_staff):
            return Response({'error': 'Only authorized faculty and mentors can edit coding questions.'}, status=status.HTTP_403_FORBIDDEN)

        question = self.get_object(question_id)
        if not question:
            return Response({'error': 'Coding question not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CodingQuestionCreateSerializer(question, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Validate reference solution if provided
        ref_sol = request.data.get('reference_solution') or question.reference_solution
        samples = request.data.get('sample_test_cases') or question.sample_test_cases
        hiddens = request.data.get('hidden_test_cases') or question.hidden_test_cases
        lang = normalize_language_name(request.data.get('programming_language') or question.programming_language)

        if ref_sol and ref_sol.strip():
            is_valid, val_err = CodeExecutionService.validate_reference_solution(
                language=lang,
                reference_solution=ref_sol,
                sample_test_cases=samples,
                hidden_test_cases=hiddens
            )
            if not is_valid:
                return Response({'error': f"Reference solution validation failed: {val_err}"}, status=status.HTTP_400_BAD_REQUEST)

        updated_q = serializer.save()
        return Response(QuestionAdminSerializer(updated_q).data)

    def patch(self, request, question_id):
        return self.put(request, question_id)

    def delete(self, request, question_id):
        if not (request.user.is_faculty() or request.user.role == 'ADMIN' or request.user.is_staff):
            return Response({'error': 'Only authorized faculty and mentors can delete coding questions.'}, status=status.HTTP_403_FORBIDDEN)

        question = self.get_object(question_id)
        if not question:
            return Response({'error': 'Coding question not found'}, status=status.HTTP_404_NOT_FOUND)

        question.delete()
        return Response({'message': 'Coding question deleted successfully.'}, status=status.HTTP_200_OK)


class CodingQuestionValidateView(views.APIView):
    """
    Validates a coding question's reference solution against all 6 test cases.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, question_id):
        question = Question.objects.filter(id=question_id, question_type='CODING').first()
        if not question:
            return Response({'error': 'Coding question not found'}, status=status.HTTP_404_NOT_FOUND)

        ref_sol = request.data.get('reference_solution') or question.reference_solution
        if not ref_sol:
            return Response({'error': 'No reference solution provided to validate.'}, status=status.HTTP_400_BAD_REQUEST)

        lang = normalize_language_name(request.data.get('language') or question.programming_language)
        samples = question.sample_test_cases or []
        hiddens = question.hidden_test_cases or []

        is_valid, val_err = CodeExecutionService.validate_reference_solution(
            language=lang,
            reference_solution=ref_sol,
            sample_test_cases=samples,
            hidden_test_cases=hiddens
        )

        return Response({
            'valid': is_valid,
            'error': val_err,
            'message': "Reference solution successfully passed all 6 test cases!" if is_valid else val_err
        })


class AICodingQuestionGenerateView(views.APIView):
    """
    Generates a beginner-friendly (EASY) coding question using AI grounded in course syllabus.
    Executes and validates the reference solution against all 6 test cases in the sandbox before saving.
    Saves as AI_GENERATED with approval_status='PENDING_REVIEW'.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not (request.user.is_faculty() or request.user.role == 'ADMIN' or request.user.is_staff):
            return Response({'error': 'Only faculty and mentors can generate coding questions.'}, status=status.HTTP_403_FORBIDDEN)

        course_id = request.data.get('course_id')
        preferred_lang = request.data.get('programming_language')
        topic = request.data.get('topic')

        if not course_id:
            return Response({'error': 'course_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        q_data, err = AICodingQuestionService.generate_and_validate_question(
            course_id=course.id,
            preferred_language=preferred_lang,
            topic=topic
        )

        if err or not q_data:
            return Response({
                'error': err or 'AI question validation failed. Please regenerate or edit the question.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create question record
        question = Question.objects.create(
            course=course,
            title=q_data['title'],
            problem_statement=q_data['problem_statement'],
            text=q_data['text'],
            topic_tag=q_data['topic_tag'],
            question_type='CODING',
            difficulty='EASY',
            marks=q_data.get('marks', 5),
            programming_language=q_data['programming_language'],
            input_format=q_data['input_format'],
            output_format=q_data['output_format'],
            constraints=q_data['constraints'],
            sample_test_cases=q_data['sample_test_cases'],
            hidden_test_cases=q_data['hidden_test_cases'],
            reference_solution=q_data['reference_solution'],
            is_bank_question=True,
            approval_status='PENDING_REVIEW',
            status='ACTIVE'
        )

        # Link to course's final assessment if available
        final_assess = Assessment.objects.filter(course=course, assessment_type='FINAL_ASSESSMENT').first()
        if final_assess:
            question.assessment = final_assess
            question.save(update_fields=['assessment'])

        return Response(QuestionAdminSerializer(question).data, status=status.HTTP_201_CREATED)


class CodingQuestionPublishView(views.APIView):
    """
    Enables faculty to review and publish/approve a coding question (e.g. AI-generated or draft).
    Validates that:
    1. Exactly 2 visible sample test cases and 4 hidden test cases exist.
    2. Reference solution passes all 6 test cases in the sandbox.
    3. Sets approval_status to 'APPROVED' and activates it for the final assessment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, question_id):
        if not (request.user.is_faculty() or request.user.role == 'ADMIN' or request.user.is_staff):
            return Response({'error': 'Only authorized faculty and mentors can publish coding questions.'}, status=status.HTTP_403_FORBIDDEN)

        question = Question.objects.filter(id=question_id, question_type='CODING').first()
        if not question:
            return Response({'error': 'Coding question not found'}, status=status.HTTP_404_NOT_FOUND)

        # Validate test cases structure
        samples = question.sample_test_cases or []
        hiddens = question.hidden_test_cases or []

        if len(samples) != 2:
            return Response({'error': f"Coding question must have exactly 2 sample test cases, found {len(samples)}."}, status=status.HTTP_400_BAD_REQUEST)
        if len(hiddens) != 4:
            return Response({'error': f"Coding question must have exactly 4 hidden test cases, found {len(hiddens)}."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate reference solution in sandbox if present
        ref_sol = question.reference_solution
        if ref_sol and ref_sol.strip():
            lang = normalize_language_name(question.programming_language)
            is_valid, val_err = CodeExecutionService.validate_reference_solution(
                language=lang,
                reference_solution=ref_sol,
                sample_test_cases=samples,
                hidden_test_cases=hiddens
            )
            if not is_valid:
                return Response({'error': f"Reference solution validation failed before publishing: {val_err}"}, status=status.HTTP_400_BAD_REQUEST)

        # Set approved and active
        question.approval_status = 'APPROVED'
        question.status = 'ACTIVE'
        question.is_bank_question = True

        # Attach to course final assessment if available
        if question.course:
            if not question.assessment:
                final_assess = Assessment.objects.filter(course=question.course, assessment_type='FINAL_ASSESSMENT').first()
                if not final_assess:
                    final_assess = Assessment.objects.create(
                        course=question.course,
                        title=f"{question.course.title} - Final Assessment",
                        assessment_type='FINAL_ASSESSMENT',
                        status='PUBLISHED',
                        passing_score=50.0,
                        duration_minutes=45,
                        total_marks=100.0,
                    )
                question.assessment = final_assess

            if question.programming_language and not question.course.programming_language:
                question.course.programming_language = question.programming_language
                question.course.save(update_fields=['programming_language'])

        question.save()

        return Response({
            'message': 'Coding question reviewed and published successfully.',
            'question': QuestionAdminSerializer(question).data
        }, status=status.HTTP_200_OK)


