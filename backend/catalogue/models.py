from django.db import models
from django.conf import settings
from django.utils import timezone


class SourceProvenanceModel(models.Model):
    """
    Abstract model enforcing strict data provenance tracking on all institutional content.
    Strictly forbids fabricated institutional facts.
    """
    SOURCE_TYPES = (
        ('FXEC_OFFICIAL', 'FXEC Official Website / Document'),
        ('FACULTY_CREATED', 'Faculty Created'),
        ('ADMIN_CREATED', 'Authorized Mentor / Admin Input'),
        ('AI_SUGGESTED', 'AI Suggested'),
        ('AI_GENERATED', 'AI Generated'),
        ('YOUTUBE', 'YouTube Educational Video'),
        ('EXTERNAL_REFERENCE', 'External Public Reference'),
        ('NPTEL_OFFICIAL', 'NPTEL Official Public Resource'),
        ('EXTERNAL_PUBLIC', 'External Public Learning Reference'),
    )

    APPROVAL_STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('ARCHIVED', 'Archived'),
    )

    CONTENT_STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PENDING_ADMIN_INPUT', 'Pending Institutional Verification'),
        ('PUBLISHED', 'Published & Verified'),
        ('UNPUBLISHED', 'Unpublished'),
        ('ARCHIVED', 'Archived'),
    )

    source_type = models.CharField(max_length=32, choices=SOURCE_TYPES, default='FXEC_OFFICIAL')
    source_url = models.URLField(blank=True, null=True, help_text="Canonical URL where fact was retrieved")
    source_title = models.CharField(max_length=255, blank=True, null=True, help_text="Authoritative title of webpage/document")
    source_description = models.TextField(blank=True, null=True, help_text="Explanatory context of institutional origin")
    source_accessed_at = models.DateTimeField(blank=True, null=True, help_text="Timestamp when source was accessed")
    last_verified_at = models.DateTimeField(blank=True, null=True, help_text="Timestamp of last provenance verification")
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_created'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_approved'
    )
    approval_status = models.CharField(max_length=32, choices=APPROVAL_STATUS_CHOICES, default='APPROVED')
    content_status = models.CharField(max_length=32, choices=CONTENT_STATUS_CHOICES, default='PUBLISHED')

    class Meta:
        abstract = True


class Department(SourceProvenanceModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class SkillCategory(SourceProvenanceModel):
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Skill Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class SkillDomain(SourceProvenanceModel):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='domains')
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Skill Domains"
        ordering = ['category', 'order', 'name']
        unique_together = ('category', 'name')

    def __str__(self):
        return f"{self.category.name} -> {self.name}"


class Skill(SourceProvenanceModel):
    LEVEL_CHOICES = (
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('EXPERT', 'Expert'),
    )

    SKILL_TYPE_CHOICES = (
        ('CORE', 'Core Skill'),
        ('ELECTIVE', 'Elective Skill'),
        ('FACULTY_INITIATIVE', 'Faculty Initiative'),
        ('EMERGING', 'Emerging / Future Skill'),
        ('PLACEMENT', 'Placement Fit Training'),
        ('TECHNICAL', 'Technical Skill'),
        ('NON_TECHNICAL', 'Non-Technical Skill'),
    )

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True, null=True, blank=True)
    short_description = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='skills')
    domain = models.ForeignKey(SkillDomain, null=True, blank=True, on_delete=models.SET_NULL, related_name='skills')
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='skills')
    departments = models.ManyToManyField(Department, blank=True, related_name='multi_skills')
    is_cross_department = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default='BEGINNER')
    skill_type = models.CharField(max_length=32, choices=SKILL_TYPE_CHOICES, default='CORE')
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependent_skills')
    learning_outcomes = models.JSONField(default=list, blank=True)
    estimated_duration = models.CharField(max_length=64, blank=True, default='4 Weeks')
    status = models.CharField(max_length=32, choices=SourceProvenanceModel.CONTENT_STATUS_CHOICES, default='PUBLISHED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"


class Course(SourceProvenanceModel):
    LEVEL_CHOICES = Skill.LEVEL_CHOICES

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='courses')
    skills = models.ManyToManyField(Skill, blank=True, related_name='multi_courses')
    category = models.ForeignKey(SkillCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='courses')
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='courses')
    departments = models.ManyToManyField(Department, blank=True, related_name='multi_courses')
    instructor_name = models.CharField(max_length=128, default='FXEC Faculty Team')
    description = models.TextField()
    outcomes = models.JSONField(default=list, blank=True)
    learning_objectives = models.JSONField(default=list, blank=True, help_text="Course-level learning objectives")
    thumbnail_url = models.URLField(blank=True, null=True)
    estimated_hours = models.PositiveIntegerField(default=10)
    course_types = models.JSONField(default=list, blank=True, help_text="e.g. ['CORE_SKILL', 'INTERDISCIPLINARY', 'VALUE_ADDED']")
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default='BEGINNER')
    version = models.PositiveIntegerField(default=1)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='follow_up_courses')
    prerequisites_text = models.TextField(blank=True, help_text="AI or faculty defined textual prerequisites")
    target_audience = models.CharField(max_length=255, blank=True, help_text="Target audience for course")
    learning_goal = models.TextField(blank=True, help_text="Primary engineering/career learning goal")
    blueprint = models.JSONField(default=dict, blank=True, help_text="Assessment and curriculum blueprint specification")
    is_published = models.BooleanField(default=True, db_index=True)
    status = models.CharField(max_length=32, choices=SourceProvenanceModel.CONTENT_STATUS_CHOICES, default='PUBLISHED')
    is_demo = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Module(SourceProvenanceModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    topic_tag = models.CharField(max_length=64, db_index=True, help_text="Topic identifier for skill-gap diagnosis mapping")
    duration_minutes = models.PositiveIntegerField(default=30)
    estimated_minutes = models.PositiveIntegerField(default=30)
    learning_objectives = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=True)
    status = models.CharField(max_length=32, default='PUBLISHED')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course', 'order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.title} - Module {self.order}: {self.title}"


