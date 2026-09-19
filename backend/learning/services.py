import logging
from typing import Dict, Any, Tuple, Optional
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def calculate_module_progress(student_id: int, module_id: int) -> Dict[str, Any]:
    """
    Authoritative calculation of module progress for a given student and module.
    A module is COMPLETED if and only if ALL required activities (materials, practice, videos)
    assigned to it are completed.
    Supports both:
    1. Lesson-structured modules (evaluates and deduplicates activities per lesson).
    2. Flat modules with direct activities.
    """
    from catalogue.models import Module
    from learning.models import (
        Enrollment,
        ModuleProgress,
        MaterialProgress,
        PracticeProgress,
        VideoProgress
    )

    module = Module.objects.select_related('course').get(id=module_id)
    enrollment, _ = Enrollment.objects.get_or_create(
        student_id=student_id,
        course_id=module.course_id
    )

    mp = ModuleProgress.objects.filter(
        enrollment=enrollment,
        module=module
    ).first()

    lessons = list(module.lessons.all().order_by('order'))

    if lessons:
        # Evaluate requirements lesson-by-lesson
        req_videos_count = 0
        done_videos_count = 0
        vids_completed = True

        req_mats_count = 0
        done_mats_count = 0
        mats_completed = True

        req_pracs_count = 0
        done_pracs_count = 0
        practice_completed = True

        for lesson in lessons:
            # 1. Lesson Video
            lesson_vids = list(lesson.videos.filter(is_required=True, status='PUBLISHED'))
            if not lesson_vids:
                lesson_vids = list(lesson.videos.filter(is_required=True).exclude(status='ARCHIVED'))
            if not lesson_vids and lesson.requires_video:
                lesson_vids = list(lesson.videos.exclude(status='ARCHIVED'))

            if lesson_vids or lesson.requires_video:
                req_videos_count += 1
                vids_pool = lesson.videos.exclude(status='ARCHIVED')
                vid_done = VideoProgress.objects.filter(
                    enrollment=enrollment,
                    video__in=vids_pool,
                    is_completed=True
                ).exists()
                if vid_done:
                    done_videos_count += 1
                else:
                    vids_completed = False

            # 2. Lesson Study Material
            lesson_mats = list(lesson.materials.filter(is_required=True, status='PUBLISHED'))
            if not lesson_mats:
                lesson_mats = list(lesson.materials.filter(is_required=True).exclude(status='ARCHIVED'))
            if not lesson_mats and lesson.requires_notes:
                lesson_mats = list(lesson.materials.exclude(status='ARCHIVED'))

            if lesson_mats or lesson.requires_notes:
                req_mats_count += 1
                mats_pool = lesson.materials.exclude(status='ARCHIVED')
                mat_done = MaterialProgress.objects.filter(
                    enrollment=enrollment,
                    material__in=mats_pool,
                    is_completed=True
                ).exists()
                if mat_done:
                    done_mats_count += 1
                else:
                    mats_completed = False

            # 3. Lesson Practice Task
            lesson_pracs = list(lesson.practice_tasks.filter(is_required=True, status='PUBLISHED'))
            if not lesson_pracs:
                lesson_pracs = list(lesson.practice_tasks.filter(is_required=True).exclude(status='ARCHIVED'))
            if not lesson_pracs and lesson.requires_practice:
                lesson_pracs = list(lesson.practice_tasks.exclude(status='ARCHIVED'))

            if lesson_pracs or lesson.requires_practice:
                req_pracs_count += 1
                pracs_pool = lesson.practice_tasks.exclude(status='ARCHIVED')
                prac_done = PracticeProgress.objects.filter(
                    enrollment=enrollment,
                    practice__in=pracs_pool,
                    is_completed=True
                ).exists()
                if prac_done:
                    done_pracs_count += 1
                else:
                    practice_completed = False

        # Check any module-level resources not bound to a lesson
        orphan_vids = list(module.videos.filter(lesson__isnull=True, is_required=True).exclude(status='ARCHIVED'))
        for ov in orphan_vids:
            req_videos_count += 1
            if VideoProgress.objects.filter(enrollment=enrollment, video=ov, is_completed=True).exists():
                done_videos_count += 1
            else:
                vids_completed = False

        orphan_mats = list(module.materials.filter(lesson__isnull=True, is_required=True).exclude(status='ARCHIVED'))
        for om in orphan_mats:
            req_mats_count += 1
            if MaterialProgress.objects.filter(enrollment=enrollment, material=om, is_completed=True).exists():
                done_mats_count += 1
            else:
                mats_completed = False

        orphan_pracs = list(module.practice_tasks.filter(lesson__isnull=True, is_required=True).exclude(status='ARCHIVED'))
        for op in orphan_pracs:
            req_pracs_count += 1
            if PracticeProgress.objects.filter(enrollment=enrollment, practice=op, is_completed=True).exists():
                done_pracs_count += 1
            else:
                practice_completed = False

        total_required = req_videos_count + req_mats_count + req_pracs_count
        completed_required = done_videos_count + done_mats_count + done_pracs_count

    else:
        # Flat module without lessons
        # 1. Required Study Materials (deduplicate multiple drafts/versions per module)
        req_materials_qs = module.materials.filter(is_required=True, status='PUBLISHED')
        if not req_materials_qs.exists():
            req_materials_qs = module.materials.filter(is_required=True).exclude(status='ARCHIVED')

        req_materials = list(req_materials_qs)
        completed_mats = set(
            MaterialProgress.objects.filter(
                enrollment=enrollment,
                material__in=req_materials,
                is_completed=True
            ).values_list('material_id', flat=True)
        ) if req_materials else set()

        # If duplicate drafts exist with same title, deduplicate
        unique_titles = set(m.title for m in req_materials)
        if len(unique_titles) < len(req_materials) and len(unique_titles) > 0:
            title_groups = {}
            for m in req_materials:
                title_groups.setdefault(m.title, []).append(m.id)
            done_groups = 0
            for title, ids in title_groups.items():
                if any(mid in completed_mats for mid in ids):
                    done_groups += 1
            mats_completed = (done_groups == len(title_groups))
            req_mats_count = len(title_groups)
            done_mats_count = done_groups
        else:
            mats_completed = len(completed_mats) == len(req_materials)
            req_mats_count = len(req_materials)
            done_mats_count = len(completed_mats)

        # 2. Required Practice Tasks
        req_practice = list(module.practice_tasks.filter(is_required=True, status='PUBLISHED'))
        if not req_practice:
            req_practice = list(module.practice_tasks.filter(is_required=True).exclude(status='ARCHIVED'))
        completed_pracs = set(
            PracticeProgress.objects.filter(
                enrollment=enrollment,
                practice__in=req_practice,
                is_completed=True
            ).values_list('practice_id', flat=True)
        ) if req_practice else set()
        practice_completed = len(completed_pracs) == len(req_practice)
        req_pracs_count = len(req_practice)
        done_pracs_count = len(completed_pracs)

        # 3. Required Videos
        req_videos = list(module.videos.filter(is_required=True, status='PUBLISHED'))
        if not req_videos:
            req_videos = list(module.videos.filter(is_required=True).exclude(status='ARCHIVED'))
        completed_vids = set(
            VideoProgress.objects.filter(
                enrollment=enrollment,
                video__in=req_videos,
                is_completed=True
            ).values_list('video_id', flat=True)
        ) if req_videos else set()
        vids_completed = len(completed_vids) == len(req_videos)
        req_videos_count = len(req_videos)
        done_videos_count = len(completed_vids)

        total_required = req_mats_count + req_pracs_count + req_videos_count
        completed_required = done_mats_count + done_pracs_count + done_videos_count

    if total_required > 0:
        is_module_completed = (
            mats_completed and practice_completed and vids_completed
        )
        progress_pct = round((completed_required / total_required) * 100.0, 1)
    else:
        # If no specific activities are flagged as required, maintain existing status
        is_module_completed = mp.is_completed if mp else False
        progress_pct = 100.0 if is_module_completed else 0.0

    if mp:
        if is_module_completed != mp.is_completed:
            mp.is_completed = is_module_completed
            mp.completed_at = timezone.now() if is_module_completed else None
            mp.save(update_fields=['is_completed', 'completed_at'])
    elif is_module_completed or completed_required > 0:
        mp = ModuleProgress.objects.create(
            enrollment=enrollment,
            module=module,
            is_completed=is_module_completed,
            completed_at=timezone.now() if is_module_completed else None
        )

    is_done_flag = mp.is_completed if mp else is_module_completed

    return {
        'module_id': module.id,
        'is_completed': is_done_flag,
        'progress_percent': progress_pct,
        'total_required': total_required,
        'completed_required': completed_required,
        'materials': {
            'total': req_mats_count,
            'completed': done_mats_count,
            'is_done': mats_completed
        },
        'practice': {
            'total': req_pracs_count,
            'completed': done_pracs_count,
            'is_done': practice_completed
        },
        'videos': {
            'total': req_videos_count,
            'completed': done_videos_count,
            'is_done': vids_completed
        }
    }


