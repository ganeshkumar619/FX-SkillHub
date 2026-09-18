import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalogue.models import (
    Department,
    SkillCategory,
    SkillDomain,
    Skill,
    Course,
    Module,
    VideoResource,
    StudyMaterial,
    PracticeTask
)
from catalogue.youtube_service import YouTubeService
from catalogue.ai_study_material_service import AIStudyMaterialService
from learning.models import (
    Enrollment,
    ModuleProgress,
    VideoProgress,
    MaterialProgress,
    PracticeProgress,
    ReportedVideoIssue
)
from assessments.models import Assessment
from authentication.authentication import generate_jwt_token

User = get_user_model()


@pytest.mark.django_db
class TestYouTubeAndAIStudyMaterial:
    """
    Automated test suite verifying YouTube Video Integration & AI Study Material:
    1. YouTube URL extraction, sanitization, and oEmbed verification
    2. Zero local media downloading; provenance tracking (YOUTUBE & AI_GENERATED)
    3. 9-section structured AI study notes DB persistence
    4. Video start tracking and reliable manual fallback completion
    5. Broken/unavailable video reporting and admin resolution queue
    6. Assessment lock / unlock integrity chain
    """

    def setup_method(self):
        self.client = APIClient()

        # Faculty / Mentor User
        self.mentor = User.objects.create_user(
            username='faculty_py',
            email='faculty@fxec.ac.in',
            password='Password123!',
            role='MENTOR'
        )
        self.mentor_token = generate_jwt_token(self.mentor)

        # Admin User
        self.admin = User.objects.create_user(
            username='admin_academic',
            email='admin@fxec.ac.in',
            password='Password123!',
            role='ADMIN',
            is_staff=True
        )
        self.admin_token = generate_jwt_token(self.admin)

        # Student User
        self.student = User.objects.create_user(
            username='student_raj',
            email='raj@fxec.ac.in',
            password='Password123!',
            role='STUDENT'
        )
        self.student_token = generate_jwt_token(self.student)

        # Catalogue Hierarchy
        self.dept = Department.objects.create(
            code='CSE',
            name='Computer Science and Engineering',
            source_type='FXEC_OFFICIAL'
        )
        self.category = SkillCategory.objects.create(
            name='Software Engineering & Systems',
            source_type='FXEC_OFFICIAL'
        )
        self.domain = SkillDomain.objects.create(
            category=self.category,
            name='Programming Languages & Runtime Engines',
            order=1
        )
        self.skill = Skill.objects.create(
            name='Python Core',
            category=self.category,
            domain=self.domain,
            department=self.dept,
            level='BEGINNER',
            skill_type='CORE',
            source_type='FXEC_OFFICIAL',
            approval_status='APPROVED'
        )
        self.course = Course.objects.create(
            title='Python Fundamentals for Software Engineers',
            slug='python-fundamentals-se',
            skill=self.skill,
            department=self.dept,
            is_published=True,
            created_by=self.mentor,
            source_type='FACULTY_CURATED'
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Introduction to Python Architecture',
            order=1,
            duration_minutes=45,
            is_required=True,
            status='PUBLISHED'
        )

    # -------------------------------------------------------------------------
    # 1. YouTube Service Extraction & Sanitization Tests
    # -------------------------------------------------------------------------

    def test_youtube_service_extraction_and_sanitization(self):
        """
        Verify that standard, share, embed, and nocookie URLs properly extract 11-char IDs,
        while non-YouTube or malicious URLs are safely rejected.
        """
        # Standard watch URL
        assert YouTubeService.extract_video_id('https://www.youtube.com/watch?v=rfscVS0vtbw') == 'rfscVS0vtbw'
        # Short share URL
        assert YouTubeService.extract_video_id('https://youtu.be/k9TUPpGqYTo') == 'k9TUPpGqYTo'
        # Embed URL
        assert YouTubeService.extract_video_id('https://www.youtube.com/embed/DZwmZ8Usvnk') == 'DZwmZ8Usvnk'
        # Nocookie URL with query string
        assert YouTubeService.extract_video_id('https://www.youtube-nocookie.com/embed/6iF8Xb7Z3wQ?rel=0&t=20') == '6iF8Xb7Z3wQ'
        
        # Privacy-enhanced embed URL generator
        embed_url = YouTubeService.get_privacy_embed_url('rfscVS0vtbw')
        assert 'youtube-nocookie.com/embed/rfscVS0vtbw' in embed_url
        assert 'enablejsapi=1' in embed_url

        # Malicious / non-YouTube URLs rejected
        assert YouTubeService.extract_video_id('https://evil-phishing.com/watch?v=rfscVS0vtbw') is None
        assert YouTubeService.extract_video_id('javascript:alert(1)') is None
        assert YouTubeService.extract_video_id('https://vimeo.com/12345678') is None

    # -------------------------------------------------------------------------
    # 2. YouTube Metadata Parsing API
    # -------------------------------------------------------------------------

    def test_youtube_parse_endpoint(self):
        """
        Verify the POST /api/catalogue/videos/parse/ endpoint.
        """
        # Valid YouTube URL
        resp = self.client.post(
            '/api/catalogue/videos/parse/',
            {'url': 'https://www.youtube.com/watch?v=rfscVS0vtbw'},
            format='json'
        )
        assert resp.status_code == 200
        assert resp.data['valid'] is True
        assert resp.data['video_id'] == 'rfscVS0vtbw'
        assert 'youtube-nocookie.com/embed/rfscVS0vtbw' in resp.data['embed_url']

        # Invalid URL
        resp_invalid = self.client.post(
            '/api/catalogue/videos/parse/',
            {'url': 'https://notyoutube.com/watch?v=123'},
            format='json'
        )
        assert resp_invalid.status_code == 400
        assert resp_invalid.data['valid'] is False

    # -------------------------------------------------------------------------
    # 3. 9-Section Structured AI Study Material & Provenance Verification
    # -------------------------------------------------------------------------

    def test_ai_study_material_9_sections_and_provenance(self):
        """
        Verify generation of 9-section structured AI study notes, verified YouTube video
        attachment, and strict provenance labeling.
        """
        result = AIStudyMaterialService.generate_and_save_module_content(self.module, user=self.mentor)
        assert result['status'] == 'SUCCESS'

        material = StudyMaterial.objects.get(id=result['study_material_id'])
        video = VideoResource.objects.get(id=result['video_id'])
        practice = PracticeTask.objects.get(id=result['practice_id'])

        # Provenance attribution checks
        assert material.source_type == 'AI_GENERATED'
        assert material.resource_type == 'AI_STUDY_NOTES'
        assert material.source_type != 'FXEC_OFFICIAL'
        assert material.reviewed_by == self.mentor

        assert video.source_type == 'YOUTUBE'
        assert video.source_type != 'FXEC_OFFICIAL'
        assert video.youtube_video_id is not None
        assert len(video.youtube_video_id) == 11
        assert video.channel_name is not None
        assert 'youtube-nocookie.com/embed' in video.get_embed_url()

        # Verify all 9 sections exist in structured_content
        sc = material.structured_content
        assert isinstance(sc, dict)
        assert 'introduction' in sc and len(sc['introduction']) > 20
        assert 'concept_explanation' in sc and len(sc['concept_explanation']) > 20
        assert 'key_points' in sc and isinstance(sc['key_points'], list) and len(sc['key_points']) >= 3
        assert 'syntax' in sc and len(sc['syntax']) > 5
        assert 'examples' in sc and isinstance(sc['examples'], list) and len(sc['examples']) >= 1
        assert 'common_mistakes' in sc and isinstance(sc['common_mistakes'], list) and len(sc['common_mistakes']) >= 1
        assert 'important_terms' in sc and isinstance(sc['important_terms'], list) and len(sc['important_terms']) >= 1
        assert 'quick_revision' in sc and isinstance(sc['quick_revision'], list) and len(sc['quick_revision']) >= 2
        assert 'practice_questions' in sc and isinstance(sc['practice_questions'], list) and len(sc['practice_questions']) >= 1

        # Check practice task alignment
        assert practice.source_type == 'AI_GENERATED'
        assert practice.task_type == 'MCQ_PRACTICE'
        assert len(practice.content['questions']) >= 1

    # -------------------------------------------------------------------------
    # 4. Video Playback Start & Authoritative Manual Confirmation
    # -------------------------------------------------------------------------

    def test_video_start_and_fallback_confirm_complete(self):
        """
        Verify student starting a video lecture records playback initialization,
        and fallback manual confirmation records completion with completion_mode='VIDEO_STARTED_MANUAL'.
        """
        res = AIStudyMaterialService.generate_and_save_module_content(self.module, user=self.mentor)
        video = VideoResource.objects.get(id=res['video_id'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')

        # 1. Register video playback start
        resp_start = self.client.post(f'/api/learning/video/{video.id}/start/')
        assert resp_start.status_code == 200
        assert resp_start.data['started'] is True
        assert resp_start.data['video_id'] == video.id

        vp = VideoProgress.objects.get(enrollment__student=self.student, video=video)
        assert vp.started_at is not None
        assert vp.is_completed is False

        # 2. Confirm video watched via fallback
        resp_confirm = self.client.post(f'/api/learning/video/{video.id}/confirm-complete/')
        assert resp_confirm.status_code == 200
        assert resp_confirm.data['is_completed'] is True
        assert resp_confirm.data['completion_mode'] == 'VIDEO_STARTED_MANUAL'

        vp.refresh_from_db()
        assert vp.is_completed is True
        assert vp.completion_mode == 'VIDEO_STARTED_MANUAL'
        assert vp.completed_at is not None

    # -------------------------------------------------------------------------
    # 5. Broken/Unavailable Video Reporting & Admin Replacement
    # -------------------------------------------------------------------------

    def test_video_unavailable_reporting_and_admin_replacement(self):
        """
        Verify student can report broken/unavailable videos and admin can resolve
        the issue with a replacement YouTube URL.
        """
        res = AIStudyMaterialService.generate_and_save_module_content(self.module, user=self.mentor)
        video = VideoResource.objects.get(id=res['video_id'])

        # 1. Student reports broken video
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        resp_report = self.client.post(
            f'/api/learning/video/{video.id}/report-unavailable/',
            {
                'issue_type': 'EMBEDDING_DISABLED',
                'notes': 'Video playback disabled by owner on external sites.'
            },
            format='json'
        )
        assert resp_report.status_code == 201
        issue_id = resp_report.data['issue_id']

        video.refresh_from_db()
        assert video.unavailable_reported_count == 1
        issue = ReportedVideoIssue.objects.get(id=issue_id)
        assert issue.status == 'OPEN'
        assert issue.issue_type == 'EMBEDDING_DISABLED'

        # 2. Admin inspects reported videos queue
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        resp_queue = self.client.get('/api/catalogue/admin/reported-videos/?status=OPEN')
        assert resp_queue.status_code == 200
        assert any(i['id'] == issue_id for i in resp_queue.data)

        # 3. Admin resolves with replacement YouTube URL
        replacement_url = 'https://www.youtube.com/watch?v=k9TUPpGqYTo'
        resp_resolve = self.client.post(
            f'/api/catalogue/admin/reported-videos/{issue_id}/resolve/',
            {
                'action': 'RESOLVE',
                'replacement_youtube_url': replacement_url
            },
            format='json'
        )
        assert resp_resolve.status_code == 200
        assert resp_resolve.data['issue']['status'] == 'RESOLVED'

        video.refresh_from_db()
        assert video.youtube_video_id == 'k9TUPpGqYTo'
        assert video.is_unavailable is False
        assert video.unavailable_reported_count == 0

    # -------------------------------------------------------------------------
    # 6. Complete Learning Journey & Assessment Lock Verification
    # -------------------------------------------------------------------------

    def test_complete_learning_journey_unlocks_assessment(self):
        """
        Verify that the final certification assessment is strictly locked
        until the student completes the YouTube lecture, AI study notes, and concept practice.
        """
        res = AIStudyMaterialService.generate_and_save_module_content(self.module, user=self.mentor)
        video = VideoResource.objects.get(id=res['video_id'])
        material = StudyMaterial.objects.get(id=res['study_material_id'])
        practice = PracticeTask.objects.get(id=res['practice_id'])

        # Create Final Assessment
        assessment = Assessment.objects.create(
            title='Python Fundamentals Certification Assessment',
            course=self.course,
            pass_percentage=70.0,
            duration_minutes=60,
            is_published=True
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')

        # Initial check: Assessment is strictly LOCKED
        elig_res = self.client.get(f'/api/courses/{self.course.id}/assessment-eligibility/')
        assert elig_res.status_code == 200
        assert elig_res.data['eligible'] is False
        assert elig_res.data['can_start'] is False

        # Step A: Watch Video
        self.client.post(f'/api/learning/video/{video.id}/start/')
        self.client.post(f'/api/learning/video/{video.id}/confirm-complete/')

        # Step B: Read & Complete AI Study Material
        mat_res = self.client.post('/api/learning/material/complete/', {'material_id': material.id})
        assert mat_res.status_code == 200

        # Intermediate check: Still locked (Practice not yet completed)
        elig_mid = self.client.get(f'/api/courses/{self.course.id}/assessment-eligibility/')
        assert elig_mid.data['eligible'] is False

        # Step C: Submit Practice Quiz
        q_id = practice.content['questions'][0]['id']
        correct_ans = practice.content['questions'][0]['correct_option']
        prac_res = self.client.post(
            '/api/learning/practice/submit/',
            {
                'practice_id': practice.id,
                'answers': {str(q_id): correct_ans}
            },
            format='json'
        )
        assert prac_res.status_code == 200
        assert prac_res.data['is_completed'] is True
        assert prac_res.data['module_completed'] is True

        # Final check: Module complete -> Assessment UNLOCKED!
        elig_final = self.client.get(f'/api/courses/{self.course.id}/assessment-eligibility/')
        assert elig_final.status_code == 200
        assert elig_final.data['eligible'] is True
        assert elig_final.data['can_start'] is True
        assert elig_final.data['completed_modules'] == 1
        assert elig_final.data['total_required_modules'] == 1