class Lesson(SourceProvenanceModel):
    LESSON_TYPES = (
        ('VIDEO', 'Video Lecture'),
        ('PDF', 'PDF / Document Guide'),
        ('TEXT', 'Reading Material / Notes'),
        ('INTERACTIVE', 'Hands-on Practice / Lab Exercise'),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=32, choices=LESSON_TYPES, default='TEXT')
    content_url = models.URLField(blank=True, null=True, help_text="Lawful URL to learning resource")
    text_content = models.TextField(blank=True, help_text="Curated notes, code examples, or guide")
    
    # AI Lesson Content Fields
    learning_objectives = models.JSONField(default=list, blank=True, help_text="Specific learning outcomes for this lesson")
    concept_explanation = models.TextField(blank=True, help_text="Detailed conceptual exposition")
    examples = models.JSONField(default=list, blank=True, help_text="Illustrative code snippets or practical examples")
    common_mistakes = models.JSONField(default=list, blank=True, help_text="Typical beginner pitfalls and resolutions")
    key_points = models.JSONField(default=list, blank=True, help_text="Core takeaways to remember")
    summary = models.TextField(blank=True, help_text="Concise end-of-lesson wrap-up")
    practice_recommendation = models.TextField(blank=True, help_text="Recommended practice exercise or problem")

    duration_minutes = models.PositiveIntegerField(default=15)
    estimated_minutes = models.PositiveIntegerField(default=15)
    is_required = models.BooleanField(default=True)
    requires_video = models.BooleanField(default=False, help_text="Lesson requires watching attached video")
    requires_notes = models.BooleanField(default=False, help_text="Lesson requires reading notes")
    requires_practice = models.BooleanField(default=False, help_text="Lesson requires completing practice")
    status = models.CharField(max_length=32, default='PUBLISHED')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['module', 'order']
        unique_together = ('module', 'order')

    def __str__(self):
        return f"{self.module.title} - Lesson {self.order}: {self.title}"