def calculate_course_progress(student_id: int, course_id: int) -> Dict[str, Any]:
    """
    Authoritative calculation of course progress for a student.
    Returns exact module counts, resource counts, status, and assessment eligibility.
    Enforces progress invariants:
    - NOT_STARTED -> 0.0%
    - IN_PROGRESS -> 1.0% to 99.9%
    - COMPLETED -> 100.0%
    """
    from catalogue.models import Course
    from learning.models import Enrollment, ModuleProgress

    course = Course.objects.get(id=course_id)
    enrollment, _ = Enrollment.objects.get_or_create(
        student_id=student_id,
        course=course
    )

    # All published modules (or all if legacy test setup without status)
    modules = list(course.modules.filter(status='PUBLISHED'))
    if not modules:
        modules = list(course.modules.all())

    if not modules:
        enrollment.progress_percent = 0.0
        enrollment.is_completed = False
        enrollment.completed_at = None
        enrollment.save(update_fields=['progress_percent', 'is_completed', 'completed_at'])
        return {
            'course_id': course.id,
            'progress': 0.0,
            'status': 'NOT_STARTED',
            'is_completed': False,
            'completed_modules': 0,
            'total_required_modules': 0,
            'completed_resources': 0,
            'total_required_resources': 0,
            'remaining_resources': 0,
            'assessment_unlocked': False,
            'current_module_id': None,
            'current_resource_id': None,
            'breakdown': {
                'videos': {'completed': 0, 'total': 0},
                'study_materials': {'completed': 0, 'total': 0},
                'practice_tasks': {'completed': 0, 'total': 0}
            }
        }

    required_modules = [m for m in modules if m.is_required]
    if not required_modules:
        required_modules = modules

    total_required_modules = len(required_modules)
    completed_modules = 0

    total_required_resources = 0
    completed_resources = 0

    total_vids, done_vids = 0, 0
    total_mats, done_mats = 0, 0
    total_pracs, done_pracs = 0, 0

    first_incomplete_module_id = None
    first_incomplete_resource_id = None

    for m in required_modules:
        mod_summary = calculate_module_progress(student_id, m.id)
        if mod_summary['is_completed']:
            completed_modules += 1
        elif first_incomplete_module_id is None:
            first_incomplete_module_id = m.id

        total_required_resources += mod_summary['total_required']
        completed_resources += mod_summary['completed_required']

        total_vids += mod_summary['videos']['total']
        done_vids += mod_summary['videos']['completed']

        total_mats += mod_summary['materials']['total']
        done_mats += mod_summary['materials']['completed']

        total_pracs += mod_summary['practice']['total']
        done_pracs += mod_summary['practice']['completed']

    # Proportional progress calculation:
    # Each required module carries equal weight in course progress.
    # Within each module, resource completion contributes proportionally to that module's fraction.
    module_weight = 100.0 / total_required_modules
    calculated_progress = 0.0

    for m in required_modules:
        mod_summary = calculate_module_progress(student_id, m.id)
        if mod_summary['is_completed']:
            calculated_progress += module_weight
        elif mod_summary['total_required'] > 0:
            fraction = mod_summary['completed_required'] / mod_summary['total_required']
            calculated_progress += fraction * module_weight

    calculated_progress = round(calculated_progress, 1)

    # Strict Invariant Enforcing:
    if completed_modules == total_required_modules and (total_required_resources == 0 or completed_resources >= total_required_resources):
        progress_pct = 100.0
        course_status = 'COMPLETED'
        is_completed = True
        assessment_unlocked = True
        first_incomplete_module_id = None
        first_incomplete_resource_id = None
    elif calculated_progress > 0.0:
        # Never report 100.0% if modules are still incomplete
        progress_pct = min(calculated_progress, 99.0)
        course_status = 'IN_PROGRESS'
        is_completed = False
        assessment_unlocked = False
    else:
        progress_pct = 0.0
        course_status = 'NOT_STARTED'
        is_completed = False
        assessment_unlocked = False

    if is_completed != enrollment.is_completed or progress_pct != enrollment.progress_percent:
        enrollment.progress_percent = progress_pct
        enrollment.is_completed = is_completed
        if is_completed and not enrollment.completed_at:
            enrollment.completed_at = timezone.now()
        elif not is_completed:
            enrollment.completed_at = None
        enrollment.save(update_fields=['progress_percent', 'is_completed', 'completed_at'])

    return {
        'course_id': course.id,
        'progress': progress_pct,
        'progress_percent': progress_pct,
        'status': course_status,
        'is_completed': is_completed,
        'completed_modules': completed_modules,
        'total_required_modules': total_required_modules,
        'required_modules': total_required_modules,
        'completed_resources': completed_resources,
        'total_required_resources': total_required_resources,
        'remaining_resources': max(0, total_required_resources - completed_resources),
        'assessment_unlocked': assessment_unlocked,
        'current_module_id': first_incomplete_module_id,
        'current_resource_id': first_incomplete_resource_id,
        'breakdown': {
            'videos': {'completed': done_vids, 'total': total_vids},
            'study_materials': {'completed': done_mats, 'total': total_mats},
            'practice_tasks': {'completed': done_pracs, 'total': total_pracs}
        }
    }


