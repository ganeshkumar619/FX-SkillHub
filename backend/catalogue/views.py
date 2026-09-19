from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q, Count
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import (
    Department, 
    SkillCategory, 
    SkillDomain, 
    Skill, 
    Course, 
    Module, 
    Lesson,
    VideoResource,
    StudyMaterial,
    PracticeTask,
    CourseApproval,
    CourseVersion,
    AISkillSuggestion,
    StudentSkillProfile,
    SkillRecommendation,
    CourseRecommendation
)
from .serializers import (
    DepartmentSerializer,
    SkillCategorySerializer,
    SkillDomainSerializer,
    SkillSerializer,
    CourseListSerializer,
    CourseDetailSerializer,
    ModuleSerializer,
    LessonSerializer,
    VideoResourceSerializer,
    StudyMaterialSerializer,
    PracticeTaskSerializer,
    CourseApprovalSerializer,
    AISkillSuggestionSerializer
)
from .duplicate_detector import check_skill_duplicate
from .ai_service import AISkillDiscoveryService
from .youtube_service import YouTubeService
from .ai_study_material_service import AIStudyMaterialService
from learning.models import ReportedVideoIssue
from learning.serializers import ReportedVideoIssueSerializer


# ---------------------------------------------------------
# Permissions Helpers
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Public / Student Catalogue Endpoints
# ---------------------------------------------------------

class DepartmentListView(generics.ListAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.AllowAny]


class SkillCategoryListView(generics.ListAPIView):
    queryset = SkillCategory.objects.all().prefetch_related('domains')
    serializer_class = SkillCategorySerializer
    permission_classes = [permissions.AllowAny]


class SkillDomainListView(generics.ListAPIView):
    queryset = SkillDomain.objects.all().select_related('category')
    serializer_class = SkillDomainSerializer
    permission_classes = [permissions.AllowAny]


class SkillListView(generics.ListAPIView):
    serializer_class = SkillSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Skill.objects.all().select_related('category', 'domain', 'department').prefetch_related('departments')
        category = self.request.query_params.get('category')
        domain = self.request.query_params.get('domain')
        dept = self.request.query_params.get('department')
        search = self.request.query_params.get('search')
        level = self.request.query_params.get('level')

        # Students only see approved skills
        user = self.request.user
        if not (user and user.is_authenticated and (user.role in ['FACULTY', 'MENTOR', 'ADMIN'] or user.is_superuser)):
            qs = qs.filter(approval_status='APPROVED')

        if category and category != 'ALL':
            qs = qs.filter(category__name=category)
        if domain and domain != 'ALL':
            qs = qs.filter(domain__name=domain)
        if dept and dept != 'ALL':
            qs = qs.filter(Q(department__code=dept) | Q(departments__code=dept) | Q(is_cross_department=True)).distinct()
        if level and level != 'ALL':
            qs = qs.filter(level=level)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs


class CourseListView(generics.ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        # Strict rule: Students only see published courses that have been approved
        if user and user.is_authenticated and (user.role in ['FACULTY', 'MENTOR', 'ADMIN'] or user.is_superuser):
            qs = Course.objects.all()
        else:
            qs = Course.objects.filter(is_published=True, approval_status='APPROVED')

        qs = qs.select_related('skill', 'department', 'skill__category').prefetch_related('departments', 'modules')

        # Multi-filter parameters
        dept = self.request.query_params.get('department')
        category = self.request.query_params.get('category')
        domain = self.request.query_params.get('domain')
        level = self.request.query_params.get('level')
        course_type = self.request.query_params.get('course_type')
        source_type = self.request.query_params.get('source_type')
        search = self.request.query_params.get('search')
        sort = self.request.query_params.get('sort', 'newest')

        if dept and dept != 'ALL':
            qs = qs.filter(Q(department__code=dept) | Q(departments__code=dept)).distinct()
        if category and category != 'ALL':
            qs = qs.filter(skill__category__name=category)
        if domain and domain != 'ALL':
            qs = qs.filter(skill__domain__name=domain)
        if level and level != 'ALL':
            qs = qs.filter(level=level)
        if course_type and course_type != 'ALL':
            qs = qs.filter(course_types__icontains=course_type)
        if source_type and source_type != 'ALL':
            qs = qs.filter(source_type=source_type)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) | 
                Q(skill__name__icontains=search)
            )

        # Dynamic Sorting
        if sort == 'newest':
            qs = qs.order_by('-created_at')
        elif sort == 'popular':
            qs = qs.annotate(enroll_count=Count('enrollments')).order_by('-enroll_count')
        elif sort == 'duration_asc':
            qs = qs.order_by('estimated_hours')
        elif sort == 'beginner_friendly':
            # Order Beginner first
            qs = qs.order_by('level', '-created_at')

        return qs


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.all().prefetch_related(
            'modules__lessons', 
            'modules__resources', 
            'departments', 
            'prerequisites'
        )
        if not (user and user.is_authenticated and (user.role in ['FACULTY', 'MENTOR', 'ADMIN'] or user.is_superuser)):
            qs = qs.filter(is_published=True, approval_status='APPROVED')
        return qs