class VideoResource(SourceProvenanceModel):
    VIDEO_TYPES = (
        ('YOUTUBE', 'YouTube Learning Video'),
        ('EXTERNAL_VIDEO', 'Approved External Educational Video'),
        ('UPLOADED_VIDEO', 'Uploaded Video File'),
        ('AI_GENERATED_VIDEO', 'AI Generated Playable Video'),
        ('AI_VIDEO_SCRIPT', 'AI Video Script & Storyboard Package'),
    )
    AI_VIDEO_STATUS_CHOICES = (
        ('NONE', 'Not Applicable'),
        ('SCRIPT_READY', 'AI Script & Storyboard Ready'),
        ('GENERATING', 'AI Video Rendering In Progress'),
        ('COMPLETED', 'AI Video Generated & Playable'),
        ('FAILED', 'AI Video Generation Failed'),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='videos')
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name='videos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_type = models.CharField(max_length=32, choices=VIDEO_TYPES, default='YOUTUBE')
    video_file = models.FileField(upload_to='videos/', blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True, help_text="Canonical YouTube video URL")
    youtube_video_id = models.CharField(max_length=64, blank=True, null=True, db_index=True, help_text="Extracted 11-char YouTube ID")
    thumbnail = models.URLField(blank=True, null=True)
    thumbnail_url = models.URLField(blank=True, null=True, help_text="Direct link to YouTube video thumbnail")
    channel_name = models.CharField(max_length=128, blank=True, null=True, help_text="Channel or author of the YouTube video")
    duration_if_available = models.CharField(max_length=64, blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(default=300, help_text="Total video runtime in seconds")
    completion_threshold_percent = models.FloatField(default=80.0, help_text="Percentage of video that must be watched for completion")
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    is_unavailable = models.BooleanField(default=False, db_index=True)
    unavailable_reported_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default='PUBLISHED')

    # AI Video Generation Metadata (Mode A & Mode B)
    ai_video_status = models.CharField(max_length=32, choices=AI_VIDEO_STATUS_CHOICES, default='NONE')
    video_provider = models.CharField(max_length=64, blank=True, null=True, help_text="e.g. GEMINI_OMNI, RUNWAY, HEYGEN, NONE")
    generation_id = models.CharField(max_length=128, blank=True, null=True, help_text="Provider task or render ID")
    script_package = models.JSONField(default=dict, blank=True, help_text="Structured script, narration, storyboard scenes, visual cues")
    captions = models.TextField(blank=True, null=True, help_text="Subtitle or caption text in WebVTT / SRT / plain text format")

    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='added_videos')
    added_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f"[{self.video_type}] {self.module.title} - {self.title}"

    @classmethod
    def extract_youtube_id(cls, url: str) -> str:
        """
        Extracts 11-character YouTube video ID from various YouTube URL formats.
        """
        import re
        if not url:
            return ""
        url = url.strip()
        if re.fullmatch(r'[a-zA-Z0-9_-]{11}', url):
            return url
        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube-nocookie\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ""

    def get_embed_url(self) -> str:
        if self.youtube_video_id:
            return f"https://www.youtube-nocookie.com/embed/{self.youtube_video_id}?enablejsapi=1"
        return self.external_url or ""


class StudyMaterial(SourceProvenanceModel):
    RESOURCE_TYPES = (
        ('AI_STUDY_NOTES', 'AI-Generated Structured Study Guide'),
        ('PDF', 'PDF Document / Handbook'),
        ('DOC', 'Word Document'),
        ('PPT', 'Presentation Slides'),
        ('ARTICLE', 'Curated Technical Article'),
        ('NOTES', 'Instructor Lecture Notes'),
        ('CODE_FILE', 'Source Code File / Repository'),
        ('REFERENCE_LINK', 'Authoritative Web Reference'),
        ('PRACTICE_RESOURCE', 'Interactive Lab / Exercise Guide'),
    )
    COMPLETION_METHODS = (
        ('MANUAL_COMPLETE', 'Manual Complete Confirmation'),
        ('OPEN', 'Open Resource'),
        ('PAGE_PROGRESS', 'Page-by-Page Reading Verification'),
        ('QUIZ_AFTER_READING', 'Quiz After Reading'),
    )
    EXPLANATION_LEVEL_CHOICES = (
        ('BEGINNER', 'Beginner Explanation'),
        ('INTERMEDIATE', 'Intermediate Explanation'),
        ('QUICK_REVISION', 'Quick Revision Notes'),
        ('ADVANCED', 'Advanced In-Depth Notes'),
    )
    REVIEW_STATUS_CHOICES = (
        ('PENDING_FACULTY_REVIEW', 'Pending Faculty Review'),
        ('APPROVED', 'Approved by Faculty'),
        ('REVISED', 'Revised by Faculty'),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='materials')
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name='materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=32, choices=RESOURCE_TYPES, default='AI_STUDY_NOTES')
    file = models.FileField(upload_to='materials/', blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    structured_content = models.JSONField(default=dict, blank=True, help_text="Structured 9-11 section educational content")
    text_content = models.TextField(blank=True, help_text="Full rendered markdown study notes")
    completion_method = models.CharField(max_length=32, choices=COMPLETION_METHODS, default='MANUAL_COMPLETE')
    version = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    status = models.CharField(max_length=32, default='PUBLISHED')

    # AI Study Material Versioning & Levels
    explanation_level = models.CharField(max_length=32, choices=EXPLANATION_LEVEL_CHOICES, default='BEGINNER')
    model_provider = models.CharField(max_length=64, default='FXEC AI Engine (Gemini 2.5)')
    review_status = models.CharField(max_length=32, choices=REVIEW_STATUS_CHOICES, default='APPROVED')

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_materials')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_materials')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f"[{self.resource_type}] {self.module.title} - {self.title}"


