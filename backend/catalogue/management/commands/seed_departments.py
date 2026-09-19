from django.core.management.base import BaseCommand
from django.utils import timezone
from catalogue.models import Department

class Command(BaseCommand):
    help = 'Seeds or updates the 10 official institutional departments for Francis Xavier Engineering College (FXEC)'

    def handle(self, *args, **options):
        now = timezone.now()
        departments_data = [
            {'code': 'CSE', 'name': 'Computer Science and Engineering', 'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.'},
            {'code': 'ECE', 'name': 'Electronics and Communication Engineering', 'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.'},
            {'code': 'EEE', 'name': 'Electrical and Electronics Engineering', 'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.'},
            {'code': 'MECH', 'name': 'Mechanical Engineering', 'description': 'NBA Accredited UG Programme.'},
            {'code': 'CIVIL', 'name': 'Civil Engineering', 'description': 'UG Programme in Civil Engineering.'},
            {'code': 'IT', 'name': 'Information Technology', 'description': 'Permanently affiliated UG Programme by Anna University.'},
            {'code': 'AIDS', 'name': 'Artificial Intelligence & Data Science', 'description': 'UG Programme specializing in Modern AI and Data Science technologies.'},
            {'code': 'CSBS', 'name': 'Computer Science and Business System', 'description': 'UG Programme blending CS and enterprise business systems.'},
            {'code': 'MBA', 'name': 'Master of Business Administration', 'description': 'Autonomous PG Programme rated Top B-School.'},
            {'code': 'MCA', 'name': 'Master of Computer Application', 'description': 'Autonomous PG Programme in computer applications.'},
        ]

        created_count = 0
        updated_count = 0

        for d in departments_data:
            dept, created = Department.objects.update_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'],
                    'description': d['description'],
                    'is_active': True,
                    'source_type': 'FXEC_OFFICIAL',
                    'source_url': 'https://www.francisxavier.ac.in/departments',
                    'source_title': 'Departments | Francis Xavier Engineering College',
                    'source_accessed_at': now,
                    'last_verified_at': now,
                    'content_status': 'PUBLISHED',
                    'approval_status': 'APPROVED'
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded departments: {created_count} created, {updated_count} updated. Total active: {Department.objects.filter(is_active=True).count()}'
            )
        )