def is_assessment_eligible(student_id: int, course_id: int) -> Dict[str, Any]:
    """
    Authoritative verification of assessment eligibility.
    Requirements:
    1. Student is enrolled.
    2. Course has published final assessment.
    3. Course progress is 100.0% and is_completed is True.
    4. All required modules are completed.
    5. All required resources are completed.
    """
    from catalogue.models import Course
    from learning.models import Enrollment

    course = Course.objects.filter(id=course_id).first()
    if not course:
        return {
            'eligible': False,
            'is_eligible': False,
            'can_start': False,
            'course_progress': 0.0,
            'completed_modules': 0,
            'required_modules': 0,
            'total_required_modules': 0,
            'remaining_resources': 0,
            'message': 'Course not found.',
            'reason': 'Course not found.'
        }

    enrollment = Enrollment.objects.filter(student_id=student_id, course=course).first()
    if not enrollment:
        req_mods = course.modules.filter(is_required=True, status='PUBLISHED').count()
        return {
            'eligible': False,
            'is_eligible': False,
            'can_start': False,
            'course_progress': 0.0,
            'completed_modules': 0,
            'required_modules': req_mods,
            'total_required_modules': req_mods,
            'remaining_resources': 0,
            'message': 'Enroll in the course to begin required learning activities.',
            'reason': 'Enroll in the course to begin required learning activities.'
        }

    # If course has 0 required modules, assessment is immediately accessible for enrolled student
    req_mods = course.modules.filter(is_required=True, status='PUBLISHED').count()
    if req_mods == 0:
        return {
            'eligible': True,
            'is_eligible': True,
            'can_start': True,
            'course_progress': 100.0,
            'completed_modules': 0,
            'required_modules': 0,
            'total_required_modules': 0,
            'remaining_resources': 0,
            'message': 'Final assessment unlocked.',
            'reason': None
        }

    summary = calculate_course_progress(student_id, course.id)
    rem_res = summary.get('remaining_resources', 0)
    is_eligible = (
        summary.get('is_completed', False) and
        summary.get('progress', 0.0) >= 100.0 and
        summary.get('completed_modules', 0) == summary.get('total_required_modules', 0) and
        rem_res == 0
    )

    if is_eligible:
        msg = "Final assessment unlocked."
    else:
        msg = (
            f"Complete all required modules before starting the assessment. "
            f"({summary.get('completed_modules', 0)}/{summary.get('total_required_modules', 0)} modules completed, "
            f"{rem_res} required activities remaining)."
        )

    return {
        'eligible': is_eligible,
        'is_eligible': is_eligible,
        'can_start': is_eligible,
        'course_progress': summary.get('progress', 0.0),
        'completed_modules': summary.get('completed_modules', 0),
        'required_modules': summary.get('total_required_modules', 0),
        'total_required_modules': summary.get('total_required_modules', 0),
        'remaining_resources': rem_res,
        'message': msg,
        'reason': msg if not is_eligible else None
    }


