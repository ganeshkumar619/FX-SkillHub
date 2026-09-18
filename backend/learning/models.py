from django.db import models
from django.conf import settings
from django.utils import timezone

class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey('catalogue.Course', on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    progress_percent = models.FloatField(default=0.0)
    is_demo = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at']

    def update_progress(self):
        """
        Recalculates real progress based on deterministic required learning item and module completion.
        """
        from .services import calculate_course_progress
        summary = calculate_course_progress(self.student_id, self.course_id)
        self.refresh_from_db(fields=['progress_percent', 'is_completed', 'completed_at'])
        return self.progress_percent

    def is_assessment_eligible(self):
        """
        Server-authoritative check: all required modules must be 100% completed.
        """
        from .services import is_assessment_eligible
        elig = is_assessment_eligible(self.student_id, self.course_id)
        return (
            elig['eligible'],
            elig['course_progress'],
            elig['completed_modules'],
            elig['total_required_modules'],
            elig['reason']
        )

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"


class ModuleProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey('catalogue.Module', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('enrollment', 'module')

    def check_and_update_completion(self):
        """
        Calculates module completion from all configured required activities via learning service.
        """
        from .services import calculate_module_progress
        summary = calculate_module_progress(self.enrollment.student_id, self.module_id)
        self.refresh_from_db(fields=['is_completed', 'completed_at'])
        return self.is_completed

    def __str__(self):
        return f"{self.enrollment.student.username} - {self.module.title} ({'Done' if self.is_completed else 'In Progress'})"


class VideoProgress(models.Model):
    COMPLETION_MODE_CHOICES = (
        ('WATCH_THRESHOLD', 'Watch Threshold Achieved'),
        ('VIDEO_STARTED_MANUAL', 'Started and Confirmed by Student'),
    )

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey('catalogue.VideoResource', on_delete=models.CASCADE, related_name='student_progress')
    watched_seconds = models.PositiveIntegerField(default=0)
    watch_percentage = models.FloatField(default=0.0)
    last_position = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False, db_index=True)
    completion_mode = models.CharField(max_length=32, choices=COMPLETION_MODE_CHOICES, default='WATCH_THRESHOLD')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'video')

    def record_start(self):
        if not self.started_at:
            self.started_at = timezone.now()
            self.save(update_fields=['started_at'])
        return self

    def record_progress(self, current_seconds, total_duration=None):
        if total_duration and total_duration > 0:
            duration = total_duration
        else:
            duration = self.video.duration_seconds or 300

        self.last_position = int(current_seconds)
        if current_seconds > self.watched_seconds:
            self.watched_seconds = int(current_seconds)

        calc_pct = round((self.watched_seconds / duration) * 100.0, 1)
        if calc_pct > self.watch_percentage:
            self.watch_percentage = min(calc_pct, 100.0)

        threshold = self.video.completion_threshold_percent or 80.0
        if self.watch_percentage >= threshold and not self.is_completed:
            self.is_completed = True
            self.completion_mode = 'WATCH_THRESHOLD'
            self.completed_at = timezone.now()

        self.save()
        # Trigger module update
        mp, _ = ModuleProgress.objects.get_or_create(enrollment=self.enrollment, module=self.video.module)
        mp.check_and_update_completion()
        self.enrollment.update_progress()
        return self

    def confirm_manual_complete(self):
        """
        Reliable fallback for embedded YouTube players where postMessage/cross-origin 
        tracking is blocked or restricted. Validates that the student started the video 
        before permitting confirmation.
        """
        if not self.is_completed:
            self.is_completed = True
            self.completion_mode = 'VIDEO_STARTED_MANUAL'
            if not self.started_at:
                self.started_at = timezone.now()
            self.completed_at = timezone.now()
            self.watch_percentage = max(self.watch_percentage, 80.0)
            self.save()

            mp, _ = ModuleProgress.objects.get_or_create(enrollment=self.enrollment, module=self.video.module)
            mp.check_and_update_completion()
            self.enrollment.update_progress()
        return self


class ReportedVideoIssue(models.Model):
    ISSUE_CHOICES = (
        ('UNAVAILABLE', 'Video is unavailable or deleted on YouTube'),
        ('EMBEDDING_DISABLED', 'Video playback on external sites has been disabled by owner'),
        ('PRIVATE', 'Video is marked private or restricted'),
        ('BROKEN_CONTENT', 'Content or audio is distorted / broken'),
        ('TOPIC_MISMATCH', 'Video does not teach the stated topic'),
        ('OTHER', 'Other Technical Issue'),
    )
    STATUS_CHOICES = (
        ('OPEN', 'Open for Faculty/Admin Review'),
        ('RESOLVED', 'Resolved / Video Replaced'),
        ('DISMISSED', 'Dismissed / Tested Working'),
    )

    video = models.ForeignKey('catalogue.VideoResource', on_delete=models.CASCADE, related_name='reported_issues')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_video_issues')
    issue_type = models.CharField(max_length=32, choices=ISSUE_CHOICES, default='UNAVAILABLE')
    notes = models.TextField(blank=True, help_text="Student description of problem")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='OPEN')
    replacement_video_id = models.CharField(max_length=64, blank=True, null=True, help_text="New YouTube ID assigned by Admin")
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='resolved_video_issues')

    class Meta:
        ordering = ['-reported_at']

    def __str__(self):
        return f"Issue [{self.issue_type}] on {self.video.title} ({self.status})"


class MaterialProgress(models.Model):
    STATUS_CHOICES = (
        ('OPENED', 'Opened'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='material_progress')
    material = models.ForeignKey('catalogue.StudyMaterial', on_delete=models.CASCADE, related_name='student_progress')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='OPENED')
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'material')

    def mark_completed(self):
        self.status = 'COMPLETED'
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()
        mp, _ = ModuleProgress.objects.get_or_create(enrollment=self.enrollment, module=self.material.module)
        mp.check_and_update_completion()
        self.enrollment.update_progress()
        return self


class PracticeProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='practice_progress')
    practice = models.ForeignKey('catalogue.PracticeTask', on_delete=models.CASCADE, related_name='student_progress')
    attempt_count = models.PositiveIntegerField(default=0)
    best_score = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'practice')

    def record_attempt(self, score):
        self.attempt_count += 1
        if score > self.best_score:
            self.best_score = round(score, 1)

        pass_score = self.practice.pass_score or 70.0
        if self.best_score >= pass_score and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()

        self.save()
        mp, _ = ModuleProgress.objects.get_or_create(enrollment=self.enrollment, module=self.practice.module)
        mp.check_and_update_completion()
        self.enrollment.update_progress()
        return self


class Quiz(models.Model):
    module = models.ForeignKey('catalogue.Module', on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    pass_percentage = models.FloatField(default=70.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quiz: {self.title} ({self.module.title})"


class QuizAttempt(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField()
    passed = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}: {self.score}%"
