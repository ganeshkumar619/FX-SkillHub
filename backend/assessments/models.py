import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Assessment(models.Model):
    ASSESSMENT_TYPES = (
        ('PRE_ASSESSMENT', 'Diagnostic Pre-Assessment (Skill Gap Analysis)'),
        ('FINAL_ASSESSMENT', 'Final Certification Assessment'),
    )

    course = models.ForeignKey('catalogue.Course', on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=200)
    assessment_type = models.CharField(max_length=32, choices=ASSESSMENT_TYPES, default='FINAL_ASSESSMENT')
    version = models.PositiveIntegerField(default=1, help_text="Immutable assessment version for reproducibility")
    duration_minutes = models.PositiveIntegerField(default=30)
    pass_percentage = models.FloatField(default=70.0)
    max_attempts = models.PositiveIntegerField(default=3)
    randomize_questions = models.BooleanField(default=True)
    randomize_options = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    blueprint = models.JSONField(default=dict, blank=True, help_text="Question count, difficulty, topic distribution blueprint")
    is_ai_generated = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='authored_assessments')

    # Configurable Assessment Security Settings (Part M)
    camera_required = models.BooleanField(default=True, help_text="Requires continuous camera stream")
    screen_share_required = models.BooleanField(default=True, help_text="Requires continuous active screen sharing")
    fullscreen_required = models.BooleanField(default=True, help_text="Requires browser fullscreen enforcement")
    face_detection_enabled = models.BooleanField(default=True, help_text="Enables computer-vision face-count detection")
    max_camera_warnings = models.PositiveIntegerField(default=2, help_text="Maximum allowed camera disconnect warnings before termination")
    max_multiple_face_warnings = models.PositiveIntegerField(default=2, help_text="Maximum allowed multiple-face warnings before termination")
    max_screen_share_warnings = models.PositiveIntegerField(default=2, help_text="Maximum allowed screen-share interruption warnings")
    max_fullscreen_warnings = models.PositiveIntegerField(default=2, help_text="Maximum allowed fullscreen exit warnings")
    max_tab_switch_warnings = models.PositiveIntegerField(default=2, help_text="Maximum allowed tab switch / blur warnings")
    auto_terminate_on_limit = models.BooleanField(default=True, help_text="Automatically terminate attempt when any warning limit is breached")
    multiple_faces_threshold_seconds = models.FloatField(default=2.0, help_text="Debounce threshold seconds for multiple face detection")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['course', '-version']

    def __str__(self):
        return f"{self.title} (v{self.version}) - {self.course.title}"