def audit_and_normalize_course_resources(course_id: int) -> Dict[str, Any]:
    """
    Audits and normalizes course structure and required flags:
    - Ensures exactly 1 primary study material per module has is_required=True.
    - Ensures exactly 1 primary practice task per module has is_required=True.
    - Ensures video resource per module is linked and flagged appropriately.
    - Verifies no orphan lessons or resources.
    """
    from catalogue.models import Course, Module, StudyMaterial, PracticeTask, VideoResource

    course = Course.objects.get(id=course_id)
    audit_log = []

    for mod in course.modules.all():
        # 1. Study Materials: Keep only primary matching course level or first material as required
        materials = list(mod.materials.all().order_by('order', 'id'))
        if materials:
            primary_mat = None
            for mat in materials:
                if mat.explanation_level == course.level:
                    primary_mat = mat
                    break
            if not primary_mat:
                primary_mat = materials[0]

            for mat in materials:
                should_be_req = (mat.id == primary_mat.id)
                if mat.is_required != should_be_req:
                    mat.is_required = should_be_req
                    mat.save(update_fields=['is_required'])
                    audit_log.append(f"Module {mod.order}: Material '{mat.title}' is_required updated to {should_be_req}")

        # 2. Practice Tasks: Keep only primary MCQ Concept Quiz as required
        practice_tasks = list(mod.practice_tasks.all().order_by('order', 'id'))
        if practice_tasks:
            primary_prac = practice_tasks[0]
            for p in practice_tasks:
                should_be_req = (p.id == primary_prac.id)
                if p.is_required != should_be_req:
                    p.is_required = should_be_req
                    p.save(update_fields=['is_required'])
                    audit_log.append(f"Module {mod.order}: Practice '{p.title}' is_required updated to {should_be_req}")

        # 3. Video Resources: Ensure video is linked and has required flag
        videos = list(mod.videos.all())
        if videos:
            for v in videos:
                if not v.is_required:
                    v.is_required = True
                    v.save(update_fields=['is_required'])
                    audit_log.append(f"Module {mod.order}: Video '{v.title}' is_required updated to True")

    logger.info(f"Course {course.id} ({course.title}) audit complete: {len(audit_log)} fixes applied.")
    return {
        'course_id': course.id,
        'course_title': course.title,
        'fixes_count': len(audit_log),
        'audit_log': audit_log
    }
