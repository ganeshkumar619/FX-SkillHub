from django.db import migrations
from django.utils import timezone

def seed_departments(apps, schema_editor):
    Department = apps.get_model('catalogue', 'Department')
    now = timezone.now()

    departments = [
        {
            'code': 'CSE',
            'name': 'Computer Science and Engineering',
            'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.',
            'is_active': True,
        },
        {
            'code': 'ECE',
            'name': 'Electronics and Communication Engineering',
            'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.',
            'is_active': True,
        },
        {
            'code': 'EEE',
            'name': 'Electrical and Electronics Engineering',
            'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.',
            'is_active': True,
        },
        {
            'code': 'MECH',
            'name': 'Mechanical Engineering',
            'description': 'NBA Accredited UG Programme.',
            'is_active': True,
        },
        {
            'code': 'CIVIL',
            'name': 'Civil Engineering',
            'description': 'UG Programme in Civil Engineering.',
            'is_active': True,
        },
        {
            'code': 'IT',
            'name': 'Information Technology',
            'description': 'Permanently affiliated UG Programme by Anna University.',
            'is_active': True,
        },
        {
            'code': 'AIDS',
            'name': 'Artificial Intelligence & Data Science',
            'description': 'UG Programme specializing in Modern AI and Data Science technologies.',
            'is_active': True,
        },
        {
            'code': 'CSBS',
            'name': 'Computer Science and Business System',
            'description': 'UG Programme blending CS and enterprise business systems.',
            'is_active': True,
        },
        {
            'code': 'MBA',
            'name': 'Master of Business Administration',
            'description': 'Autonomous PG Programme rated Top B-School.',
            'is_active': True,
        },
        {
            'code': 'MCA',
            'name': 'Master of Computer Application',
            'description': 'Autonomous PG Programme in computer applications.',
            'is_active': True,
        },
    ]

    for d in departments:
        dept, created = Department.objects.get_or_create(
            code=d['code'],
            defaults={
                'name': d['name'],
                'description': d['description'],
                'is_active': d['is_active'],
                'source_type': 'FXEC_OFFICIAL',
                'source_url': 'https://www.francisxavier.ac.in/departments',
                'source_title': 'Departments | Francis Xavier Engineering College',
                'source_accessed_at': now,
                'last_verified_at': now,
                'content_status': 'PUBLISHED',
                'approval_status': 'APPROVED'
            }
        )
        if not created and not dept.is_active:
            dept.is_active = True
            dept.save(update_fields=['is_active'])

def remove_departments(apps, schema_editor):
    # Reverse migration: no-op to protect existing data
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0008_add_department_is_active_updated_at'),
    ]

    operations = [
        migrations.RunPython(seed_departments, remove_departments),
    ]