class Question(models.Model):
    QUESTION_TYPES = (
        ('MCQ_SINGLE', 'Single Choice MCQ'),
        ('MCQ_MULTIPLE', 'Multiple Choice MCQ'),
        ('TRUE_FALSE', 'True / False'),
        ('CODING', 'Programming Coding Question'),
    )
    DIFFICULTY_LEVELS = (
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
    )

    assessment = models.ForeignKey(Assessment, null=True, blank=True, on_delete=models.CASCADE, related_name='questions')
    course = models.ForeignKey('catalogue.Course', null=True, blank=True, on_delete=models.CASCADE, related_name='question_bank')
    text = models.TextField()
    topic_tag = models.CharField(max_length=64, db_index=True, help_text="Corresponds with Module topic_tag for skill-gap diagnosis")
    question_type = models.CharField(max_length=16, choices=QUESTION_TYPES, default='MCQ_SINGLE')
    difficulty = models.CharField(max_length=16, choices=DIFFICULTY_LEVELS, default='EASY')
    marks = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True, help_text="Pedagogical explanation shown post-submission")
    order = models.PositiveIntegerField(default=1)

    # Coding Problem Specific Fields
    title = models.CharField(max_length=255, blank=True, default='')
    problem_statement = models.TextField(blank=True, default='')
    programming_language = models.CharField(
        max_length=16, 
        blank=True, 
        default='', 
        choices=[('c', 'C'), ('cpp', 'C++'), ('java', 'Java'), ('python', 'Python')],
        help_text="Required programming language for this coding problem"
    )
    input_format = models.TextField(blank=True, default='')
    output_format = models.TextField(blank=True, default='')
    constraints = models.TextField(blank=True, default='')
    sample_test_cases = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Exactly 2 visible test cases: [{'input': '...', 'output': '...'}]"
    )
    hidden_test_cases = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Exactly 4 hidden test cases: [{'input': '...', 'output': '...'}]"
    )
    reference_solution = models.TextField(
        blank=True, 
        default='', 
        help_text="Trusted reference solution for automated validation"
    )
    approval_status = models.CharField(
        max_length=32,
        default='APPROVED',
        choices=[('DRAFT', 'Draft'), ('PENDING_REVIEW', 'Pending Review'), ('APPROVED', 'Approved')],
        db_index=True
    )

    # AI Quality Control & Bank Status
    is_bank_question = models.BooleanField(default=False, db_index=True, help_text="Member of the Course AI Question Bank pool")
    semantic_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True, help_text="Normalized token hash for duplicate detection")
    quality_score = models.FloatField(default=1.0, help_text="AI quality assurance score (0.0 - 1.0)")
    status = models.CharField(
        max_length=32,
        default='ACTIVE',
        choices=[('ACTIVE', 'Active'), ('QUESTION_REQUIRES_REVIEW', 'Requires Review')],
        db_index=True,
        help_text="Integrity status of question content and answer key"
    )

    class Meta:
        ordering = ['assessment', 'order']

    def __str__(self):
        return f"[{self.topic_tag}] {self.text[:50]}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['question', 'order']

    def __str__(self):
        return f"{self.text} ({'Correct' if self.is_correct else 'Incorrect'})"


