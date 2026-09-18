import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fx_skillhub.settings')
django.setup()

from catalogue.models import Course, Module, Lesson, VideoResource, StudyMaterial, PracticeTask
from authentication.models import User
from learning.models import Enrollment, ModuleProgress, MaterialProgress, PracticeProgress, VideoProgress
from learning.services import calculate_course_progress, is_assessment_eligible

student = User.objects.filter(first_name__icontains='Ganesh').first() or User.objects.filter(username__icontains='ganesh').first()
print('Student:', student.id, student.email, student.get_full_name())

course = Course.objects.filter(title__icontains='C programming').first()
print('Course:', course.id, course.title, course.slug)

print('Modules in course:', course.modules.count())
for m in course.modules.all():
    print(f"Module {m.id}: {m.title}")
    print(f"  direct vids: {m.videos.count()}, mats: {m.materials.count()}, pracs: {m.practice_tasks.count()}")
    for l in m.lessons.all():
        print(f"  Lesson {l.id}: {l.title} (req_vid={l.requires_video}, req_mat={l.requires_notes}, req_prac={l.requires_practice})")
        print(f"    vids: {list(l.videos.values('id', 'title', 'is_required'))}")
        print(f"    mats: {list(l.materials.values('id', 'title', 'is_required'))}")
        print(f"    pracs: {list(l.practice_tasks.values('id', 'title', 'is_required'))}")

enr = Enrollment.objects.filter(student=student, course=course).first()
print('Enrollment:', enr.id if enr else None)
if enr:
    print('Module Progress:', list(enr.module_progress.values('module_id', 'is_completed')))
    print('Material Progress:', list(enr.material_progress.values('material_id', 'is_completed')))
    print('Practice Progress:', list(enr.practice_progress.values('practice_id', 'is_completed')))
    print('Video Progress:', list(enr.video_progress.values('video_id', 'is_completed')))

progress = calculate_course_progress(student.id, course.id)
print('calculate_course_progress:')
import pprint
pprint.pprint(progress)

elig = is_assessment_eligible(student.id, course.id)
print('is_assessment_eligible:')
pprint.pprint(elig)
