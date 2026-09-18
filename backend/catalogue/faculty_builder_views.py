import re
import logging
from typing import Dict, Any, List
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (
    Course,
    Module,
    Lesson,
    VideoResource,
    StudyMaterial,
    PracticeTask,
    Skill,
    SkillCategory,
    Department,
    CourseApproval
)
from .serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    ModuleSerializer,
    LessonSerializer,
    VideoResourceSerializer,
    StudyMaterialSerializer,
    PracticeTaskSerializer
)
from .youtube_service import YouTubeService
from .ai_course_builder_service import AICourseBuilderService
from learning.services import calculate_course_progress
from assessments.models import Assessment, Question, QuestionOption
from assessments.serializers import AssessmentAdminSerializer, QuestionAdminSerializer

logger = logging.getLogger(__name__)


class IsMentorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.role in ['FACULTY', 'MENTOR', 'ADMIN'] or request.user.is_superuser)
        )


class IsAdminOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.role == 'ADMIN' or request.user.is_superuser)
        )


# =====================================================================
# 1. Course Management (Create, List, Detail, Update, Delete)
# =====================================================================

class FacultyCourseCreateOrUpdateView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def get(self, request, pk=None):
        if pk:
            course = Course.objects.filter(id=pk).prefetch_related(
                'modules__lessons__videos',
                'modules__lessons__materials',
                'modules__lessons__practice_tasks',
                'modules__videos',
                'modules__materials',
                'modules__practice_tasks',
                'departments'
            ).first()
            if not course:
                return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
            if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
                return Response({'error': 'Unauthorized to access this course'}, status=status.HTTP_403_FORBIDDEN)
            return Response(CourseDetailSerializer(course).data)

        # List courses created by this faculty (or all for admin)
        qs = Course.objects.all().select_related('skill', 'department', 'created_by')
        if request.user.role != 'ADMIN' and not request.user.is_superuser:
            qs = qs.filter(created_by=request.user)
        qs = qs.order_by('-created_at')
        return Response(CourseListSerializer(qs, many=True).data)

    def post(self, request):
        data = request.data
        title = data.get('title', '').strip()
        if not title:
            return Response({'error': 'Course title is required'}, status=status.HTTP_400_BAD_REQUEST)

        skill_id = data.get('skill_id')
        if not skill_id:
            return Response({'error': 'skill_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        skill = Skill.objects.filter(id=skill_id).first()
        if not skill:
            return Response({'error': 'Selected skill does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        category = None
        if data.get('category_id'):
            category = SkillCategory.objects.filter(id=data['category_id']).first()
        if not category and skill.category:
            category = skill.category

        department = None
        if data.get('department_id'):
            department = Department.objects.filter(id=data['department_id']).first()
        elif skill.department:
            department = skill.department

        # Generate unique slug
        base_slug = slugify(title) or 'course'
        slug = base_slug
        counter = 1
        while Course.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        instructor_name = data.get('instructor_name') or (
            f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        )

        outcomes = data.get('learning_objectives') or data.get('outcomes') or []
        if isinstance(outcomes, str):
            outcomes = [o.strip() for o in outcomes.split('\n') if o.strip()]

        course = Course.objects.create(
            title=title,
            slug=slug,
            skill=skill,
            category=category,
            department=department,
            instructor_name=instructor_name,
            description=data.get('description', '').strip(),
            outcomes=outcomes,
            learning_objectives=outcomes,
            prerequisites_text=data.get('prerequisites_text', '').strip(),
            thumbnail_url=data.get('thumbnail_url', '').strip() or None,
            estimated_hours=int(data.get('estimated_hours') or 10),
            course_types=data.get('course_types') or ['FACULTY_INITIATIVE'],
            level=data.get('level') or skill.level or 'BEGINNER',
            version=1,
            is_published=False,
            approval_status='DRAFT',
            content_status='DRAFT',
            source_type='FACULTY_CREATED',
            source_title=f"Faculty Curriculum: {title}",
            source_url=data.get('source_url', ''),
            created_by=request.user
        )

        # Department mappings
        dept_ids = data.get('department_ids', [])
        if dept_ids:
            course.departments.set(Department.objects.filter(id__in=dept_ids))

        return Response(CourseDetailSerializer(course).data, status=status.HTTP_201_CREATED)

    def put(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this course'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        if 'title' in data:
            course.title = data['title'].strip()
        if 'description' in data:
            course.description = data['description'].strip()
        if 'level' in data:
            course.level = data['level']
        if 'estimated_hours' in data:
            course.estimated_hours = int(data['estimated_hours'])
        if 'thumbnail_url' in data:
            course.thumbnail_url = data['thumbnail_url'].strip() or None
        if 'prerequisites_text' in data:
            course.prerequisites_text = data['prerequisites_text'].strip()
        if 'course_types' in data:
            course.course_types = data['course_types']
        if 'learning_objectives' in data or 'outcomes' in data:
            objs = data.get('learning_objectives') or data.get('outcomes') or []
            if isinstance(objs, str):
                objs = [o.strip() for o in objs.split('\n') if o.strip()]
            course.outcomes = objs
            course.learning_objectives = objs

        if 'category_id' in data:
            course.category = SkillCategory.objects.filter(id=data['category_id']).first()
        if 'department_id' in data:
            course.department = Department.objects.filter(id=data['department_id']).first()

        course.save()

        if 'department_ids' in data:
            course.departments.set(Department.objects.filter(id__in=data['department_ids']))

        return Response(CourseDetailSerializer(course).data)

    def delete(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to delete this course'}, status=status.HTTP_403_FORBIDDEN)

        course_title = course.title
        course.delete()
        return Response({'message': f"Course '{course_title}' successfully deleted."}, status=status.HTTP_200_OK)


# =====================================================================
# 2. Module Management (Add, Edit, Delete, Reorder)
# =====================================================================

class FacultyModuleCreateView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, course_id):
        course = Course.objects.filter(id=course_id).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this course'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        title = data.get('title', '').strip()
        if not title:
            return Response({'error': 'Module title is required'}, status=status.HTTP_400_BAD_REQUEST)

        order = data.get('order')
        if order is None:
            max_order = Module.objects.filter(course=course).count()
            order = max_order + 1

        objs = data.get('learning_objectives', [])
        if isinstance(objs, str):
            objs = [o.strip() for o in objs.split('\n') if o.strip()]

        duration = int(data.get('duration_minutes') or data.get('estimated_minutes') or 30)

        module = Module.objects.create(
            course=course,
            order=int(order),
            title=title,
            description=data.get('description', '').strip(),
            topic_tag=data.get('topic_tag') or f"{course.slug[:12]}_mod{order}",
            duration_minutes=duration,
            estimated_minutes=duration,
            learning_objectives=objs,
            is_required=bool(data.get('is_required', True)),
            status='DRAFT' if course.approval_status == 'DRAFT' else 'PUBLISHED',
            source_type='FACULTY_CREATED',
            created_by=request.user
        )

        return Response(ModuleSerializer(module).data, status=status.HTTP_201_CREATED)


class FacultyModuleDetailView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def put(self, request, pk):
        module = Module.objects.select_related('course').filter(id=pk).first()
        if not module:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

        if module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this module'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        if 'title' in data:
            module.title = data['title'].strip()
        if 'description' in data:
            module.description = data['description'].strip()
        if 'order' in data:
            module.order = int(data['order'])
        if 'duration_minutes' in data or 'estimated_minutes' in data:
            dur = int(data.get('duration_minutes') or data.get('estimated_minutes'))
            module.duration_minutes = dur
            module.estimated_minutes = dur
        if 'is_required' in data:
            module.is_required = bool(data['is_required'])
        if 'learning_objectives' in data:
            objs = data['learning_objectives']
            if isinstance(objs, str):
                objs = [o.strip() for o in objs.split('\n') if o.strip()]
            module.learning_objectives = objs

        module.save()
        return Response(ModuleSerializer(module).data)

    def delete(self, request, pk):
        module = Module.objects.select_related('course').filter(id=pk).first()
        if not module:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

        if module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to delete this module'}, status=status.HTTP_403_FORBIDDEN)

        module.delete()
        return Response({'message': f"Module '{module.title}' successfully deleted."})


# =====================================================================
# 3. Lesson Management (Add, Edit, Delete, Reorder)
# =====================================================================

class FacultyLessonCreateView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, module_id):
        module = Module.objects.select_related('course').filter(id=module_id).first()
        if not module:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

        if module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this course'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        title = data.get('title', '').strip()
        if not title:
            return Response({'error': 'Lesson title is required'}, status=status.HTTP_400_BAD_REQUEST)

        order = data.get('order')
        if order is None:
            max_order = Lesson.objects.filter(module=module).count()
            order = max_order + 1

        duration = int(data.get('duration_minutes') or data.get('estimated_minutes') or 15)

        lesson = Lesson.objects.create(
            module=module,
            order=int(order),
            title=title,
            description=data.get('description', '').strip(),
            content_type=data.get('content_type', 'TEXT'),
            duration_minutes=duration,
            estimated_minutes=duration,
            is_required=bool(data.get('is_required', True)),
            requires_video=bool(data.get('requires_video', False)),
            requires_notes=bool(data.get('requires_notes', False)),
            requires_practice=bool(data.get('requires_practice', False)),
            status='DRAFT' if module.course.approval_status == 'DRAFT' else 'PUBLISHED',
            source_type='FACULTY_CREATED',
            created_by=request.user
        )

        return Response(LessonSerializer(lesson).data, status=status.HTTP_201_CREATED)


class FacultyLessonDetailView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def put(self, request, pk):
        lesson = Lesson.objects.select_related('module__course').filter(id=pk).first()
        if not lesson:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)

        if lesson.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this lesson'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        if 'title' in data:
            lesson.title = data['title'].strip()
        if 'description' in data:
            lesson.description = data['description'].strip()
        if 'order' in data:
            lesson.order = int(data['order'])
        if 'duration_minutes' in data or 'estimated_minutes' in data:
            dur = int(data.get('duration_minutes') or data.get('estimated_minutes'))
            lesson.duration_minutes = dur
            lesson.estimated_minutes = dur
        if 'is_required' in data:
            lesson.is_required = bool(data['is_required'])
        if 'requires_video' in data:
            lesson.requires_video = bool(data['requires_video'])
        if 'requires_notes' in data:
            lesson.requires_notes = bool(data['requires_notes'])
        if 'requires_practice' in data:
            lesson.requires_practice = bool(data['requires_practice'])
        if 'content_type' in data:
            lesson.content_type = data['content_type']

        lesson.save()
        return Response(LessonSerializer(lesson).data)

    def delete(self, request, pk):
        lesson = Lesson.objects.select_related('module__course').filter(id=pk).first()
        if not lesson:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)

        if lesson.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to delete this lesson'}, status=status.HTTP_403_FORBIDDEN)

        lesson.delete()
        return Response({'message': f"Lesson '{lesson.title}' successfully deleted."})


# =====================================================================
# 4. Learning Resources per Lesson (AI Notes, Faculty Notes, YouTube, Practice)
# =====================================================================

class FacultyLessonAINotesView(APIView):
    """
    1-Click AI Study Notes Generation for a specific Lesson.
    Generates 10 structured pedagogical sections, saves as DRAFT with source_type='AI_GENERATED'.
    Faculty can edit the generated notes before publishing.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        lesson = Lesson.objects.select_related('module__course__skill').filter(id=pk).first()
        if not lesson:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)

        if lesson.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this lesson'}, status=status.HTTP_403_FORBIDDEN)

        course = lesson.module.course
        skill_name = course.skill.name if course.skill else course.title
        objs = lesson.learning_objectives or lesson.module.learning_objectives or course.learning_objectives

        gen_result = AICourseBuilderService.generate_lesson_ai_notes(
            skill_name=skill_name,
            course_title=course.title,
            module_title=lesson.module.title,
            lesson_title=lesson.title,
            level=course.level,
            learning_objectives=objs
        )

        is_required = request.data.get('is_required', True)
        title = request.data.get('title') or f"AI Study Notes: {lesson.title}"

        # Create or update study material
        material = StudyMaterial.objects.filter(
            lesson=lesson,
            resource_type='AI_STUDY_NOTES'
        ).exclude(status='ARCHIVED').first()

        if not material:
            material = StudyMaterial.objects.filter(
                lesson=lesson,
                title__icontains='AI Study Notes'
            ).exclude(status='ARCHIVED').first()

        if material:
            material.title = title
            material.description = f"AI-generated 10-section comprehensive study guide for {lesson.title}"
            material.status = 'DRAFT' if course.approval_status == 'DRAFT' else 'PUBLISHED'
            material.structured_content = gen_result['structured_content']
            material.text_content = gen_result['text_content']
            material.explanation_level = course.level if course.level in ['BEGINNER', 'INTERMEDIATE', 'ADVANCED'] else 'BEGINNER'
            material.is_required = is_required
            material.reviewed_by = request.user
            material.reviewed_at = timezone.now()
            material.save()
        else:
            material = StudyMaterial.objects.create(
                module=lesson.module,
                lesson=lesson,
                title=title,
                description=f"AI-generated 10-section comprehensive study guide for {lesson.title}",
                resource_type='AI_STUDY_NOTES',
                source_type='AI_GENERATED',
                status='DRAFT' if course.approval_status == 'DRAFT' else 'PUBLISHED',
                structured_content=gen_result['structured_content'],
                text_content=gen_result['text_content'],
                explanation_level=course.level if course.level in ['BEGINNER', 'INTERMEDIATE', 'ADVANCED'] else 'BEGINNER',
                is_required=is_required,
                uploaded_by=request.user,
                reviewed_by=request.user,
                reviewed_at=timezone.now()
            )

        return Response({
            'message': f"AI study notes generated successfully for lesson '{lesson.title}'.",
            'material': StudyMaterialSerializer(material).data
        }, status=status.HTTP_201_CREATED)


class FacultyLessonManualNotesView(APIView):
    """
    Faculty Manual Notes creation.
    Allows rich markdown content (headings, code blocks, bullet points, callouts, tables).
    Saves with source_type='FACULTY_CREATED'.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        lesson = Lesson.objects.select_related('module__course').filter(id=pk).first()
        if not lesson:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)

        if lesson.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this lesson'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        title = data.get('title', '').strip() or f"Faculty Notes: {lesson.title}"
        text_content = data.get('text_content', '').strip()
        uploaded_file = request.FILES.get('file')
        if not text_content and not uploaded_file:
            return Response({'error': 'Notes content or document file is required'}, status=status.HTTP_400_BAD_REQUEST)

        resource_type = 'NOTES'
        if uploaded_file:
            fname = uploaded_file.name.lower()
            if fname.endswith('.pdf'):
                resource_type = 'PDF'
            elif fname.endswith(('.doc', '.docx')):
                resource_type = 'DOC'
            elif fname.endswith(('.ppt', '.pptx')):
                resource_type = 'PPT'

        is_required = data.get('is_required', True)
        if isinstance(is_required, str):
            is_required = is_required.lower() in ('true', '1')

        material = StudyMaterial.objects.create(
            module=lesson.module,
            lesson=lesson,
            title=title,
            description=data.get('description', '').strip(),
            resource_type=resource_type,
            file=uploaded_file,
            source_type='FACULTY_CREATED',
            status='DRAFT' if lesson.module.course.approval_status == 'DRAFT' else 'PUBLISHED',
            text_content=text_content,
            structured_content={'notes': text_content, 'author': request.user.username},
            is_required=is_required,
            uploaded_by=request.user,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )

        return Response(StudyMaterialSerializer(material).data, status=status.HTTP_201_CREATED)


class FacultyLessonYouTubeView(APIView):
    """
    Adds a verified YouTube learning video to a lesson.
    Validates YouTube URL, extracts 11-char video ID, retrieves genuine oEmbed metadata,
    and stores VideoResource with source_type='YOUTUBE'.
    Zero arbitrary iframe HTML stored. Zero fake URLs.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        lesson = Lesson.objects.select_related('module__course').filter(id=pk).first()
        if not lesson:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)

        if lesson.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this lesson'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        raw_url = data.get('youtube_url', '').strip()
        if not raw_url:
            return Response({'error': 'youtube_url is required'}, status=status.HTTP_400_BAD_REQUEST)

        meta = YouTubeService.fetch_video_metadata(raw_url)
        if not meta or not meta.get('valid'):
            return Response({
                'error': 'Invalid or unreachable YouTube URL. Please provide a standard YouTube watch or share URL.'
            }, status=status.HTTP_400_BAD_REQUEST)

        video_id = meta['video_id']
        title = data.get('title', '').strip() or meta.get('title') or f"YouTube Lecture ({video_id})"
        is_required = data.get('is_required', True)
        order = data.get('order', 1)

        video = VideoResource.objects.create(
            module=lesson.module,
            lesson=lesson,
            title=title,
            description=data.get('description', '').strip(),
            video_type='YOUTUBE',
            source_type='YOUTUBE',
            youtube_url=meta['source_url'],
            youtube_video_id=video_id,
            channel_name=meta.get('author_name', ''),
            thumbnail_url=meta.get('thumbnail_url', YouTubeService.get_standard_thumbnail_url(video_id)),
            duration_seconds=int(data.get('duration_seconds', 600)),
            is_required=is_required,
            order=order,
            status='DRAFT' if lesson.module.course.approval_status == 'DRAFT' else 'PUBLISHED',
            added_by=request.user,
            verified_at=timezone.now()
        )

        return Response(VideoResourceSerializer(video).data, status=status.HTTP_201_CREATED)


class FacultyLessonPracticeView(APIView):
    """
    Adds a practice quiz / MCQ / coding challenge linked to the lesson.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        lesson = Lesson.objects.select_related('module__course').filter(id=pk).first()
        if not lesson:
            return Response({'error': 'Lesson not found'}, status=status.HTTP_404_NOT_FOUND)

        if lesson.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this lesson'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        title = data.get('title', '').strip() or f"Practice Quiz: {lesson.title}"
        task_type = data.get('task_type', 'MCQ_PRACTICE')
        difficulty = data.get('difficulty', 'MEDIUM')
        content = data.get('content') or {}
        if isinstance(content, dict) and 'questions' in content and isinstance(content['questions'], list):
            for idx, q in enumerate(content['questions']):
                if isinstance(q, dict) and 'id' not in q:
                    q['id'] = idx + 1
        pass_score = float(data.get('pass_score', 70.0))
        is_required = bool(data.get('is_required', True))
        order = int(data.get('order', 1))

        practice = PracticeTask.objects.create(
            module=lesson.module,
            lesson=lesson,
            title=title,
            description=data.get('description', '').strip(),
            task_type=task_type,
            difficulty=difficulty,
            content=content,
            explanation=data.get('explanation', '').strip(),
            pass_score=pass_score,
            is_required=is_required,
            order=order,
            source_type='FACULTY_CREATED',
            status='DRAFT' if lesson.module.course.approval_status == 'DRAFT' else 'PUBLISHED'
        )

        return Response(PracticeTaskSerializer(practice).data, status=status.HTTP_201_CREATED)


class FacultyResourceDetailView(APIView):
    """
    Allows faculty to edit or delete any resource (VideoResource, StudyMaterial, PracticeTask) by ID.
    Supports payload or query param resource_type: 'video' | 'material' | 'practice'.
    """
    permission_classes = [IsMentorOrAdmin]

    def put(self, request, pk):
        rtype = request.data.get('resource_type') or request.query_params.get('resource_type')
        data = request.data

        # 1. VideoResource
        if rtype == 'video' or VideoResource.objects.filter(id=pk).exists():
            v = VideoResource.objects.filter(id=pk).first()
            if not v:
                return Response({'error': 'Video resource not found'}, status=status.HTTP_404_NOT_FOUND)
            if 'title' in data:
                v.title = data['title'].strip()
            if 'description' in data:
                v.description = data['description'].strip()
            if 'is_required' in data:
                v.is_required = bool(data['is_required'])
            if 'order' in data:
                v.order = int(data['order'])
            if 'youtube_url' in data:
                meta = YouTubeService.fetch_video_metadata(data['youtube_url'])
                if meta and meta.get('valid'):
                    v.youtube_url = meta['source_url']
                    v.youtube_video_id = meta['video_id']
                    v.channel_name = meta.get('author_name', v.channel_name)
                    v.thumbnail_url = meta.get('thumbnail_url', v.thumbnail_url)
            v.save()
            return Response(VideoResourceSerializer(v).data)

        # 2. StudyMaterial
        elif rtype == 'material' or StudyMaterial.objects.filter(id=pk).exists():
            m = StudyMaterial.objects.filter(id=pk).first()
            if not m:
                return Response({'error': 'Study material not found'}, status=status.HTTP_404_NOT_FOUND)
            if 'title' in data:
                m.title = data['title'].strip()
            if 'text_content' in data:
                m.text_content = data['text_content']
            if 'structured_content' in data:
                m.structured_content = data['structured_content']
            if 'is_required' in data:
                m.is_required = bool(data['is_required'])
            if 'order' in data:
                m.order = int(data['order'])
            uploaded_file = request.FILES.get('file')
            if uploaded_file:
                m.file = uploaded_file
                fname = uploaded_file.name.lower()
                if fname.endswith('.pdf'):
                    m.resource_type = 'PDF'
                elif fname.endswith(('.doc', '.docx')):
                    m.resource_type = 'DOC'
                elif fname.endswith(('.ppt', '.pptx')):
                    m.resource_type = 'PPT'
            m.save()
            return Response(StudyMaterialSerializer(m).data)

        # 3. PracticeTask
        elif rtype == 'practice' or PracticeTask.objects.filter(id=pk).exists():
            p = PracticeTask.objects.filter(id=pk).first()
            if not p:
                return Response({'error': 'Practice task not found'}, status=status.HTTP_404_NOT_FOUND)
            if 'title' in data:
                p.title = data['title'].strip()
            if 'content' in data:
                c = data['content']
                if isinstance(c, dict) and 'questions' in c and isinstance(c['questions'], list):
                    for idx, q in enumerate(c['questions']):
                        if isinstance(q, dict) and 'id' not in q:
                            q['id'] = idx + 1
                p.content = c
            if 'pass_score' in data:
                p.pass_score = float(data['pass_score'])
            if 'is_required' in data:
                p.is_required = bool(data['is_required'])
            if 'order' in data:
                p.order = int(data['order'])
            p.save()
            return Response(PracticeTaskSerializer(p).data)

        return Response({'error': 'Resource not found or type unrecognized'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        rtype = (request.data.get('resource_type') or request.query_params.get('resource_type') or '').lower()
        deleted = False

        if rtype == 'video':
            v = VideoResource.objects.filter(id=pk).first()
            if v:
                if v.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
                    return Response({'error': 'Unauthorized to delete this resource'}, status=status.HTTP_403_FORBIDDEN)
                v.delete()
                deleted = True
        elif rtype in ['material', 'notes', 'study_material']:
            m = StudyMaterial.objects.filter(id=pk).first()
            if m:
                if m.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
                    return Response({'error': 'Unauthorized to delete this resource'}, status=status.HTTP_403_FORBIDDEN)
                m.delete()
                deleted = True
        elif rtype in ['practice', 'quiz']:
            p = PracticeTask.objects.filter(id=pk).first()
            if p:
                if p.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
                    return Response({'error': 'Unauthorized to delete this resource'}, status=status.HTTP_403_FORBIDDEN)
                p.delete()
                deleted = True
        else:
            # Check models sequentially
            v = VideoResource.objects.filter(id=pk).first()
            if v:
                if v.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
                    return Response({'error': 'Unauthorized to delete this resource'}, status=status.HTTP_403_FORBIDDEN)
                v.delete()
                deleted = True
            else:
                m = StudyMaterial.objects.filter(id=pk).first()
                if m:
                    if m.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
                        return Response({'error': 'Unauthorized to delete this resource'}, status=status.HTTP_403_FORBIDDEN)
                    m.delete()
                    deleted = True
                else:
                    p = PracticeTask.objects.filter(id=pk).first()
                    if p:
                        if p.module.course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
                            return Response({'error': 'Unauthorized to delete this resource'}, status=status.HTTP_403_FORBIDDEN)
                        p.delete()
                        deleted = True

        if deleted:
            return Response({'message': 'Resource successfully deleted.'}, status=status.HTTP_200_OK)
        return Response({'error': 'Resource not found'}, status=status.HTTP_404_NOT_FOUND)


# =====================================================================
# 5. Course Validation, Preview & Submit for Review
# =====================================================================

def validate_course_content(course: Course) -> Dict[str, Any]:
    """
    Validates complete course curriculum before submission for institutional admin review:
    - Course title exists
    - Course description exists
    - At least one module exists
    - For every required module: at least one lesson exists
    - For every required lesson: at least one learning resource exists
    - If a lesson is configured to require video -> video must exist
    - If a lesson is configured to require notes -> notes must exist
    - If a lesson is configured to require practice -> practice must exist
    """
    errors = []
    summary = {
        'modules_count': 0,
        'lessons_count': 0,
        'videos_count': 0,
        'materials_count': 0,
        'practice_count': 0
    }

    if not course.title or not course.title.strip():
        errors.append("Course title is missing.")
    if not course.description or not course.description.strip():
        errors.append("Course description is missing.")

    modules = list(course.modules.prefetch_related('lessons__videos', 'lessons__materials', 'lessons__practice_tasks', 'videos', 'materials', 'practice_tasks').all())
    summary['modules_count'] = len(modules)

    if not modules:
        errors.append("Course must contain at least one module.")
        return {'valid': False, 'errors': errors, 'summary': summary}

    for mod in modules:
        lessons = list(mod.lessons.all())
        summary['lessons_count'] += len(lessons)

        if mod.is_required and not lessons:
            # Check if module itself has resources directly
            has_mod_resources = mod.videos.exists() or mod.materials.exists() or mod.practice_tasks.exists()
            if not has_mod_resources:
                errors.append(f"Required module '{mod.title}' must contain at least one lesson or learning resource.")

        for lsn in lessons:
            vids = list(lsn.videos.all())
            mats = list(lsn.materials.all())
            pracs = list(lsn.practice_tasks.all())

            summary['videos_count'] += len(vids)
            summary['materials_count'] += len(mats)
            summary['practice_count'] += len(pracs)

            total_res = len(vids) + len(mats) + len(pracs)
            if lsn.is_required and total_res == 0:
                errors.append(f"Lesson '{lsn.title}' in module '{mod.title}' must have at least one learning resource (notes, video, or practice).")

            if lsn.requires_video and len(vids) == 0:
                errors.append(f"Lesson '{lsn.title}' is configured to require a video, but no video is attached.")

            if lsn.requires_notes and len(mats) == 0:
                errors.append(f"Lesson '{lsn.title}' is configured to require study notes, but no notes are attached.")

            if lsn.requires_practice and len(pracs) == 0:
                errors.append(f"Lesson '{lsn.title}' is configured to require practice, but no practice quiz is attached.")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'summary': summary
    }


class FacultyCourseValidateView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        val_result = validate_course_content(course)
        return Response(val_result, status=status.HTTP_200_OK if val_result['valid'] else status.HTTP_400_BAD_REQUEST)


class FacultyCourseSubmitReviewView(APIView):
    """
    Submits course to Academic Administration for review after verifying curriculum completeness.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to submit this course'}, status=status.HTTP_403_FORBIDDEN)

        # Run strict validation
        val_result = validate_course_content(course)
        if not val_result['valid']:
            return Response({
                'error': 'Course content validation failed. Please address all issues before submitting for review.',
                'validation_errors': val_result['errors'],
                'summary': val_result['summary']
            }, status=status.HTTP_400_BAD_REQUEST)

        course.approval_status = 'PENDING_REVIEW'
        course.content_status = 'PENDING_ADMIN_INPUT'
        course.save(update_fields=['approval_status', 'content_status'])

        notes = request.data.get('notes', 'Submitted course proposal for institutional admin review.')
        CourseApproval.objects.create(
            course=course,
            reviewer=request.user,
            action='SUBMITTED',
            notes=notes
        )

        return Response({
            'message': f"Course '{course.title}' successfully submitted for institutional admin review.",
            'approval_status': course.approval_status,
            'summary': val_result['summary']
        })


class FacultyCoursePreviewView(APIView):
    """
    Simulates the exact student view for the faculty member before submission.
    Returns complete nested course hierarchy with validation metrics.
    """
    permission_classes = [IsMentorOrAdmin]

    def get(self, request, pk):
        course = Course.objects.filter(id=pk).prefetch_related(
            'modules__lessons__videos',
            'modules__lessons__materials',
            'modules__lessons__practice_tasks',
            'modules__videos',
            'modules__materials',
            'modules__practice_tasks',
            'departments'
        ).first()

        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        val_result = validate_course_content(course)
        course_data = CourseDetailSerializer(course).data

        return Response({
            'course': course_data,
            'validation': val_result
        })


# =====================================================================
# 6. AI Video & Material Discovery APIs
# =====================================================================

class AIYouTubeSuggestionsView(APIView):
    """
    AI Recommendation Endpoint for YouTube videos.
    Returns genuine, verified YouTube videos matching the lesson/module topic.
    Never generates fake URLs.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        skill = request.data.get('skill', '')
        course = request.data.get('course', '')
        module = request.data.get('module', '')
        lesson = request.data.get('lesson', '')
        level = request.data.get('level', 'BEGINNER')
        limit = int(request.data.get('limit', 4))

        suggestions = AICourseBuilderService.suggest_youtube_videos(
            skill_name=skill,
            course_title=course,
            module_title=module,
            lesson_title=lesson,
            level=level,
            limit=limit
        )

        return Response({
            'query': {
                'skill': skill,
                'course': course,
                'module': module,
                'lesson': lesson,
                'level': level
            },
            'count': len(suggestions),
            'suggestions': suggestions
        })


class AIStudyMaterialPreviewView(APIView):
    """
    Generates preview of 10-section AI study material without saving immediately.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        skill = request.data.get('skill', '')
        course = request.data.get('course', '')
        module = request.data.get('module', '')
        lesson = request.data.get('lesson', '')
        level = request.data.get('level', 'BEGINNER')
        objs = request.data.get('learning_objectives', [])

        gen_result = AICourseBuilderService.generate_lesson_ai_notes(
            skill_name=skill,
            course_title=course,
            module_title=module,
            lesson_title=lesson,
            level=level,
            learning_objectives=objs
        )

        return Response(gen_result)


# =====================================================================
# 6. Faculty Final Certification Assessment Management
# =====================================================================

class FacultyCourseFinalAssessmentView(APIView):
    """
    Manages a Course's Final Certification Assessment:
    - GET: Retrieve current assessment settings and all questions with options.
    - POST: Create or update assessment configuration (duration, pass %, security rules).
    """
    permission_classes = [IsMentorOrAdmin]

    def get(self, request, course_id):
        course = Course.objects.filter(id=course_id).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to access this course assessment'}, status=status.HTTP_403_FORBIDDEN)

        assessment = Assessment.objects.filter(
            course=course,
            assessment_type='FINAL_ASSESSMENT'
        ).prefetch_related('questions__options').first()

        if not assessment:
            return Response({
                'exists': False,
                'course_id': course.id,
                'course_title': course.title,
                'default_title': f"{course.title} Final Certification Assessment"
            })

        return Response({
            'exists': True,
            'assessment': AssessmentAdminSerializer(assessment).data
        })

    def post(self, request, course_id):
        course = Course.objects.filter(id=course_id).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify this course assessment'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        assessment, created = Assessment.objects.get_or_create(
            course=course,
            assessment_type='FINAL_ASSESSMENT',
            defaults={
                'title': data.get('title') or f"{course.title} Final Certification Assessment",
                'duration_minutes': int(data.get('duration_minutes', 30)),
                'pass_percentage': float(data.get('pass_percentage', 70.0)),
                'max_attempts': int(data.get('max_attempts', 3)),
                'camera_required': bool(data.get('camera_required', True)),
                'screen_share_required': bool(data.get('screen_share_required', True)),
                'fullscreen_required': bool(data.get('fullscreen_required', True)),
                'face_detection_enabled': bool(data.get('face_detection_enabled', True)),
                'is_published': bool(data.get('is_published', True)),
                'created_by': request.user
            }
        )

        if not created:
            if 'title' in data:
                assessment.title = data['title'].strip() or assessment.title
            if 'duration_minutes' in data:
                assessment.duration_minutes = int(data['duration_minutes'])
            if 'pass_percentage' in data:
                assessment.pass_percentage = float(data['pass_percentage'])
            if 'max_attempts' in data:
                assessment.max_attempts = int(data['max_attempts'])
            if 'camera_required' in data:
                assessment.camera_required = bool(data['camera_required'])
            if 'screen_share_required' in data:
                assessment.screen_share_required = bool(data['screen_share_required'])
            if 'fullscreen_required' in data:
                assessment.fullscreen_required = bool(data['fullscreen_required'])
            if 'face_detection_enabled' in data:
                assessment.face_detection_enabled = bool(data['face_detection_enabled'])
            if 'is_published' in data:
                assessment.is_published = bool(data['is_published'])
            assessment.save()

        return Response({
            'exists': True,
            'assessment': AssessmentAdminSerializer(assessment).data
        })


class FacultyCourseAssessmentQuestionCreateOrUpdateView(APIView):
    """
    Manages questions within a Course Final Assessment:
    - POST: Add single question OR batch import questions.
    - PUT: Edit an existing question and its options.
    - DELETE: Remove a question from the assessment.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, course_id):
        course = Course.objects.filter(id=course_id).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to modify questions'}, status=status.HTTP_403_FORBIDDEN)

        assessment, _ = Assessment.objects.get_or_create(
            course=course,
            assessment_type='FINAL_ASSESSMENT',
            defaults={
                'title': f"{course.title} Final Certification Assessment",
                'created_by': request.user
            }
        )

        data = request.data
        questions_list = data.get('questions')
        created_questions = []

        # Batch addition (e.g. from AI selection or CSV)
        if isinstance(questions_list, list) and len(questions_list) > 0:
            with transaction.atomic():
                current_order = assessment.questions.count()
                for q_data in questions_list:
                    current_order += 1
                    text = (q_data.get('text') or q_data.get('question') or '').strip()
                    if not text:
                        continue
                    q_obj = Question.objects.create(
                        assessment=assessment,
                        course=course,
                        text=text,
                        topic_tag=(q_data.get('topic_tag') or 'core')[:64],
                        question_type='MCQ_SINGLE',
                        difficulty=q_data.get('difficulty', 'MEDIUM'),
                        marks=int(q_data.get('marks', 1)),
                        explanation=q_data.get('explanation', '').strip(),
                        order=current_order,
                        is_bank_question=True,
                        status='ACTIVE'
                    )
                    options = q_data.get('options', [])
                    for opt_idx, opt in enumerate(options, start=1):
                        opt_text = (opt.get('text') if isinstance(opt, dict) else str(opt)).strip()
                        is_corr = bool(opt.get('is_correct', False)) if isinstance(opt, dict) else (opt_idx == 1)
                        QuestionOption.objects.create(
                            question=q_obj,
                            text=opt_text,
                            is_correct=is_corr,
                            order=opt_idx
                        )
                    created_questions.append(q_obj)
            return Response({
                'message': f"{len(created_questions)} questions added to assessment.",
                'saved_count': len(created_questions),
                'assessment': AssessmentAdminSerializer(assessment).data
            }, status=status.HTTP_201_CREATED)

        # Single manual question creation
        text = data.get('text', '').strip()
        if not text:
            return Response({'error': 'Question text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        options = data.get('options', [])
        if not options or len(options) < 2:
            return Response({'error': 'Question must have at least 2 options.'}, status=status.HTTP_400_BAD_REQUEST)

        has_correct = any(bool(opt.get('is_correct')) for opt in options if isinstance(opt, dict))
        if not has_correct:
            return Response({'error': 'At least one option must be marked as correct.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            q_order = assessment.questions.count() + 1
            q_obj = Question.objects.create(
                assessment=assessment,
                course=course,
                text=text,
                topic_tag=(data.get('topic_tag') or 'core')[:64],
                question_type=data.get('question_type', 'MCQ_SINGLE'),
                difficulty=data.get('difficulty', 'EASY'),
                marks=int(data.get('marks', 1)),
                explanation=data.get('explanation', '').strip(),
                order=q_order,
                is_bank_question=True,
                status='ACTIVE'
            )
            for opt_idx, opt in enumerate(options, start=1):
                opt_text = (opt.get('text') if isinstance(opt, dict) else str(opt)).strip()
                is_corr = bool(opt.get('is_correct', False)) if isinstance(opt, dict) else False
                QuestionOption.objects.create(
                    question=q_obj,
                    text=opt_text,
                    is_correct=is_corr,
                    order=opt_idx
                )

        return Response({
            'message': 'Question created successfully.',
            'question': QuestionAdminSerializer(q_obj).data,
            'assessment': AssessmentAdminSerializer(assessment).data
        }, status=status.HTTP_201_CREATED)

    def put(self, request, course_id, question_id):
        question = Question.objects.filter(id=question_id, assessment__course_id=course_id).first()
        if not question:
            return Response({'error': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)

        course = question.assessment.course
        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to update this question'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        if 'text' in data and data['text'].strip():
            question.text = data['text'].strip()
        if 'topic_tag' in data:
            question.topic_tag = data['topic_tag'].strip()[:64]
        if 'difficulty' in data:
            question.difficulty = data['difficulty']
        if 'marks' in data:
            question.marks = int(data['marks'])
        if 'explanation' in data:
            question.explanation = data['explanation'].strip()
        question.save()

        if 'options' in data and isinstance(data['options'], list) and len(data['options']) >= 2:
            with transaction.atomic():
                question.options.all().delete()
                for opt_idx, opt in enumerate(data['options'], start=1):
                    opt_text = (opt.get('text') if isinstance(opt, dict) else str(opt)).strip()
                    is_corr = bool(opt.get('is_correct', False)) if isinstance(opt, dict) else False
                    QuestionOption.objects.create(
                        question=question,
                        text=opt_text,
                        is_correct=is_corr,
                        order=opt_idx
                    )

        return Response(QuestionAdminSerializer(question).data)

    def delete(self, request, course_id, question_id):
        question = Question.objects.filter(id=question_id, assessment__course_id=course_id).first()
        if not question:
            return Response({'error': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)

        course = question.assessment.course
        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to delete this question'}, status=status.HTTP_403_FORBIDDEN)

        question.delete()
        return Response({'success': True, 'deleted_id': question_id})


class FacultyCourseAssessmentAIGenerateView(APIView):
    """
    AI-powered question generator for Course Final Certification Assessment.
    Supports previewing generated questions or auto-saving directly to assessment.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, course_id):
        course = Course.objects.filter(id=course_id).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to generate questions for this course'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        count = int(data.get('count', 10))
        difficulty = data.get('difficulty', 'ALL')
        auto_save = bool(data.get('auto_save', False))

        generated_questions = AICourseBuilderService.generate_final_assessment_questions(
            course=course,
            count=count,
            difficulty=difficulty
        )

        if auto_save:
            assessment, _ = Assessment.objects.get_or_create(
                course=course,
                assessment_type='FINAL_ASSESSMENT',
                defaults={
                    'title': f"{course.title} Final Certification Assessment",
                    'created_by': request.user
                }
            )
            saved_questions = []
            with transaction.atomic():
                start_order = assessment.questions.count()
                for q_spec in generated_questions:
                    start_order += 1
                    q_obj = Question.objects.create(
                        assessment=assessment,
                        course=course,
                        text=q_spec['text'],
                        topic_tag=q_spec.get('topic_tag', 'core')[:64],
                        question_type='MCQ_SINGLE',
                        difficulty=q_spec.get('difficulty', 'MEDIUM'),
                        marks=int(q_spec.get('marks', 1)),
                        explanation=q_spec.get('explanation', ''),
                        order=start_order,
                        is_bank_question=True,
                        status='ACTIVE'
                    )
                    for opt_idx, opt in enumerate(q_spec.get('options', []), start=1):
                        QuestionOption.objects.create(
                            question=q_obj,
                            text=opt['text'],
                            is_correct=opt['is_correct'],
                            order=opt_idx
                        )
                    saved_questions.append(q_obj)

            return Response({
                'saved': True,
                'generated_count': len(saved_questions),
                'assessment': AssessmentAdminSerializer(assessment).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'saved': False,
            'generated_count': len(generated_questions),
            'questions': generated_questions
        })


# =====================================================================
# 7. Admin Review & Approval Endpoints
# =====================================================================

class AdminCourseReviewsListView(generics.ListAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        return Course.objects.filter(approval_status='PENDING_REVIEW').select_related(
            'skill', 'department', 'created_by'
        ).prefetch_related('modules__lessons', 'departments').order_by('-updated_at')


class AdminCourseReviewActionView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk, action=None):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        act = (action or request.data.get('action') or '').upper()
        notes = request.data.get('notes', '')

        if act == 'APPROVE':
            course.approval_status = 'APPROVED'
            course.content_status = 'PUBLISHED'
            course.is_published = True
            course.save(update_fields=['approval_status', 'content_status', 'is_published'])

            # Publish all child modules, lessons, and resources
            with transaction.atomic():
                modules = course.modules.all()
                modules.update(status='PUBLISHED', content_status='PUBLISHED')
                for m in modules:
                    m.lessons.all().update(status='PUBLISHED')
                    m.videos.all().update(status='PUBLISHED')
                    m.materials.all().update(status='PUBLISHED')
                    m.practice_tasks.all().update(status='PUBLISHED')

            CourseApproval.objects.create(
                course=course,
                reviewer=request.user,
                action='APPROVED',
                notes=notes or 'Approved and officially published by Academic Administration.'
            )

            return Response({
                'message': f"Course '{course.title}' approved and published to the student catalogue.",
                'approval_status': 'APPROVED',
                'is_published': True
            })

        elif act == 'REJECT':
            course.approval_status = 'REJECTED'
            course.content_status = 'DRAFT'
            course.is_published = False
            course.save(update_fields=['approval_status', 'content_status', 'is_published'])

            CourseApproval.objects.create(
                course=course,
                reviewer=request.user,
                action='REJECTED',
                notes=notes or 'Course proposal requires revisions.'
            )

            return Response({
                'message': f"Course '{course.title}' rejected with revision notes.",
                'approval_status': 'REJECTED'
            })

        return Response({'error': f"Unknown review action '{act}'"}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# 8. Student Course By ID and Progress
# =====================================================================

class StudentCourseDetailByIdView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        course = Course.objects.filter(id=pk).prefetch_related(
            'modules__lessons__videos',
            'modules__lessons__materials',
            'modules__lessons__practice_tasks',
            'modules__videos',
            'modules__materials',
            'modules__practice_tasks',
            'departments',
            'prerequisites'
        ).first()

        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if not (user and user.is_authenticated and (user.role in ['FACULTY', 'MENTOR', 'ADMIN'] or user.is_superuser)):
            if not course.is_published or course.approval_status != 'APPROVED':
                return Response({'error': 'Course is not currently published.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(CourseDetailSerializer(course).data)


class StudentCourseProgressByIdView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        progress = calculate_course_progress(request.user.id, course.id)
        return Response(progress)