class AssessmentAttempt(models.Model):
    STATUS_CHOICES = (
        ('READY', 'Ready to Begin'),
        ('IN_PROGRESS', 'In Progress'),
        ('WARNING', 'Security Warning Active'),
        ('SUBMITTED', 'Submitted by Student'),
        ('EXPIRED', 'Expired (Auto-submitted by Server)'),
        ('EVALUATED', 'Evaluated'),
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
        ('TERMINATED_SECURITY_VIOLATION', 'Terminated Due to Critical Security Violation'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assessment_attempts')
    enrollment = models.ForeignKey('learning.Enrollment', null=True, blank=True, on_delete=models.SET_NULL, related_name='attempts')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='READY')
    started_at = models.DateTimeField(default=timezone.now)
    server_deadline = models.DateTimeField(help_text="Server-enforced deadline beyond which submissions are auto-closed")
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0.0)
    percentage = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)
    topic_breakdown = models.JSONField(default=dict, blank=True, help_text="Diagnostic topic percentage scores for skill gaps")

    # Multi-Layer Proctoring Security Counters (Server Authoritative)
    camera_warning_count = models.PositiveIntegerField(default=0)
    multiple_face_warning_count = models.PositiveIntegerField(default=0)
    screen_share_warning_count = models.PositiveIntegerField(default=0)
    fullscreen_warning_count = models.PositiveIntegerField(default=0)
    tab_switch_warning_count = models.PositiveIntegerField(default=0)

    # Dynamic Question Bank Sampling & Option Randomization
    selected_question_ids = models.JSONField(default=list, blank=True, help_text="Specific Question IDs chosen from the pool for this attempt")
    question_option_orders = models.JSONField(default=dict, blank=True, help_text="Mapping of question_id -> randomized option_ids order")

    # Faculty Review Flag
    review_status = models.CharField(
        max_length=16,
        choices=(('CLEAN', 'Clean'), ('WARNING', 'Warning Flagged'), ('INVALID', 'Invalidated')),
        default='CLEAN'
    )
    termination_reason = models.TextField(blank=True, null=True, help_text="Reason recorded if auto-terminated by AssessmentSecurityEngine")
    terminated_at = models.DateTimeField(null=True, blank=True)

    is_demo = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-started_at']

    def is_expired(self):
        return timezone.now() > self.server_deadline

    def evaluate(self):
        """
        Authoritative server evaluation logic:
        1. Evaluates each question based on stable Option IDs (never frontend order or display position).
        2. Compares selected Option IDs against authoritatively marked is_correct Options.
        3. Supports single-choice (MCQ_SINGLE, TRUE_FALSE) and multi-choice (MCQ_MULTIPLE).
        4. Computes total marks, percentage, pass/fail status, and topic-level mastery.
        """
        total_possible = 0
        total_earned = 0.0
        topic_stats = {} # topic -> {earned, total}

        if self.selected_question_ids:
            questions_qs = Question.objects.filter(id__in=self.selected_question_ids).prefetch_related('options')
            q_map = {q.id: q for q in questions_qs}
            questions = [q_map[qid] for qid in self.selected_question_ids if qid in q_map]
        else:
            questions = list(self.assessment.questions.prefetch_related('options').all())

        for question in questions:
            q_marks = question.marks
            total_possible += q_marks
            tag = question.topic_tag or 'general'
            if tag not in topic_stats:
                topic_stats[tag] = {'earned': 0.0, 'total': 0}
            topic_stats[tag]['total'] += q_marks

            ans = self.answers.filter(question=question).first()
            if ans:
                if question.question_type == 'CODING':
                    # Proportional scoring based on server-evaluated test cases
                    if ans.total_test_cases > 0:
                        ratio = ans.test_cases_passed / float(ans.total_test_cases)
                        earned_for_q = round(ratio * q_marks, 1)
                        ans.marks_obtained = earned_for_q
                        ans.is_correct = (ans.test_cases_passed == ans.total_test_cases)
                        total_earned += earned_for_q
                        topic_stats[tag]['earned'] += earned_for_q
                    else:
                        ans.is_correct = False
                        ans.marks_obtained = 0.0
                    ans.save(update_fields=['is_correct', 'marks_obtained'])
                else:
                    correct_option_ids = set(question.options.filter(is_correct=True).values_list('id', flat=True))
                    selected_option_ids = set(ans.selected_options.values_list('id', flat=True))
                    
                    if question.question_type == 'MCQ_MULTIPLE':
                        is_corr = bool(selected_option_ids and correct_option_ids == selected_option_ids)
                    else:
                        # Single-choice MCQ & True/False: exactly one option selected matches exactly one correct option
                        is_corr = bool(
                            len(selected_option_ids) == 1 and
                            len(correct_option_ids) == 1 and
                            list(selected_option_ids)[0] == list(correct_option_ids)[0]
                        )

                    if is_corr:
                        ans.is_correct = True
                        ans.marks_obtained = float(q_marks)
                        total_earned += q_marks
                        topic_stats[tag]['earned'] += q_marks
                    else:
                        ans.is_correct = False
                        ans.marks_obtained = 0.0
                    ans.save(update_fields=['is_correct', 'marks_obtained'])

        self.score = round(total_earned, 1)
        self.percentage = round((total_earned / total_possible * 100.0) if total_possible > 0 else 0.0, 1)
        self.passed = self.percentage >= self.assessment.pass_percentage
        
        # Calculate topic breakdown percentages
        breakdown = {}
        for tag, data in topic_stats.items():
            breakdown[tag] = round((data['earned'] / data['total'] * 100.0) if data['total'] > 0 else 0.0, 1)
        self.topic_breakdown = breakdown
        self.status = 'EVALUATED'
        self.save(update_fields=['score', 'percentage', 'passed', 'topic_breakdown', 'status'])
        return self

    def __str__(self):
        return f"{self.student.username} - {self.assessment.title} ({self.status}: {self.percentage}%)"


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_options = models.ManyToManyField(QuestionOption, blank=True)
    is_correct = models.BooleanField(default=False)
    marks_obtained = models.FloatField(default=0.0)
    answered_at = models.DateTimeField(auto_now=True)

    # Coding Problem Specific Submission Details
    submitted_code = models.TextField(blank=True, default='')
    code_language = models.CharField(max_length=16, blank=True, default='')
    test_cases_passed = models.PositiveSmallIntegerField(default=0)
    total_test_cases = models.PositiveSmallIntegerField(default=0)
    code_execution_details = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"Answer to {self.question.id} for attempt {self.attempt.id}"
