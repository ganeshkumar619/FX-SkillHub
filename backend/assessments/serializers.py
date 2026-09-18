from rest_framework import serializers
from .models import Assessment, Question, QuestionOption, AssessmentAttempt, StudentAnswer
from proctoring.models import RiskScore

class QuestionOptionSafeSerializer(serializers.ModelSerializer):
    """Safe option serializer for students during examination — strips correct answer flag."""
    class Meta:
        model = QuestionOption
        fields = ['id', 'text', 'order']

class QuestionSafeSerializer(serializers.ModelSerializer):
    """Safe question serializer for students — strips correct answer and explanation."""
    options = QuestionOptionSafeSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'topic_tag', 'question_type', 'difficulty', 'marks', 'order', 'options']

class AssessmentBriefSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'id', 'title', 'assessment_type', 'version',
            'duration_minutes', 'pass_percentage', 'max_attempts',
            'questions_count',
            'camera_required', 'screen_share_required', 'fullscreen_required',
            'face_detection_enabled', 'max_camera_warnings', 'max_multiple_face_warnings',
            'max_screen_share_warnings', 'max_fullscreen_warnings', 'max_tab_switch_warnings',
            'multiple_faces_threshold_seconds', 'auto_terminate_on_limit'
        ]

class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ['question', 'selected_options', 'answered_at']

class AssessmentAttemptDetailSerializer(serializers.ModelSerializer):
    assessment = AssessmentBriefSerializer(read_only=True)
    questions = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentAttempt
        fields = [
            'id', 'assessment', 'status', 'started_at',
            'server_deadline', 'score', 'percentage', 'passed',
            'review_status', 'questions', 'answers',
            'camera_warning_count', 'multiple_face_warning_count',
            'screen_share_warning_count', 'fullscreen_warning_count',
            'tab_switch_warning_count', 'termination_reason', 'terminated_at'
        ]

    def get_questions(self, obj):
        if obj.selected_question_ids:
            questions_qs = Question.objects.filter(id__in=obj.selected_question_ids).prefetch_related('options')
            q_map = {q.id: q for q in questions_qs}
            ordered_questions = [q_map[qid] for qid in obj.selected_question_ids if qid in q_map]
        else:
            ordered_questions = list(obj.assessment.questions.prefetch_related('options').all())

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
        fields = ['id', 'text', 'topic_tag', 'question_type', 'difficulty', 'marks', 'explanation', 'order', 'options', 'status', 'is_bank_question']


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


