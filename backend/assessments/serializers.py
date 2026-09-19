from django.db.models import Q
from rest_framework import serializers
from .models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from proctoring.models import RiskScore

class QuestionOptionSafeSerializer(serializers.ModelSerializer):
    """Safe option serializer for students during examination — strips correct answer flag."""
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'order']

class QuestionSafeSerializer(serializers.ModelSerializer):
    """Safe question serializer for students — strips correct answer, explanation, and hidden test cases."""
    options = QuestionOptionSafeSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'text', 'title', 'topic_tag', 'question_type', 'difficulty', 'marks', 'order', 'options',
            'problem_statement', 'programming_language', 'input_format', 'output_format', 'constraints',
            'sample_test_cases'
        ]

class AssessmentBriefSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)
    coding_question = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            'id', 'title', 'assessment_type', 'version',
            'duration_minutes', 'pass_percentage', 'max_attempts',
            'questions_count', 'coding_question',
            'camera_required', 'screen_share_required', 'fullscreen_required',
            'face_detection_enabled', 'max_camera_warnings', 'max_multiple_face_warnings',
            'max_screen_share_warnings', 'max_fullscreen_warnings', 'max_tab_switch_warnings',
            'multiple_faces_threshold_seconds', 'auto_terminate_on_limit'
        ]

    def get_coding_question(self, obj):
        course = obj.course
        if not course:
            return None
        course_prog_lang = course.get_programming_language() if hasattr(course, 'get_programming_language') else None

        coding_qs = Question.objects.filter(
            Q(assessment=obj) | Q(course=course),
            question_type='CODING',
            approval_status='APPROVED'
        ).distinct()

        if not (course_prog_lang or coding_qs.exists()):
            return None

        if course_prog_lang:
            lang_matched = coding_qs.filter(programming_language__iexact=course_prog_lang)
            if lang_matched.exists():
                coding_qs = lang_matched

        if not coding_qs.exists():
            return None

        assess_q = coding_qs.filter(assessment=obj)
        coding_q = assess_q.first() if assess_q.count() == 1 else coding_qs.order_by('order', 'id').first()

        return {
            'id': coding_q.id,
            'title': coding_q.title or coding_q.text,
            'problem_statement': coding_q.problem_statement or coding_q.text,
            'input_format': coding_q.input_format or '',
            'output_format': coding_q.output_format or '',
            'constraints': coding_q.constraints or '',
            'difficulty': coding_q.difficulty or 'EASY',
            'programming_language': (coding_q.programming_language or course_prog_lang or 'c').upper(),
            'sample_test_cases': [
                {
                    'input': str(tc.get('input', '')),
                    'expected_output': str(tc.get('expected_output') or tc.get('output', ''))
                }
                for tc in (coding_q.sample_test_cases or [])[:2]
            ]
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('coding_question'):
            data['assessment_type'] = 'CODING'
        return data

class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = [
            'question', 'selected_options', 'answered_at',
            'submitted_code', 'code_language', 'test_cases_passed', 'total_test_cases', 'code_execution_details'
        ]

class AssessmentAttemptDetailSerializer(serializers.ModelSerializer):
    assessment = AssessmentBriefSerializer(read_only=True)
    questions = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    coding_answers = serializers.SerializerMethodField()
    coding_question = serializers.SerializerMethodField()
    assessment_type = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentAttempt
        fields = [
            'id', 'assessment', 'status', 'started_at',
            'server_deadline', 'score', 'percentage', 'passed',
            'review_status', 'questions', 'answers', 'coding_answers',
            'coding_question', 'assessment_type',
            'camera_warning_count', 'multiple_face_warning_count',
            'screen_share_warning_count', 'fullscreen_warning_count',
            'tab_switch_warning_count', 'termination_reason', 'terminated_at'
        ]

    def get_coding_question(self, obj):
        brief_serializer = AssessmentBriefSerializer(obj.assessment)
        return brief_serializer.get_coding_question(obj.assessment)

    def get_assessment_type(self, obj):
        if self.get_coding_question(obj):
            return 'CODING'
        return obj.assessment.assessment_type

    def get_questions(self, obj):
        if obj.selected_question_ids:
            questions_qs = Question.objects.filter(id__in=obj.selected_question_ids).prefetch_related('options')
            q_map = {q.id: q for q in questions_qs}
            ordered_questions = [q_map[qid] for qid in obj.selected_question_ids if qid in q_map]
        else:
            ordered_questions = list(obj.assessment.questions.prefetch_related('options').all())

        coding_q_data = self.get_coding_question(obj)
        if coding_q_data and not any(q.question_type == 'CODING' for q in ordered_questions):
            coding_obj = Question.objects.filter(id=coding_q_data['id']).first()
            if coding_obj:
                ordered_questions.append(coding_obj)

        data = []
        option_orders = obj.question_option_orders or {}
        for q in ordered_questions:
            q_data = QuestionSafeSerializer(q).data
            q_opt_order = option_orders.get(str(q.id))
            if q_opt_order and 'options' in q_data:
                opt_map = {opt['id']: opt for opt in q_data['options']}
                q_data['options'] = [opt_map[oid] for oid in q_opt_order if oid in opt_map]
            data.append(q_data)
        return data

    def get_answers(self, obj):
        result = {}
        for ans in obj.answers.all():
            result[ans.question_id] = list(ans.selected_options.values_list('id', flat=True))
        return result

    def get_coding_answers(self, obj):
        result = {}
        for ans in obj.answers.filter(question__question_type='CODING'):
            result[ans.question_id] = {
                'submitted_code': ans.submitted_code,
                'code_language': ans.code_language,
                'test_cases_passed': ans.test_cases_passed,
                'total_test_cases': ans.total_test_cases,
                'code_execution_details': ans.code_execution_details
            }
        return result

class RiskScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskScore
        fields = ['numerical_score', 'tier', 'event_count', 'evaluated_at']

class AssessmentResultSerializer(serializers.ModelSerializer):
    assessment = AssessmentBriefSerializer(read_only=True)
    risk_assessment = RiskScoreSerializer(read_only=True)
    review_data = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentAttempt
        fields = [
            'id', 'assessment', 'status', 'started_at',
            'submitted_at', 'score', 'percentage', 'passed',
            'topic_breakdown', 'review_status', 'risk_assessment',
            'camera_warning_count', 'multiple_face_warning_count',
            'screen_share_warning_count', 'fullscreen_warning_count',
            'tab_switch_warning_count', 'termination_reason', 'terminated_at',
            'review_data'
        ]

    def get_review_data(self, obj):
        try:
            from .wrong_answer_service import WrongAnswerReviewService
            return WrongAnswerReviewService.generate_attempt_review(obj)
        except Exception as e:
            return {'error': str(e), 'detailed_questions': []}


class QuestionOptionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionAdminSerializer(serializers.ModelSerializer):
    options = QuestionOptionAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'course_id', 'text', 'title', 'topic_tag', 'question_type', 'difficulty', 'marks',
            'explanation', 'order', 'options', 'status', 'is_bank_question',
            'problem_statement', 'programming_language', 'input_format', 'output_format',
            'constraints', 'sample_test_cases', 'hidden_test_cases', 'reference_solution',
            'approval_status'
        ]


