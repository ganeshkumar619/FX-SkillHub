import sys
from django.core.management.base import BaseCommand
from assessments.models import Question, QuestionOption
from catalogue.models import PracticeTask

class Command(BaseCommand):
    help = 'Audits question database for answer key integrity, detects corrupted keys, and flags invalid questions as QUESTION_REQUIRES_REVIEW.'

    def handle(self, *args, **options):
        self.stdout.write("==================================================")
        self.stdout.write("QUIZ DATA INTEGRITY AUDIT — FX SKILLHUB")
        self.stdout.write("==================================================\n")

        # 1. Audit assessments.Question
        total_questions = Question.objects.count()
        self.stdout.write(f"Auditing {total_questions} assessment questions in database...\n")

        valid_count = 0
        invalid_questions = []

        for q in Question.objects.prefetch_related('options').all():
            options = list(q.options.all())
            correct_opts = [opt for opt in options if opt.is_correct]
            correct_count = len(correct_opts)
            num_options = len(options)

            is_valid = True
            issue = None

            if num_options == 0:
                is_valid = False
                issue = "No options attached to question"
            elif q.question_type == 'SINGLE_CHOICE':
                if correct_count == 0:
                    is_valid = False
                    issue = "0 correct options (missing answer key)"
                elif correct_count > 1:
                    is_valid = False
                    issue = f"{correct_count} correct options found for single-choice MCQ"
            elif q.question_type == 'MULTIPLE_CHOICE':
                if correct_count == 0:
                    is_valid = False
                    issue = "0 correct options for multiple-choice question"

            if not is_valid:
                q.status = 'QUESTION_REQUIRES_REVIEW'
                q.save(update_fields=['status'])
                invalid_questions.append({
                    'id': q.id,
                    'text': q.text[:70],
                    'type': q.question_type,
                    'options_count': num_options,
                    'correct_count': correct_count,
                    'correct_options': [opt.text for opt in correct_opts],
                    'issue': issue,
                    'status': q.status
                })
            else:
                if q.status != 'ACTIVE':
                    q.status = 'ACTIVE'
                    q.save(update_fields=['status'])
                valid_count += 1

        self.stdout.write(f"Assessment Questions Audit Result:")
        self.stdout.write(f"  Total Audited: {total_questions}")
        self.stdout.write(f"  Valid Active Questions: {valid_count}")
        self.stdout.write(f"  Corrupted/Invalid Questions: {len(invalid_questions)}\n")

        if invalid_questions:
            self.stdout.write("--- INVALID QUESTIONS REPORT ---")
            for item in invalid_questions:
                self.stdout.write(
                    f"  [QUESTION_ID: {item['id']}] [{item['type']}] Status: {item['status']}\n"
                    f"    Issue: {item['issue']}\n"
                    f"    Text: {item['text']}...\n"
                    f"    Correct Count: {item['correct_count']} -> {item['correct_options']}\n"
                )
        else:
            self.stdout.write("[OK] 100% of assessment questions in database have valid, single-source-of-truth answer keys.\n")

        # 2. Audit catalogue.PracticeTask questions
        self.stdout.write("Auditing practice tasks JSON question content...")
        practice_tasks = PracticeTask.objects.all()
        practice_total_questions = 0
        practice_issues = []

        for pt in practice_tasks:
            content = pt.content or {}
            questions = content.get('questions', [])
            if not questions:
                continue

            for idx, q in enumerate(questions):
                practice_total_questions += 1
                q_id = q.get('id', idx)
                correct_opt = q.get('correct_option')
                correct_ans = q.get('correct_answer')
                opts = q.get('options', [])

                if correct_opt is None and correct_ans is None:
                    practice_issues.append({
                        'practice_task_id': pt.id,
                        'practice_title': pt.title,
                        'question_id': q_id,
                        'issue': 'Missing correct_option and correct_answer'
                    })
                else:
                    resolved_key = correct_opt if correct_opt is not None else correct_ans
                    if opts and resolved_key not in opts:
                        practice_issues.append({
                            'practice_task_id': pt.id,
                            'practice_title': pt.title,
                            'question_id': q_id,
                            'issue': f"Correct answer '{resolved_key}' not in option list: {opts}"
                        })

        self.stdout.write(f"Practice Tasks Questions Audited: {practice_total_questions}")
        self.stdout.write(f"Practice Tasks Issues: {len(practice_issues)}\n")

        if practice_issues:
            self.stdout.write("--- PRACTICE TASKS ISSUES REPORT ---")
            for issue in practice_issues:
                self.stdout.write(f"  [Task {issue['practice_task_id']} - {issue['practice_title']}] Q: {issue['question_id']} -> {issue['issue']}")
        else:
            self.stdout.write("[OK] All practice task questions have verified answer keys matching available options.\n")

        self.stdout.write("==================================================")
        self.stdout.write("AUDIT COMPLETE -- NO QUIZ DATA DELETED")
        self.stdout.write("==================================================")