class ModuleDetailView(generics.RetrieveAPIView):
    queryset = Module.objects.all().prefetch_related('lessons', 'resources')
    serializer_class = ModuleSerializer
    permission_classes = [permissions.AllowAny]


# ---------------------------------------------------------
# Faculty APIs (Creation, Course Builder, Duplicate Check)
# ---------------------------------------------------------

class SkillDuplicateCheckView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        name = request.data.get('name', '')
        category_id = request.data.get('category_id')
        exclude_id = request.data.get('exclude_id')
        result = check_skill_duplicate(name, category_id, exclude_id)
        return Response(result)


class FacultyCreateSkillView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        data = request.data
        name = data.get('name', '').strip()
        if not name:
            return Response({'error': 'Skill name is required'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Duplicate detection check
        force_create = data.get('force_create', False)
        dup_check = check_skill_duplicate(name)
        if dup_check['has_exact_match'] and not force_create:
            return Response({
                'error': 'Duplicate skill detected',
                'duplicate_info': dup_check
            }, status=status.HTTP_409_CONFLICT)

        # 2. Extract relationships
        category = SkillCategory.objects.filter(id=data.get('category_id')).first()
        if not category:
            category = SkillCategory.objects.first()

        domain = SkillDomain.objects.filter(id=data.get('domain_id')).first() if data.get('domain_id') else None
        department = Department.objects.filter(id=data.get('department_id')).first() if data.get('department_id') else None

        # 3. Create skill with strict Faculty Provenance
        skill = Skill.objects.create(
            name=name,
            category=category,
            domain=domain,
            department=department,
            is_cross_department=data.get('is_cross_department', False),
            description=data.get('description', ''),
            level=data.get('level', 'BEGINNER'),
            skill_type=data.get('skill_type', 'CORE'),
            learning_outcomes=data.get('learning_outcomes', []),
            estimated_duration=data.get('estimated_duration', '4 Weeks'),
            source_type='FACULTY_CREATED',
            source_url=data.get('source_url', ''),
            source_title=data.get('source_title', f'Created by Faculty {request.user.get_full_name() or request.user.username}'),
            created_by=request.user,
            approval_status='PENDING_REVIEW', # Faculty cannot self-approve institutional content
            content_status='DRAFT'
        )

        # Multi departments
        dept_ids = data.get('department_ids', [])
        if dept_ids:
            skill.departments.set(Department.objects.filter(id__in=dept_ids))

        return Response(SkillSerializer(skill).data, status=status.HTTP_201_CREATED)


class FacultyMySkillsView(generics.ListAPIView):
    serializer_class = SkillSerializer
    permission_classes = [IsMentorOrAdmin]

    def get_queryset(self):
        return Skill.objects.filter(created_by=self.request.user).order_by('-created_at')


class FacultySkillDetailView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def delete(self, request, pk):
        skill = Skill.objects.filter(id=pk).first()
        if not skill:
            return Response({'error': 'Skill not found'}, status=status.HTTP_404_NOT_FOUND)

        if skill.created_by != request.user and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Unauthorized to delete this skill'}, status=status.HTTP_403_FORBIDDEN)

        if skill.courses.exists() and request.user.role != 'ADMIN' and not request.user.is_superuser:
            return Response({'error': 'Cannot delete skill with active courses attached.'}, status=status.HTTP_400_BAD_REQUEST)

        skill_name = skill.name
        skill.delete()
        return Response({'message': f"Skill '{skill_name}' successfully deleted."}, status=status.HTTP_200_OK)


class FacultyMyCoursesView(generics.ListAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [IsMentorOrAdmin]

    def get_queryset(self):
        qs = Course.objects.filter(created_by=self.request.user).prefetch_related('modules__lessons', 'departments')
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter != 'ALL':
            qs = qs.filter(approval_status=status_filter)
        return qs.order_by('-created_at')


class FacultyCreateCourseView(APIView):
    """
    Comprehensive Faculty Course Builder API:
    Supports creating Course + Modules + Lessons in a single atomic transaction.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        data = request.data
        title = data.get('title', '').strip()
        if not title:
            return Response({'error': 'Course title is required'}, status=status.HTTP_400_BAD_REQUEST)

        skill = Skill.objects.filter(id=data.get('skill_id')).first()
        if not skill:
            return Response({'error': 'Valid Skill ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        department = Department.objects.filter(id=data.get('department_id')).first()
        
        # Generate unique slug
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while Course.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        instructor_name = data.get('instructor_name') or f"Prof. {request.user.get_full_name() or request.user.username}"

        course = Course.objects.create(
            title=title,
            slug=slug,
            skill=skill,
            department=department,
            instructor_name=instructor_name,
            description=data.get('description', ''),
            outcomes=data.get('outcomes', []),
            thumbnail_url=data.get('thumbnail_url', ''),
            estimated_hours=int(data.get('estimated_hours', 10)),
            course_types=data.get('course_types', ['FACULTY_INITIATIVE']),
            level=data.get('level', skill.level),
            version=1,
            is_published=False, # Faculty cannot directly publish
            approval_status='DRAFT',
            content_status='DRAFT',
            source_type='FACULTY_CREATED',
            source_title=f"Faculty Syllabus: {title}",
            source_url=data.get('source_url', ''),
            created_by=request.user
        )

        # Interdisciplinary multi-departments
        dept_ids = data.get('department_ids', [])
        if dept_ids:
            course.departments.set(Department.objects.filter(id__in=dept_ids))

        # Modules & Lessons builder
        modules_data = data.get('modules', [])
        for m_idx, m_item in enumerate(modules_data, start=1):
            module = Module.objects.create(
                course=course,
                order=m_item.get('order', m_idx),
                title=m_item.get('title', f"Module {m_idx}"),
                description=m_item.get('description', ''),
                topic_tag=m_item.get('topic_tag', f"{slug[:15]}_mod{m_idx}"),
                duration_minutes=int(m_item.get('duration_minutes', 30)),
                source_type='FACULTY_CREATED',
                created_by=request.user
            )

            lessons_data = m_item.get('lessons', [])
            for l_idx, l_item in enumerate(lessons_data, start=1):
                Lesson.objects.create(
                    module=module,
                    order=l_item.get('order', l_idx),
                    title=l_item.get('title', f"Lesson {l_idx}"),
                    content_type=l_item.get('content_type', 'TEXT'),
                    content_url=l_item.get('content_url', ''),
                    text_content=l_item.get('text_content', ''),
                    duration_minutes=int(l_item.get('duration_minutes', 15)),
                    source_type='FACULTY_CREATED',
                    created_by=request.user
                )

        return Response(CourseDetailSerializer(course).data, status=status.HTTP_201_CREATED)


class FacultyUpdateCourseView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def put(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        # Faculty can only edit their own draft or rejected courses
        if course.created_by != request.user and not request.user.role == 'ADMIN':
            return Response({'error': 'Unauthorized to modify this course'}, status=status.HTTP_403_FORBIDDEN)

        if course.approval_status == 'APPROVED' and not request.user.role == 'ADMIN':
            return Response({'error': 'Cannot edit an officially approved course directly. Submit an amendment version.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        if 'title' in data:
            course.title = data['title']
        if 'description' in data:
            course.description = data['description']
        if 'outcomes' in data:
            course.outcomes = data['outcomes']
        if 'estimated_hours' in data:
            course.estimated_hours = int(data['estimated_hours'])
        if 'level' in data:
            course.level = data['level']
        if 'course_types' in data:
            course.course_types = data['course_types']

        course.save()

        # Update departments
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


class FacultySubmitReviewView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if course.created_by != request.user and not request.user.role == 'ADMIN':
            return Response({'error': 'Unauthorized to submit this course'}, status=status.HTTP_403_FORBIDDEN)

        course.approval_status = 'PENDING_REVIEW'
        course.content_status = 'PENDING_ADMIN_INPUT'
        course.save(update_fields=['approval_status', 'content_status'])

        CourseApproval.objects.create(
            course=course,
            reviewer=request.user,
            action='SUBMITTED',
            notes=request.data.get('notes', 'Submitted course proposal for institutional admin review.')
        )

        return Response({
            'message': 'Course successfully submitted for institutional admin review.',
            'approval_status': course.approval_status
        })


class FacultyAIAssistBuilderView(APIView):
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        skill_name = request.data.get('skill_name', '')
        dept_name = request.data.get('department_name')
        result = AISkillDiscoveryService.assist_course_builder(skill_name, dept_name)
        return Response(result)


# ---------------------------------------------------------
# Admin APIs (Governance, Approvals, Source Verification)
# ---------------------------------------------------------

class AdminCourseProposalsListView(generics.ListAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        return Course.objects.filter(approval_status='PENDING_REVIEW').select_related(
            'skill', 'department', 'created_by'
        ).prefetch_related('modules__lessons', 'departments').order_by('-updated_at')


class AdminApproveProposalView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        notes = request.data.get('notes', 'Approved by institutional administrator.')

        course.approval_status = 'APPROVED'
        course.content_status = 'PUBLISHED'
        course.is_published = True
        course.approved_by = request.user
        course.last_verified_at = now
        course.save()

        # Log approval
        CourseApproval.objects.create(
            course=course,
            reviewer=request.user,
            action='APPROVED',
            notes=notes
        )

        # Snapshot version
        modules_snapshot = []
        for m in course.modules.all().prefetch_related('lessons'):
            modules_snapshot.append({
                'order': m.order,
                'title': m.title,
                'lessons': [{'order': l.order, 'title': l.title, 'type': l.content_type} for l in m.lessons.all()]
            })

        CourseVersion.objects.create(
            course=course,
            version_number=course.version,
            snapshot_data={'title': course.title, 'description': course.description, 'modules': modules_snapshot},
            created_by=request.user,
            change_summary=f"Approved version {course.version}: {notes}"
        )

        return Response({
            'message': f"Course '{course.title}' officially approved and published.",
            'course': CourseDetailSerializer(course).data
        })


class AdminRejectProposalView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        notes = request.data.get('notes', 'Course proposal requires revision.')
        course.approval_status = 'REJECTED'
        course.is_published = False
        course.save(update_fields=['approval_status', 'is_published'])

        CourseApproval.objects.create(
            course=course,
            reviewer=request.user,
            action='REJECTED',
            notes=notes
        )

        return Response({
            'message': f"Course proposal '{course.title}' marked as rejected.",
            'approval_status': course.approval_status
        })


class AdminPublishCourseView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        course.is_published = True
        course.content_status = 'PUBLISHED'
        course.save(update_fields=['is_published', 'content_status'])
        return Response({'message': f"Course '{course.title}' published."})


class AdminUnpublishCourseView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        course.is_published = False
        course.content_status = 'UNPUBLISHED'
        course.save(update_fields=['is_published', 'content_status'])
        return Response({'message': f"Course '{course.title}' unpublished."})


class AdminArchiveCourseView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        course.is_published = False
        course.approval_status = 'ARCHIVED'
        course.content_status = 'ARCHIVED'
        course.save(update_fields=['is_published', 'approval_status', 'content_status'])
        return Response({'message': f"Course '{course.title}' archived."})


class AdminCourseDeleteView(APIView):
    """
    Admin endpoint to permanently delete a course (proposal, published, or archived).
    Removes modules, lessons, videos, and associated materials cleanly.
    """
    permission_classes = [IsAdminOnly]

    def delete(self, request, pk):
        course = Course.objects.filter(id=pk).first()
        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
        title = course.title
        course.delete()
        return Response({'message': f"Course '{title}' successfully deleted."}, status=status.HTTP_200_OK)


class AdminVerifySourceView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request):
        resource_type = request.data.get('resource_type', 'course') # 'course' or 'skill'
        resource_id = request.data.get('resource_id')
        now = timezone.now()

        if resource_type == 'course':
            obj = Course.objects.filter(id=resource_id).first()
        else:
            obj = Skill.objects.filter(id=resource_id).first()

        if not obj:
            return Response({'error': 'Resource not found'}, status=status.HTTP_404_NOT_FOUND)

        obj.last_verified_at = now
        obj.content_status = 'PUBLISHED'
        obj.save(update_fields=['last_verified_at', 'content_status'])
        return Response({'message': 'Source provenance successfully verified.', 'last_verified_at': now})


class AdminAISuggestionsListView(generics.ListAPIView):
    serializer_class = AISkillSuggestionSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        return AISkillSuggestion.objects.all().select_related('department')


class AdminApproveAISuggestionView(APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        sugg = AISkillSuggestion.objects.filter(id=pk).first()
        if not sugg:
            return Response({'error': 'AI suggestion not found'}, status=status.HTTP_404_NOT_FOUND)

        # Convert to official draft skill
        cat, _ = SkillCategory.objects.get_or_create(
            name=sugg.category_name,
            defaults={'source_type': 'ADMIN_CREATED'}
        )
        domain = None
        if sugg.domain_name:
            domain, _ = SkillDomain.objects.get_or_create(
                category=cat,
                name=sugg.domain_name,
                defaults={'source_type': 'ADMIN_CREATED'}
            )

        skill, created = Skill.objects.get_or_create(
            name=sugg.title,
            defaults={
                'category': cat,
                'domain': domain,
                'department': sugg.department,
                'level': sugg.level,
                'skill_type': sugg.skill_type,
                'description': sugg.justification,
                'learning_outcomes': sugg.learning_outcomes,
                'source_type': 'AI_SUGGESTED',
                'approval_status': 'APPROVED',
                'content_status': 'PUBLISHED',
                'created_by': request.user,
                'approved_by': request.user,
                'last_verified_at': timezone.now()
            }
        )

        sugg.approval_status = 'APPROVED'
        sugg.reviewed_by = request.user
        sugg.reviewed_at = timezone.now()
        sugg.save()

        return Response({
            'message': f"AI Suggestion '{sugg.title}' converted to approved catalogue skill.",
            'skill_id': skill.id
        })


class AdminAISuggestionDetailView(APIView):
    permission_classes = [IsAdminOnly]

    def delete(self, request, pk):
        sugg = AISkillSuggestion.objects.filter(id=pk).first()
        if not sugg:
            return Response({'error': 'AI suggestion not found'}, status=status.HTTP_404_NOT_FOUND)
        title = sugg.title
        sugg.delete()
        return Response({'message': f"AI Suggestion '{title}' deleted."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------
# AI Skill Discovery & Gap Analysis APIs
# ---------------------------------------------------------

class AISkillDiscoveryView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        prompt = request.data.get('prompt', '')
        dept = request.data.get('department')
        if not prompt:
            return Response({'error': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)

        suggestions = AISkillDiscoveryService.discover_skills(prompt, dept)
        return Response({
            'prompt': prompt,
            'source_label': 'AI_SUGGESTED',
            'disclaimer': 'These are AI-recommended skills and emerging career pathways. They are labeled PENDING_REVIEW until approved by institutional faculty.',
            'suggestions': suggestions
        })


class AISkillGenerateView(APIView):
    """
    Synthesizes and registers an institutional Skill using AI.
    Supports preview_only=true for form pre-filling, or persists the Skill directly.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        skill_name = request.data.get('skill_name', '').strip()
        if not skill_name:
            return Response({'error': 'skill_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        department_code = request.data.get('department_code')
        level = request.data.get('level', 'BEGINNER')
        skill_type = request.data.get('skill_type', 'TECHNICAL')
        preview_only = bool(request.data.get('preview_only', False))

        try:
            result = AISkillDiscoveryService.generate_skill(
                skill_name=skill_name,
                department_code=department_code,
                level=level,
                skill_type=skill_type,
                creator_user=request.user,
                preview_only=preview_only
            )
            return Response(result, status=status.HTTP_200_OK if preview_only else status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("AI Skill generation failed")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AISkillGapAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        analysis = AISkillDiscoveryService.analyze_student_skill_gaps(request.user)
        return Response(analysis)

    def post(self, request):
        analysis = AISkillDiscoveryService.analyze_student_skill_gaps(request.user)
        return Response(analysis)


# ---------------------------------------------------------
# YouTube Learning Video & AI Study Material APIs
# ---------------------------------------------------------

class YouTubeVideoParseView(APIView):
    """
    Parses and verifies a YouTube URL using official YouTube oEmbed API.
    Returns sanitised embed URL, video ID, channel name, and title.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        url = request.data.get('url', '').strip()
        if not url:
            return Response({'error': 'YouTube URL is required'}, status=status.HTTP_400_BAD_REQUEST)

        meta = YouTubeService.fetch_video_metadata(url)
        if not meta or not meta.get('valid'):
            return Response({
                'error': 'Invalid or unsupported YouTube URL. Please provide a standard YouTube watch or share URL.',
                'valid': False
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response(meta)


class VideoResourceCreateView(APIView):
    """
    Faculty & Admin endpoint to add a verified YouTube learning video to a module.
    Automatically verifies URL and extracts metadata without storing media files.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        module_id = request.data.get('module_id')
        youtube_url = request.data.get('youtube_url', '').strip()
        title = request.data.get('title', '').strip()
        is_required = request.data.get('is_required', True)
        order = request.data.get('order', 0)

        if not module_id or not youtube_url:
            return Response({'error': 'module_id and youtube_url are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            module = Module.objects.get(id=module_id)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

        meta = YouTubeService.fetch_video_metadata(youtube_url)
        if not meta or not meta.get('valid'):
            return Response({'error': 'Invalid YouTube URL or metadata lookup failed'}, status=status.HTTP_400_BAD_REQUEST)

        video = VideoResource.objects.create(
            module=module,
            title=title or meta.get('title') or f"Video: {meta.get('video_id')}",
            youtube_url=meta.get('source_url', youtube_url),
            youtube_video_id=meta.get('video_id'),
            channel_name=meta.get('author_name', ''),
            thumbnail_url=meta.get('thumbnail_url', ''),
            source_type='YOUTUBE',
            source_url=meta.get('source_url', youtube_url),
            is_required=is_required,
            order=order,
            added_by=request.user,
            status='APPROVED' if (request.user.role == 'ADMIN' or request.user.is_superuser) else 'PENDING_REVIEW'
        )

        return Response(VideoResourceSerializer(video).data, status=status.HTTP_201_CREATED)


class VideoResourceReviewView(APIView):
    """
    Faculty & Admin endpoint to review, approve, reject, or replace a YouTube video.
    """
    permission_classes = [IsMentorOrAdmin]

    def patch(self, request, pk):
        try:
            video = VideoResource.objects.get(id=pk)
        except VideoResource.DoesNotExist:
            return Response({'error': 'Video resource not found'}, status=status.HTTP_404_NOT_FOUND)

        replace_url = request.data.get('replace_youtube_url', '').strip()
        if replace_url:
            meta = YouTubeService.fetch_video_metadata(replace_url)
            if not meta or not meta.get('valid'):
                return Response({'error': 'Replacement YouTube URL is invalid'}, status=status.HTTP_400_BAD_REQUEST)

            video.youtube_url = meta.get('source_url', replace_url)
            video.youtube_video_id = meta.get('video_id')
            video.channel_name = meta.get('author_name', video.channel_name)
            video.thumbnail_url = meta.get('thumbnail_url', video.thumbnail_url)
            video.source_url = meta.get('source_url', replace_url)
            video.is_unavailable = False
            video.unavailable_reported_count = 0
            if request.data.get('title'):
                video.title = request.data.get('title')
            elif meta.get('title'):
                video.title = meta.get('title')

        if 'is_unavailable' in request.data:
            video.is_unavailable = bool(request.data['is_unavailable'])
            if not video.is_unavailable:
                video.unavailable_reported_count = 0

        if 'status' in request.data:
            video.status = request.data['status']

        if 'title' in request.data and not replace_url:
            video.title = request.data['title']

        video.verified_at = timezone.now()
        video.save()

        return Response(VideoResourceSerializer(video).data)


class AIStudyMaterialGenerateView(APIView):
    """
    Faculty & Admin 1-click endpoint to generate 9-section structured AI study notes,
    attach verified real educational YouTube video, and create aligned practice questions.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request, pk):
        try:
            module = Module.objects.select_related('course').get(id=pk)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

        result = AIStudyMaterialService.generate_and_save_module_content(module)

        return Response({
            'message': f"Curriculum generated successfully for module '{module.title}'.",
            'module_id': module.id,
            'module_title': module.title,
            'video': VideoResourceSerializer(result['video']).data if result.get('video') else None,
            'material': StudyMaterialSerializer(result['material']).data if result.get('material') else None,
            'practice_task': PracticeTaskSerializer(result['practice_task']).data if result.get('practice_task') else None
        }, status=status.HTTP_200_OK)


class AdminReportedVideoIssuesView(APIView):
    """
    Admin review queue for student-reported unavailable/broken videos.
    Supports listing open issues and resolving them with video replacements.
    """
    permission_classes = [IsMentorOrAdmin]

    def get(self, request):
        status_filter = request.query_params.get('status', 'OPEN')
        qs = ReportedVideoIssue.objects.select_related('video', 'student', 'video__module', 'video__module__course')
        if status_filter != 'ALL':
            qs = qs.filter(status=status_filter)

        serializer = ReportedVideoIssueSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, pk=None):
        issue_id = pk or request.data.get('issue_id')
        action = request.data.get('action', 'RESOLVE')  # RESOLVE or DISMISS
        replacement_url = request.data.get('replacement_youtube_url', '').strip()

        if not issue_id:
            return Response({'error': 'issue_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            issue = ReportedVideoIssue.objects.select_related('video').get(id=issue_id)
        except ReportedVideoIssue.DoesNotExist:
            return Response({'error': 'Reported issue not found'}, status=status.HTTP_404_NOT_FOUND)

        if action == 'RESOLVE':
            v = issue.video
            if replacement_url:
                meta = YouTubeService.fetch_video_metadata(replacement_url)
                if meta and (meta.get('valid') or meta.get('is_valid')):
                    v.youtube_url = meta.get('source_url', replacement_url)
                    v.youtube_video_id = meta.get('video_id')
                    v.channel_name = meta.get('author_name', v.channel_name)
                    v.thumbnail_url = meta.get('thumbnail_url', v.thumbnail_url)
                    issue.replacement_video_id = meta.get('video_id')

            v.is_unavailable = False
            v.unavailable_reported_count = 0
            v.save()

            issue.status = 'RESOLVED'
            issue.resolved_by = request.user
            issue.resolved_at = timezone.now()
            issue.save()

        elif action == 'DISMISS':
            issue.status = 'DISMISSED'
            issue.resolved_by = request.user
            issue.resolved_at = timezone.now()
            issue.save()

            v = issue.video
            v.is_unavailable = False
            v.unavailable_reported_count = 0
            v.save()

        return Response({
            'message': f"Reported issue {action.lower()}d successfully.",
            'issue': ReportedVideoIssueSerializer(issue).data
        })

    def delete(self, request, pk=None):
        issue_id = pk or request.data.get('issue_id')
        if not issue_id:
            return Response({'error': 'issue_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        issue = ReportedVideoIssue.objects.filter(id=issue_id).first()
        if not issue:
            return Response({'error': 'Reported issue not found'}, status=status.HTTP_404_NOT_FOUND)
        issue.delete()
        return Response({'message': 'Reported video issue deleted successfully.', 'id': issue_id}, status=status.HTTP_200_OK)


class AICourseGenerateView(APIView):
    """
    Unified AI endpoint to generate a full production-ready course,
    including modules, lessons, 4-level study materials, video scripts/storyboards,
    practice challenges, semantic duplicate-free question bank, and assessment blueprint.
    """
    permission_classes = [IsMentorOrAdmin]

    def post(self, request):
        skill_name = request.data.get('skill_name', '').strip()
        course_name = request.data.get('course_name', '').strip()
        level = request.data.get('level', 'BEGINNER').strip().upper()
        target_audience = request.data.get('target_audience', '').strip()
        learning_goal = request.data.get('learning_goal', '').strip()
        optional_duration = request.data.get('optional_duration')
        department_code = request.data.get('department_code')
        module_count = int(request.data.get('module_count', 4))

        if not skill_name:
            return Response({'error': 'skill_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .ai_course_generator_service import AICourseGeneratorService
            result = AICourseGeneratorService.generate_full_course(
                skill_name=skill_name,
                course_name=course_name,
                level=level,
                target_audience=target_audience,
                learning_goal=learning_goal,
                optional_duration=optional_duration,
                creator_user=request.user,
                department_code=department_code,
                module_count=max(2, min(module_count, 8))
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("AI Course generation failed")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseQuestionBankView(APIView):
    """
    View to inspect and expand the approved AI Question Bank for a course.
    """
    permission_classes = [IsMentorOrAdmin]

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        from assessments.models import Question
        questions = Question.objects.filter(
            Q(course=course) | Q(assessment__course=course)
        ).distinct().prefetch_related('options')

        diff_counts = {'EASY': 0, 'MEDIUM': 0, 'HARD': 0}
        q_list = []
        for q in questions:
            d = q.difficulty if q.difficulty in diff_counts else 'MEDIUM'
            diff_counts[d] = diff_counts.get(d, 0) + 1
            q_list.append({
                'id': q.id,
                'text': q.text,
                'difficulty': q.difficulty,
                'topic_tag': q.topic_tag,
                'marks': q.marks,
                'is_bank_question': q.is_bank_question,
                'semantic_hash': q.semantic_hash,
                'explanation': q.explanation,
                'options': [{'id': o.id, 'text': o.text, 'is_correct': o.is_correct} for o in q.options.all()]
            })

        return Response({
            'course_id': course.id,
            'course_title': course.title,
            'blueprint': course.blueprint,
            'total_questions': len(q_list),
            'difficulty_breakdown': diff_counts,
            'questions': q_list
        })

    def post(self, request, course_id):
        """Expand question bank with additional AI questions."""
        try:
            course = Course.objects.prefetch_related('modules').get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        from .ai_course_generator_service import AICourseGeneratorService
        from assessments.models import Question, QuestionOption
        from assessments.question_bank_service import QuestionBankService

        added = []
        for mod in course.modules.all():
            candidates = AICourseGeneratorService._generate_topic_questions(
                skill_name=course.skill.name if course.skill else course.title,
                module_spec={'title': mod.title, 'topic_tag': mod.topic_tag}
            )
            for c in candidates:
                is_dup, _ = QuestionBankService.is_duplicate(course.id, c['text'])
                if not is_dup:
                    sem_hash = QuestionBankService.compute_semantic_hash(c['text'])
                    q = Question.objects.create(
                        course=course,
                        is_bank_question=True,
                        text=c['text'],
                        topic_tag=mod.topic_tag,
                        question_type='MCQ_SINGLE',
                        difficulty=c['difficulty'],
                        marks=c.get('marks', 1),
                        explanation=c.get('explanation', ''),
                        semantic_hash=sem_hash,
                        quality_score=1.0
                    )
                    for opt_idx, opt in enumerate(c['options'], start=1):
                        QuestionOption.objects.create(
                            question=q,
                            text=opt['text'],
                            is_correct=opt['is_correct'],
                            order=opt_idx
                        )
                    added.append(q.id)

        return Response({
            'message': f"Question bank expanded successfully. Added {len(added)} new questions.",
            'added_count': len(added),
            'added_ids': added
        })


class VideoPackageDetailView(APIView):
    """
    Endpoint to retrieve Mode B AI Video Script, Narration, and Storyboard packages.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, video_id):
        try:
            video = VideoResource.objects.select_related('module', 'module__course').get(id=video_id)
        except VideoResource.DoesNotExist:
            return Response({'error': 'Video resource not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'video_id': video.id,
            'title': video.title,
            'video_type': video.video_type,
            'ai_video_status': video.ai_video_status,
            'video_provider': video.video_provider,
            'duration_seconds': video.duration_seconds,
            'script_package': video.script_package,
            'captions': video.captions,
            'source_type': video.source_type,
            'youtube_url': video.youtube_url if video.video_type == 'YOUTUBE' else None,
            'youtube_video_id': video.youtube_video_id if video.video_type == 'YOUTUBE' else None,
        })
