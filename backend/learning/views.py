from django.utils import timezone
from rest_framework import views, generics, status, permissions
from rest_framework.response import Response
from .models import (
    Enrollment, 
    ModuleProgress, 
    VideoProgress, 
    MaterialProgress, 
    PracticeProgress,
    ReportedVideoIssue
)
from .serializers import EnrollmentSerializer
from catalogue.models import (
    Course, 
    Module, 
    VideoResource, 
    StudyMaterial, 
    PracticeTask
)
from audit.models import AuditLog


class EnrollmentListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__department', 'course__skill')
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    def post(self, request):
        course_id = request.data.get('course_id')
        if not course_id:
            return Response({'error': 'course_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = Course.objects.get(id=course_id, is_published=True)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={
                'is_demo': getattr(request.user, 'is_demo', False)
            }
        )

        AuditLog.log_action(
            action='COURSE_ENROLLED' if created else 'ENROLLMENT_ACCESSED',
            resource_type='Course',
            resource_id=course.id,
            user=request.user
        )

        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CourseProgressDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_slug):
        if str(course_slug).isdigit():
            course = Course.objects.filter(id=int(course_slug)).first()
        else:
            course = Course.objects.filter(slug=course_slug).first()

        if not course:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        from .services import calculate_course_progress, is_assessment_eligible

        summary = calculate_course_progress(request.user.id, course.id)
        elig = is_assessment_eligible(request.user.id, course.id)

        enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        enrolled = enrollment is not None

        module_items = {}
        video_items = {}
        material_items = {}
        practice_items = {}

        if enrollment:
            module_items = {
                mp.module_id: mp.is_completed
                for mp in enrollment.module_progress.all()
            }
            video_items = {
                vp.video_id: {
                    'watched_seconds': vp.watched_seconds,
                    'watch_percentage': vp.watch_percentage,
                    'last_position': vp.last_position,
                    'is_completed': vp.is_completed
                }
                for vp in enrollment.video_progress.all()
            }
            material_items = {
                mp.material_id: {
                    'status': mp.status,
                    'is_completed': mp.is_completed
                }
                for mp in enrollment.material_progress.all()
            }
            practice_items = {
                pp.practice_id: {
                    'attempt_count': pp.attempt_count,
                    'best_score': pp.best_score,
                    'is_completed': pp.is_completed
                }
                for pp in enrollment.practice_progress.all()
            }

        return Response({
            'enrolled': enrolled,
            'enrollment_id': enrollment.id if enrollment else None,
            'course_id': course.id,
            'course_slug': course.slug,
            'course_title': course.title,
            'progress': summary['progress'],
            'progress_percent': summary['progress_percent'],
            'status': summary['status'],
            'is_completed': summary['is_completed'],
            'completed_modules': summary['completed_modules'],
            'total_required_modules': summary['total_required_modules'],
            'completed_resources': summary['completed_resources'],
            'total_required_resources': summary['total_required_resources'],
            'remaining_resources': summary['remaining_resources'],
            'assessment_unlocked': summary['assessment_unlocked'],
            'current_module_id': summary['current_module_id'],
            'current_resource_id': summary['current_resource_id'],
            'breakdown': summary['breakdown'],
            'module_progress': module_items,
            'video_progress': video_items,
            'material_progress': material_items,
            'practice_progress': practice_items,
            'eligibility': elig
        })


class CompleteModuleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, module_id=None):
        if not module_id:
            module_id = request.data.get('module_id')
        if not module_id:
            return Response({'error': 'module_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            module = Module.objects.select_related('course').get(id=module_id)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, _ = Enrollment.objects.get_or_create(
            student=request.user,
            course=module.course,
            defaults={'is_demo': getattr(request.user, 'is_demo', False)}
        )

        from .services import calculate_module_progress, calculate_course_progress
        mod_summary = calculate_module_progress(request.user.id, module.id)
        course_summary = calculate_course_progress(request.user.id, module.course_id)

        if not mod_summary['is_completed']:
            return Response({
                'error': 'Cannot mark module complete: required videos, study materials, or practice tasks are incomplete.',
                'module_completed': False,
                'progress_percent': course_summary['progress'],
                'is_completed': course_summary['is_completed'],
                'details': mod_summary
            }, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log_action(
            action='MODULE_COMPLETED',
            resource_type='Module',
            resource_id=module.id,
            user=request.user,
            metadata={'course': module.course.title, 'new_percent': course_summary['progress']}
        )

        return Response({
            'message': 'Module marked as completed',
            'module_completed': True,
            'progress_percent': course_summary['progress'],
            'is_completed': course_summary['is_completed'],
            'assessment_unlocked': course_summary['assessment_unlocked'],
            'summary': course_summary
        })

    def get(self, request, module_id=None):
        if not module_id:
            module_id = request.query_params.get('module_id')
        if not module_id:
            return Response({'error': 'module_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            module = Module.objects.select_related('course').get(id=module_id)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)

        from .services import calculate_module_progress, calculate_course_progress
        mod_summary = calculate_module_progress(request.user.id, module.id)
        course_summary = calculate_course_progress(request.user.id, module.course_id)
        return Response({
            'module_id': module.id,
            'is_completed': mod_summary['is_completed'],
            'module_completed': mod_summary['is_completed'],
            'details': mod_summary,
            'course_completed': course_summary['is_completed'],
            'assessment_unlocked': course_summary['assessment_unlocked'],
            'completed_modules': course_summary['completed_modules'],
            'total_required_modules': course_summary['total_required_modules']
        })


class VideoProgressView(views.APIView):
    """
    Records video playback heartbeat and enforces the 80% completion rule.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        video_id = request.data.get('video_id')
        current_seconds = request.data.get('current_seconds')
        watched_seconds = request.data.get('watched_seconds')
        watch_pct_in = request.data.get('watch_percentage')
        duration_seconds = request.data.get('duration_seconds')
        is_completed_flag = request.data.get('is_completed')

        if not video_id:
            return Response({'error': 'video_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            video = VideoResource.objects.select_related('module', 'module__course').get(id=video_id)
        except VideoResource.DoesNotExist:
            return Response({'error': 'Video resource not found'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, _ = Enrollment.objects.get_or_create(
            student=request.user,
            course=video.module.course,
            defaults={'is_demo': getattr(request.user, 'is_demo', False)}
        )

        vp, _ = VideoProgress.objects.get_or_create(
            enrollment=enrollment,
            video=video
        )

        dur = float(duration_seconds) if duration_seconds else (video.duration_seconds or 300)
        secs = float(current_seconds) if current_seconds is not None else (float(watched_seconds) if watched_seconds is not None else 0.0)

        vp.last_position = int(secs)
        if secs > vp.watched_seconds:
            vp.watched_seconds = int(secs)

        calc_pct = round((vp.watched_seconds / dur) * 100.0, 1)
        if watch_pct_in is not None:
            calc_pct = max(calc_pct, float(watch_pct_in))
        vp.watch_percentage = min(calc_pct, 100.0)

        threshold = video.completion_threshold_percent or 80.0
        if (
            vp.watch_percentage >= threshold or 
            is_completed_flag is True or 
            (watched_seconds is not None and float(watched_seconds) >= dur * 0.8)
        ):
            if not vp.is_completed:
                vp.is_completed = True
                vp.completion_mode = 'WATCH_THRESHOLD'
                vp.completed_at = timezone.now()
        vp.save()

        from .services import calculate_module_progress, calculate_course_progress
        mod_summary = calculate_module_progress(request.user.id, video.module_id)
        course_summary = calculate_course_progress(request.user.id, video.module.course_id)

        return Response({
            'video_id': video.id,
            'watched_seconds': vp.watched_seconds,
            'watch_percentage': vp.watch_percentage,
            'is_completed': vp.is_completed,
            'module_completed': mod_summary['is_completed'],
            'course_progress': course_summary['progress'],
            'assessment_unlocked': course_summary['assessment_unlocked'],
            'summary': course_summary
        })


class MaterialCompleteView(views.APIView):
    """
    Marks a study material (PDF, doc, notes) as completed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        material_id = request.data.get('material_id')
        if not material_id:
            return Response({'error': 'material_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            material = StudyMaterial.objects.select_related('module', 'module__course').get(id=material_id)
        except StudyMaterial.DoesNotExist:
            return Response({'error': 'Study material not found'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, _ = Enrollment.objects.get_or_create(
            student=request.user,
            course=material.module.course,
            defaults={'is_demo': getattr(request.user, 'is_demo', False)}
        )

        mp, _ = MaterialProgress.objects.get_or_create(
            enrollment=enrollment,
            material=material
        )

        mp.status = 'COMPLETED'
        mp.is_completed = True
        mp.completed_at = timezone.now()
        mp.save()

        from .services import calculate_module_progress, calculate_course_progress
        mod_summary = calculate_module_progress(request.user.id, material.module_id)
        course_summary = calculate_course_progress(request.user.id, material.module.course_id)

        return Response({
            'material_id': material.id,
            'status': mp.status,
            'is_completed': mp.is_completed,
            'module_completed': mod_summary['is_completed'],
            'course_progress': course_summary['progress'],
            'assessment_unlocked': course_summary['assessment_unlocked'],
            'summary': course_summary
        })


def evaluate_mcq_answer(user_ans, expected, options=None):
    """
    Evaluates student practice response against expected correct answer.
    Supports:
    - Letter options ('A', 'B', 'C', 'D' / 'a', 'b', 'c', 'd')
    - Full text options ('printf()')
    - Numeric 0-based indices (0, 1, 2, 3)
    - Cross-matching: user chose option text, expected is letter (e.g. 'printf()' vs 'B')
    - Cross-matching: user chose letter, expected is option text (e.g. 'B' vs 'printf()')
    """
    if user_ans is None or expected is None:
        return False

    u_str = str(user_ans).strip()
    e_str = str(expected).strip()

    # 1. Direct case-insensitive string match
    if u_str.lower() == e_str.lower():
        return True

    opts = options if isinstance(options, list) else []
    if not opts:
        return False

    def letter_to_idx(val):
        if len(val) == 1 and val.isalpha():
            idx = ord(val.upper()) - ord('A')
            if 0 <= idx < len(opts):
                return idx
        return None

    def num_to_idx(val):
        try:
            num = int(val)
            if 0 <= num < len(opts):
                return num
        except (ValueError, TypeError):
            pass
        return None

    def text_to_idx(val):
        target = str(val).strip().lower()
        for idx, o in enumerate(opts):
            if str(o).strip().lower() == target:
                return idx
        return None

    def resolve_idx(val):
        # 1. Letter
        idx = letter_to_idx(val)
        if idx is not None:
            return idx
        # 2. Text match
        idx = text_to_idx(val)
        if idx is not None:
            return idx
        # 3. Numeric index
        idx = num_to_idx(val)
        if idx is not None:
            return idx
        return None

    e_idx = resolve_idx(e_str)
    u_idx = resolve_idx(u_str)

    if e_idx is not None and u_idx is not None and e_idx == u_idx:
        return True

    if e_idx is not None and 0 <= e_idx < len(opts):
        if str(opts[e_idx]).strip().lower() == u_str.lower():
            return True

    if u_idx is not None and 0 <= u_idx < len(opts):
        if str(opts[u_idx]).strip().lower() == e_str.lower():
            return True

    return False


class PracticeSubmitView(views.APIView):
    """
    Submits student responses for a practice task and evaluates pass/fail status.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        practice_id = request.data.get('practice_id')
        submitted_score = request.data.get('score')
        answers = request.data.get('answers', {})

        if not practice_id:
            return Response({'error': 'practice_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            practice = PracticeTask.objects.select_related('module', 'module__course').get(id=practice_id)
        except PracticeTask.DoesNotExist:
            return Response({'error': 'Practice task not found'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, _ = Enrollment.objects.get_or_create(
            student=request.user,
            course=practice.module.course,
            defaults={'is_demo': getattr(request.user, 'is_demo', False)}
        )

        pp, _ = PracticeProgress.objects.get_or_create(
            enrollment=enrollment,
            practice=practice
        )

        final_score = 0.0
        questions = practice.content.get('questions', []) if isinstance(practice.content, dict) else []
        if questions:
            correct_count = 0
            for idx, q in enumerate(questions):
                expected = q.get('correct_option') if q.get('correct_option') is not None else q.get('correct_answer')
                options = q.get('options', [])

                q_id = str(q.get('id')) if q.get('id') is not None else None
                user_ans = None
                if q_id is not None:
                    user_ans = answers.get(q_id) if answers.get(q_id) is not None else answers.get(q.get('id'))
                if user_ans is None:
                    user_ans = answers.get(str(idx)) if answers.get(str(idx)) is not None else answers.get(idx)
                if user_ans is None and len(questions) == 1 and len(answers) == 1:
                    user_ans = list(answers.values())[0]

                if evaluate_mcq_answer(user_ans, expected, options):
                    correct_count += 1

            final_score = round((correct_count / len(questions)) * 100.0, 1)
        elif submitted_score is not None:
            final_score = float(submitted_score)
        else:
            final_score = 100.0

        pp.record_attempt(final_score)

        from .services import calculate_module_progress, calculate_course_progress
        mod_summary = calculate_module_progress(request.user.id, practice.module_id)
        course_summary = calculate_course_progress(request.user.id, practice.module.course_id)

        return Response({
            'practice_id': practice.id,
            'score': final_score,
            'pass_score': practice.pass_score,
            'is_completed': pp.is_completed,
            'attempts': pp.attempt_count,
            'best_score': pp.best_score,
            'module_completed': mod_summary['is_completed'],
            'course_progress': course_summary['progress'],
            'assessment_unlocked': course_summary['assessment_unlocked'],
            'summary': course_summary
        })


class CourseAssessmentEligibilityView(views.APIView):
    """
    Returns server-authoritative assessment eligibility for a course.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        from .services import is_assessment_eligible
        elig = is_assessment_eligible(request.user.id, course_id)
        if elig['message'] == 'Course not found.':
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(elig)


class GenericResourceCompleteView(views.APIView):
    """
    Generic completion endpoint: POST /api/learning/resources/<int:resource_id>/complete/
    Accepts any resource ID (Video, Study Material, Practice Task) and marks it completed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, resource_id):
        from catalogue.models import VideoResource, StudyMaterial, PracticeTask
        from .services import calculate_module_progress, calculate_course_progress

        vid = VideoResource.objects.filter(id=resource_id).first()
        if vid:
            enrollment, _ = Enrollment.objects.get_or_create(student=request.user, course=vid.module.course)
            vp, _ = VideoProgress.objects.get_or_create(enrollment=enrollment, video=vid)
            vp.is_completed = True
            vp.watch_percentage = 100.0
            vp.watched_seconds = vid.duration_seconds or 300
            vp.completed_at = timezone.now()
            vp.save()
            mod_summary = calculate_module_progress(request.user.id, vid.module_id)
            course_summary = calculate_course_progress(request.user.id, vid.module.course_id)
            return Response({
                'resource_id': resource_id,
                'resource_type': 'VIDEO',
                'is_completed': True,
                'module_completed': mod_summary['is_completed'],
                'course_progress': course_summary['progress'],
                'assessment_unlocked': course_summary['assessment_unlocked'],
                'summary': course_summary
            })

        mat = StudyMaterial.objects.filter(id=resource_id).first()
        if mat:
            enrollment, _ = Enrollment.objects.get_or_create(student=request.user, course=mat.module.course)
            mp, _ = MaterialProgress.objects.get_or_create(enrollment=enrollment, material=mat)
            mp.is_completed = True
            mp.status = 'COMPLETED'
            mp.completed_at = timezone.now()
            mp.save()
            mod_summary = calculate_module_progress(request.user.id, mat.module_id)
            course_summary = calculate_course_progress(request.user.id, mat.module.course_id)
            return Response({
                'resource_id': resource_id,
                'resource_type': 'STUDY_MATERIAL',
                'is_completed': True,
                'module_completed': mod_summary['is_completed'],
                'course_progress': course_summary['progress'],
                'assessment_unlocked': course_summary['assessment_unlocked'],
                'summary': course_summary
            })

        prac = PracticeTask.objects.filter(id=resource_id).first()
        if prac:
            enrollment, _ = Enrollment.objects.get_or_create(student=request.user, course=prac.module.course)
            pp, _ = PracticeProgress.objects.get_or_create(enrollment=enrollment, practice=prac)
            pp.is_completed = True
            pp.best_score = 100.0
            pp.completed_at = timezone.now()
            pp.save()
            mod_summary = calculate_module_progress(request.user.id, prac.module_id)
            course_summary = calculate_course_progress(request.user.id, prac.module.course_id)
            return Response({
                'resource_id': resource_id,
                'resource_type': 'PRACTICE_TASK',
                'is_completed': True,
                'module_completed': mod_summary['is_completed'],
                'course_progress': course_summary['progress'],
                'assessment_unlocked': course_summary['assessment_unlocked'],
                'summary': course_summary
            })

        return Response({'error': 'Resource not found'}, status=status.HTTP_404_NOT_FOUND)


class VideoStartView(views.APIView):
    """
    Registers that a student has started playing a YouTube video.
    Initializes VideoProgress and records started_at timestamp.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, video_id=None):
        v_id = video_id or request.data.get('video_id')
        if not v_id:
            return Response({'error': 'video_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            video = VideoResource.objects.select_related('module', 'module__course').get(id=v_id)
        except VideoResource.DoesNotExist:
            return Response({'error': 'Video resource not found'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, _ = Enrollment.objects.get_or_create(
            student=request.user,
            course=video.module.course,
            defaults={'is_demo': getattr(request.user, 'is_demo', False)}
        )

        vp, _ = VideoProgress.objects.get_or_create(
            enrollment=enrollment,
            video=video
        )
        vp.record_start()

        return Response({
            'video_id': video.id,
            'started': True,
            'started_at': vp.started_at,
            'is_completed': vp.is_completed,
            'watch_percentage': vp.watch_percentage,
            'completion_mode': vp.completion_mode
        })


class VideoManualConfirmView(views.APIView):
    """
    Allows a student to confirm they have watched the YouTube video.
    Serves as an authoritative fallback for cross-origin or restricted embedded players.
    Requires that the student has initiated playback (started_at exists).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, video_id=None):
        v_id = video_id or request.data.get('video_id')
        if not v_id:
            return Response({'error': 'video_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            video = VideoResource.objects.select_related('module', 'module__course').get(id=v_id)
        except VideoResource.DoesNotExist:
            return Response({'error': 'Video resource not found'}, status=status.HTTP_404_NOT_FOUND)

        enrollment, _ = Enrollment.objects.get_or_create(
            student=request.user,
            course=video.module.course,
            defaults={'is_demo': getattr(request.user, 'is_demo', False)}
        )

        vp, _ = VideoProgress.objects.get_or_create(
            enrollment=enrollment,
            video=video
        )

        vp.confirm_manual_complete()

        mod_prog, _ = ModuleProgress.objects.get_or_create(enrollment=enrollment, module=video.module)
        is_module_done = mod_prog.check_and_update_completion()
        new_course_percent = enrollment.update_progress()

        return Response({
            'video_id': video.id,
            'is_completed': vp.is_completed,
            'completion_mode': vp.completion_mode,
            'watch_percentage': vp.watch_percentage,
            'module_completed': is_module_done,
            'course_progress': new_course_percent
        })


class ReportUnavailableVideoView(views.APIView):
    """
    Allows a student to report a broken, deleted, or unavailable YouTube video.
    Increments report counters and flags video for faculty review.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, video_id=None):
        v_id = video_id or request.data.get('video_id')
        issue_type = request.data.get('issue_type', 'UNAVAILABLE')
        notes = request.data.get('notes', '')

        if not v_id:
            return Response({'error': 'video_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            video = VideoResource.objects.select_related('module', 'module__course').get(id=v_id)
        except VideoResource.DoesNotExist:
            return Response({'error': 'Video resource not found'}, status=status.HTTP_404_NOT_FOUND)

        issue = ReportedVideoIssue.objects.create(
            video=video,
            student=request.user,
            issue_type=issue_type,
            notes=notes,
            status='OPEN'
        )

        video.unavailable_reported_count += 1
        if video.unavailable_reported_count >= 3:
            video.is_unavailable = True
        video.save(update_fields=['unavailable_reported_count', 'is_unavailable'])

        AuditLog.log_action(
            action='VIDEO_ISSUE_REPORTED',
            resource_type='VideoResource',
            resource_id=video.id,
            user=request.user,
            metadata={
                'issue_type': issue_type,
                'reported_count': video.unavailable_reported_count,
                'is_unavailable': video.is_unavailable
            }
        )

        return Response({
            'message': 'Thank you. The issue has been reported to faculty and course administrators for review.',
            'issue_id': issue.id,
            'reported_count': video.unavailable_reported_count,
            'is_marked_unavailable': video.is_unavailable
        }, status=status.HTTP_201_CREATED)


class LearningAnalyticsView(views.APIView):
    """
    Provides aggregated learning analytics across courses, modules, videos, and materials.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        enrollments = Enrollment.objects.filter(student=request.user)
        total_enrolled = enrollments.count()
        completed_courses = enrollments.filter(is_completed=True).count()

        total_mod_done = ModuleProgress.objects.filter(enrollment__student=request.user, is_completed=True).count()
        total_videos_done = VideoProgress.objects.filter(enrollment__student=request.user, is_completed=True).count()
        total_materials_done = MaterialProgress.objects.filter(enrollment__student=request.user, is_completed=True).count()
        total_practices_done = PracticeProgress.objects.filter(enrollment__student=request.user, is_completed=True).count()

        avg_progress = 0.0
        if total_enrolled > 0:
            avg_progress = round(sum(e.progress_percent for e in enrollments) / total_enrolled, 1)

        return Response({
            'total_enrolled_courses': total_enrolled,
            'completed_courses': completed_courses,
            'average_progress': avg_progress,
            'modules_completed': total_mod_done,
            'videos_watched': total_videos_done,
            'study_materials_completed': total_materials_done,
            'practices_passed': total_practices_done
        })