class PracticeTask(SourceProvenanceModel):
    TASK_TYPES = (
        ('MCQ_PRACTICE', 'Concept Check MCQ Practice'),
        ('CODING_TASK', 'Hands-on Coding Challenge'),
        ('DEBUGGING', 'Code Debugging & Fixing Challenge'),
        ('SHORT_ANSWER', 'Conceptual Short Answer Question'),
        ('FILL_BLANKS', 'Fill-in-the-Blanks Syntax Challenge'),
        ('PROBLEM_SOLVING', 'Algorithmic / Architectural Problem Solving'),
        ('EXERCISE', 'Guided Practical Exercise'),
        ('ASSIGNMENT', 'Module Mini-Assignment'),
    )
    DIFFICULTY_LEVELS = (
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='practice_tasks')
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name='practice_tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=32, choices=TASK_TYPES, default='MCQ_PRACTICE')
    difficulty = models.CharField(max_length=16, choices=DIFFICULTY_LEVELS, default='MEDIUM')
    content = models.JSONField(default=dict, blank=True, help_text="Questions, starter code, test cases, or rubric")
    explanation = models.TextField(blank=True, help_text="Pedagogical explanation shown post-submission")
    pass_score = models.FloatField(default=70.0)
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    status = models.CharField(max_length=32, default='PUBLISHED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f"[{self.task_type}] {self.module.title} - {self.title}"


class LearningResource(SourceProvenanceModel):
    RESOURCE_TYPES = (
        ('VIDEO_LINK', 'Video Lecture (External Link / Embed)'),
        ('DOCUMENT_LINK', 'Reference Document / Syllabus (PDF / Link)'),
        ('INTERACTIVE_LAB', 'Hands-on Practice / Lab Exercise'),
        ('READING_MATERIAL', 'Curated Notes / Study Guide'),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=32, choices=RESOURCE_TYPES, default='VIDEO_LINK')
    content_url = models.URLField(blank=True, null=True, help_text="Lawful URL to external public or institutional material")
    text_content = models.TextField(blank=True, help_text="Explanatory notes or guide")
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class CourseApproval(models.Model):
    ACTION_CHOICES = (
        ('SUBMITTED', 'Submitted for Review'),
        ('APPROVED', 'Approved & Published'),
        ('REJECTED', 'Rejected'),
        ('CHANGES_REQUESTED', 'Changes Requested'),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='approvals')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.title} - {self.action} by {self.reviewer.username}"


class CourseVersion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    snapshot_data = models.JSONField(help_text="Full curriculum snapshot including modules and lessons")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    change_summary = models.TextField(blank=True)

    class Meta:
        ordering = ['course', '-version_number']
        unique_together = ('course', 'version_number')

    def __str__(self):
        return f"{self.course.title} v{self.version_number}"


class AISkillSuggestion(models.Model):
    title = models.CharField(max_length=200)
    category_name = models.CharField(max_length=128)
    domain_name = models.CharField(max_length=128, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    level = models.CharField(max_length=16, choices=Skill.LEVEL_CHOICES, default='BEGINNER')
    skill_type = models.CharField(max_length=32, choices=Skill.SKILL_TYPE_CHOICES, default='EMERGING')
    justification = models.TextField()
    prerequisites = models.JSONField(default=list, blank=True)
    suggested_modules = models.JSONField(default=list, blank=True)
    learning_outcomes = models.JSONField(default=list, blank=True)
    source_type = models.CharField(max_length=32, default='AI_SUGGESTED')
    approval_status = models.CharField(max_length=32, choices=SourceProvenanceModel.APPROVAL_STATUS_CHOICES, default='PENDING_REVIEW')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_ai_suggestions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[AI_SUGGESTED] {self.title} ({self.approval_status})"


class StudentSkillProfile(models.Model):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_profile')
    selected_interests = models.JSONField(default=list, blank=True)
    career_goal = models.CharField(max_length=255, blank=True)
    target_role = models.CharField(max_length=128, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.student.username}"


class SkillRecommendation(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_recommendations')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    reason = models.TextField()
    score = models.FloatField(default=0.0)
    recommended_sequence = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['student', 'recommended_sequence']

    def __str__(self):
        return f"Rec: {self.student.username} -> {self.skill.name}"


class CourseRecommendation(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_recommendations')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    reason = models.TextField()
    score = models.FloatField(default=0.0)
    recommended_sequence = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['student', 'recommended_sequence']

    def __str__(self):
        return f"Rec: {self.student.username} -> {self.course.title}"