class CodingQuestionCreateSerializer(serializers.ModelSerializer):
    topic_tag = serializers.CharField(required=False, default='coding')
    text = serializers.CharField(required=False, default='')

    class Meta:
        model = Question
        fields = [
            'id', 'course', 'text', 'title', 'topic_tag', 'difficulty', 'marks',
            'problem_statement', 'programming_language', 'input_format', 'output_format',
            'constraints', 'sample_test_cases', 'hidden_test_cases', 'reference_solution',
            'approval_status'
        ]

    def validate(self, attrs):
        prog_lang = (attrs.get('programming_language') or '').lower()
        valid_langs = ['c', 'cpp', 'java', 'python']
        if prog_lang not in valid_langs:
            raise serializers.ValidationError({'programming_language': f"Language must be one of {valid_langs}"})

        samples = attrs.get('sample_test_cases') or []
        if len(samples) != 2:
            raise serializers.ValidationError({'sample_test_cases': "Exactly 2 sample test cases required."})

        hiddens = attrs.get('hidden_test_cases') or []
        if len(hiddens) != 4:
            raise serializers.ValidationError({'hidden_test_cases': "Exactly 4 hidden test cases required."})

        for s in samples:
            if 'output' not in s and 'expected_output' in s:
                s['output'] = s['expected_output']
            if 'input' not in s or 'output' not in s:
                raise serializers.ValidationError({'sample_test_cases': "Each sample test case must have 'input' and 'output' (or 'expected_output')."})

        for h in hiddens:
            if 'output' not in h and 'expected_output' in h:
                h['output'] = h['expected_output']
            if 'input' not in h or 'output' not in h:
                raise serializers.ValidationError({'hidden_test_cases': "Each hidden test case must have 'input' and 'output' (or 'expected_output')."})

        return attrs


class AssessmentAdminSerializer(serializers.ModelSerializer):
    questions = QuestionAdminSerializer(many=True, read_only=True)
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)
    total_marks = serializers.SerializerMethodField()

    def get_total_marks(self, obj):
        return sum(q.marks for q in obj.questions.all())

    class Meta:
        model = Assessment
        fields = [
            'id', 'course_id', 'title', 'assessment_type', 'version',
            'duration_minutes', 'pass_percentage', 'max_attempts',
            'randomize_questions', 'randomize_options', 'is_published',
            'is_ai_generated', 'blueprint', 'questions_count', 'total_marks',
            'camera_required', 'screen_share_required', 'fullscreen_required',
            'face_detection_enabled', 'max_camera_warnings', 'max_multiple_face_warnings',
            'max_screen_share_warnings', 'max_fullscreen_warnings', 'max_tab_switch_warnings',
            'multiple_faces_threshold_seconds', 'auto_terminate_on_limit',
            'questions'
        ]


