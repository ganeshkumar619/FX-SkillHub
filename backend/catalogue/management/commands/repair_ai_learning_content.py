import re
from typing import Dict, Any, List
from django.core.management.base import BaseCommand
from django.db import transaction
from catalogue.models import Course, Module, StudyMaterial, Lesson
from catalogue.common_mistakes_service import CommonMistakesService


class Command(BaseCommand):
    help = "Audit and repair all common mistakes and best practice learning content across all courses and modules."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run audit and print repairs without committing changes to database.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-generation and alignment of all common mistakes across all modules.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        mode_str = "[DRY RUN] " if dry_run else ""
        if force:
            mode_str += "[FORCE REPAIR] "
        self.stdout.write(self.style.NOTICE(f"{mode_str}Starting comprehensive audit and repair of Common Mistakes & Best Practice Fixes..."))

        total_courses = Course.objects.count()
        total_modules = Module.objects.count()
        materials = StudyMaterial.objects.select_related('module__course__skill').all()
        lessons = Lesson.objects.select_related('module__course__skill').all()

        material_repairs = 0
        lesson_repairs = 0
        items_repaired_count = 0
        validation_failures = 0

        self.stdout.write(f"Auditing {total_courses} courses, {total_modules} modules, {materials.count()} study materials, {lessons.count()} lessons...\n")

        with transaction.atomic():
            # 1. Audit & Repair StudyMaterial records
            for sm in materials:
                mod_title = sm.module.title if sm.module else (sm.title or "General Topic")
                skill_name = sm.module.course.skill.name if (sm.module and sm.module.course and sm.module.course.skill) else ""
                
                sc = sm.structured_content
                if not isinstance(sc, dict):
                    sc = {}

                raw_cms = sc.get('common_mistakes', [])
                if not isinstance(raw_cms, list):
                    raw_cms = []

                # Determine if repair is required
                needs_repair = False
                if force:
                    needs_repair = True
                    repaired_cms = CommonMistakesService.generate_topic_common_mistakes(mod_title, skill_name)
                elif len(raw_cms) < 3:
                    needs_repair = True
                else:
                    for item in raw_cms:
                        if not isinstance(item, dict):
                            needs_repair = True
                            break
                        sol = (item.get('recommended_solution') or item.get('correct') or '').strip()
                        rat = (item.get('technical_rationale') or item.get('reason') or '').strip()
                        if not sol or not rat or sol.startswith('#') or sol.startswith('//') or "always assert preconditions" in rat.lower():
                            needs_repair = True
                            break

                if needs_repair:
                    if not force:
                        repaired_cms = CommonMistakesService.repair_or_complete_common_mistakes(
                            raw_cms,
                            topic_title=mod_title,
                            skill_name=skill_name
                        )

                    is_valid, errs = CommonMistakesService.validate_common_mistakes(repaired_cms)
                    if not is_valid:
                        self.stdout.write(self.style.ERROR(f"Validation failure on Material #{sm.id} ({mod_title}): {errs}"))
                        validation_failures += 1
                        continue

                    items_repaired_count += len(repaired_cms)
                    material_repairs += 1

                    if not dry_run:
                        sc['common_mistakes'] = repaired_cms
                        sm.structured_content = sc

                        # Recompile / update Section 6 in text_content if present
                        if sm.text_content:
                            # Check if section 6 exists in markdown
                            sec6_pattern = re.compile(
                                r"(## 6\. (?:Common (?:Mistakes & Engineering Pitfalls|Pitfalls & Anti-Patterns)).*?)(?=\n## 7\.|\Z)",
                                re.DOTALL | re.IGNORECASE
                            )
                            formatted_sec6 = "## 6. Common Pitfalls & Anti-Patterns\n" + "\n\n".join([
                                f"❌ **Common Pitfall:** {cm.get('common_pitfall', cm.get('mistake'))}\n"
                                f"✅ **Recommended Solution:** {cm.get('recommended_solution', cm.get('correct'))}\n"
                                f"💡 **Technical Rationale:** {cm.get('technical_rationale', cm.get('reason'))}"
                                for cm in repaired_cms
                            ])
                            if sec6_pattern.search(sm.text_content):
                                sm.text_content = sec6_pattern.sub(formatted_sec6 + "\n\n", sm.text_content)
                            else:
                                sm.text_content += f"\n\n{formatted_sec6}\n"

                        sm.save()

            # 2. Audit & Repair Lesson records
            for lsn in lessons:
                mod_title = lsn.module.title if lsn.module else (lsn.title or "General Topic")
                skill_name = lsn.module.course.skill.name if (lsn.module and lsn.module.course and lsn.module.course.skill) else ""
                
                raw_cms = lsn.common_mistakes
                if not isinstance(raw_cms, list):
                    raw_cms = []

                # Determine if repair is required
                needs_repair = False
                if force:
                    needs_repair = True
                    repaired_cms = CommonMistakesService.generate_topic_common_mistakes(lsn.title or mod_title, skill_name)
                elif len(raw_cms) < 3:
                    needs_repair = True
                else:
                    for item in raw_cms:
                        if not isinstance(item, dict):
                            needs_repair = True
                            break
                        sol = (item.get('recommended_solution') or item.get('correct') or '').strip()
                        rat = (item.get('technical_rationale') or item.get('reason') or '').strip()
                        if not sol or not rat or sol.startswith('#') or sol.startswith('//') or "always assert preconditions" in rat.lower():
                            needs_repair = True
                            break

                if needs_repair:
                    if not force:
                        repaired_cms = CommonMistakesService.repair_or_complete_common_mistakes(
                            raw_cms,
                            topic_title=lsn.title or mod_title,
                            skill_name=skill_name
                        )

                    is_valid, errs = CommonMistakesService.validate_common_mistakes(repaired_cms)
                    if not is_valid:
                        self.stdout.write(self.style.ERROR(f"Validation failure on Lesson #{lsn.id} ({lsn.title}): {errs}"))
                        validation_failures += 1
                        continue

                    lesson_repairs += 1
                    items_repaired_count += len(repaired_cms)

                    if not dry_run:
                        lsn.common_mistakes = repaired_cms
                        lsn.save(update_fields=['common_mistakes'])

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("AUDIT & REPAIR COMPLETION REPORT"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total Courses Audited:          {total_courses}")
        self.stdout.write(f"Total Modules Audited:          {total_modules}")
        self.stdout.write(f"Study Materials Audited:        {materials.count()}")
        self.stdout.write(f"Study Materials Repaired:       {material_repairs}")
        self.stdout.write(f"Lessons Audited:                {lessons.count()}")
        self.stdout.write(f"Lessons Repaired:               {lesson_repairs}")
        self.stdout.write(f"Total Mistake Items Repaired:   {items_repaired_count}")
        self.stdout.write(f"Validation Failures:            {validation_failures}")
        self.stdout.write(f"Status:                         {'SUCCESS' if validation_failures == 0 else 'PARTIAL'}")
        self.stdout.write("=" * 60 + "\n")
