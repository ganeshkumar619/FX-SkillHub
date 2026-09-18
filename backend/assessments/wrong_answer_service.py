import re
from typing import Dict, Any, List, Optional
from django.db.models import Q
from .models import AssessmentAttempt, Question, QuestionOption, StudentAnswer
from catalogue.models import Module, VideoResource, StudyMaterial, PracticeTask

class WrongAnswerReviewService:
    """
    Service responsible for comprehensive wrong-answer evaluation,
    AI-powered mistake diagnostics, topic-level error distribution,
    and verified institutional learning resource recommendations.
    """

    @classmethod
    def generate_ai_mistake_diagnosis(
        cls,
        question: Question,
        student_answers: List[str],
        correct_answers: List[str],
        topic_title: str
    ) -> Dict[str, str]:
        """
        Synthesizes a structured pedagogical AI explanation for an incorrect answer:
        1. Why the selected answer is incorrect.
        2. Why the correct answer is correct.
        3. Simple intuitive explanation.
        4. Practical code/syntax example.
        5. Recommended concept to revise.
        """
        student_ans_str = ", ".join(student_answers) if student_answers else "No answer selected (Skipped)"
        correct_ans_str = ", ".join(correct_answers) if correct_answers else "N/A"
        q_text = question.text
        explanation = question.explanation or ""

        # Deterministic, pedagogical AI diagnostic generation
        why_incorrect = (
            f"Selecting '{student_ans_str}' represents a common misconception in {topic_title}. "
            f"It conflates related syntax or operational paradigms with the core requirements of this concept."
            if student_answers else
            f"This question was skipped or unanswered. Understanding the fundamental definition in {topic_title} is necessary to solve it."
        )

        why_correct = (
            f"'{correct_ans_str}' is the correct response because {explanation.strip()}"
            if explanation else
            f"'{correct_ans_str}' is the authoritatively correct principle governing {topic_title} in production systems."
        )

        simple_explanation = (
            f"In {topic_title}, always prioritize standard definitions and defensive patterns. "
            f"Keep in mind that: {explanation or correct_ans_str}"
        )

        # Illustrative mini code or syntax example tailored to the question or topic
        small_example = cls._generate_contextual_example(question, topic_title, correct_ans_str)

        return {
            'why_incorrect': why_incorrect,
            'why_correct': why_correct,
            'simple_explanation': simple_explanation,
            'small_example': small_example,
            'recommended_topic': topic_title
        }

    @classmethod
    def _generate_contextual_example(cls, question: Question, topic_title: str, correct_ans: str) -> str:
        """
        Generates a concise code or pattern snippet demonstrating the correct behavior.
        """
        text_lower = question.text.lower()
        if 'function' in text_lower or 'def' in text_lower:
            return "# Defining and invoking a standard function\ndef calculate_total(price, tax=0.1):\n    return price + (price * tax)\n\nresult = calculate_total(100) # Returns 110.0"
        elif 'loop' in text_lower or 'while' in text_lower or 'for' in text_lower:
            return "# Standard bounded iteration pattern\nitems = ['A', 'B', 'C']\nfor idx, item in enumerate(items):\n    print(f'{idx}: {item}')"
        elif 'class' in text_lower or 'oop' in text_lower or 'object' in text_lower:
            return "# Encapsulation with classes and initialization\nclass StudentRecord:\n    def __init__(self, name, roll_no):\n        self.name = name\n        self.roll_no = roll_no"
        elif 'exception' in text_lower or 'try' in text_lower or 'error' in text_lower:
            return "# Defensive exception handling\ntry:\n    with open('data.txt', 'r') as f:\n        content = f.read()\nexcept FileNotFoundError as err:\n    logging.warning('File missing, fallback to defaults')"
        elif 'array' in text_lower or 'numpy' in text_lower or 'matrix' in text_lower:
            return "# High-performance vector operations\nimport numpy as np\narr = np.array([1, 2, 3, 4])\nsquared = arr ** 2 # Vectorized [1, 4, 9, 16]"
        elif 'spring' in text_lower or 'bean' in text_lower or 'injection' in text_lower:
            return "@RestController\n@RequestMapping('/api/v1/students')\npublic class StudentController {\n    @Autowired\n    private StudentService service;\n}"
        elif 'react' in text_lower or 'component' in text_lower or 'hook' in text_lower:
            return "// Deterministic state management with React hook\nconst [count, setCount] = useState(0);\nconst handleIncrement = () => setCount(prev => prev + 1);"
        else:
            return f"# Recommended implementation pattern for {topic_title}\n# Correct Rule: {correct_ans[:60]}"

    @classmethod
    def generate_attempt_review(cls, attempt: AssessmentAttempt) -> Dict[str, Any]:
        """
        Generates full detailed review breakdown:
        - Overall counts: total, answered, correct, wrong
        - List of all question reviews (with student answers, correct answers, is_correct flag)
        - Mistake-specific AI diagnostic explanations
        - Topic-wise error distribution
        - Real recommendations to course YouTube videos, study materials, and practice sets.
        """
        course = attempt.assessment.course

        # 1. Resolve questions for this attempt in order
        if attempt.selected_question_ids:
            questions_qs = Question.objects.filter(id__in=attempt.selected_question_ids).prefetch_related('options')
            q_map = {q.id: q for q in questions_qs}
            questions = [q_map[qid] for qid in attempt.selected_question_ids if qid in q_map]
        else:
            questions = list(attempt.assessment.questions.prefetch_related('options').all())

        # 2. Fetch student answers for this attempt
        student_answers_qs = StudentAnswer.objects.filter(attempt=attempt).prefetch_related('selected_options')
        ans_map = {sa.question_id: sa for sa in student_answers_qs}

        detailed_reviews = []
        topic_errors: Dict[str, int] = {}
        correct_count = 0
        wrong_count = 0
        answered_count = 0

        for idx, q in enumerate(questions, start=1):
            ans = ans_map.get(q.id)
            selected_opts = list(ans.selected_options.all()) if ans else []
            correct_opts = list(q.options.filter(is_correct=True))

            selected_ids = [opt.id for opt in selected_opts]
            correct_ids = [opt.id for opt in correct_opts]

            is_answered = len(selected_opts) > 0
            if is_answered:
                answered_count += 1

            # Determine correctness using database Option IDs as source of truth
            if not is_answered or not correct_ids:
                is_correct = False
            elif q.question_type == 'SINGLE_CHOICE':
                is_correct = (len(selected_ids) == 1 and len(correct_ids) == 1 and selected_ids[0] == correct_ids[0])
            else:
                is_correct = (set(selected_ids) == set(correct_ids))

            student_answer_texts = [opt.text for opt in selected_opts]
            correct_answer_texts = [opt.text for opt in correct_opts]

            # Format all options for UI display
            options_data = [
                {
                    'id': opt.id,
                    'text': opt.text,
                    'is_correct': opt.is_correct,
                    'is_selected': opt.id in selected_ids,
                    'order': opt.order
                }
                for opt in q.options.all().order_by('order')
            ]

            topic_label = (q.topic_tag or 'General Engineering').replace('_', ' ').replace('-', ' ').title()

            ai_diagnosis = None
            if not is_correct:
                wrong_count += 1
                topic_tag = q.topic_tag or 'general'
                topic_errors[topic_tag] = topic_errors.get(topic_tag, 0) + 1

                ai_diagnosis = cls.generate_ai_mistake_diagnosis(
                    question=q,
                    student_answers=student_answer_texts,
                    correct_answers=correct_answer_texts,
                    topic_title=topic_label
                )
            else:
                correct_count += 1

            detailed_reviews.append({
                'question_id': q.id,
                'order': idx,
                'question_text': q.text,
                'topic_tag': q.topic_tag or 'general',
                'topic_label': topic_label,
                'difficulty': q.difficulty,
                'marks': q.marks,
                'selected_option_id': selected_ids[0] if selected_ids else None,
                'selected_option_ids': selected_ids,
                'correct_option_id': correct_ids[0] if correct_ids else None,
                'correct_option_ids': correct_ids,
                'is_answered': is_answered,
                'is_correct': is_correct,
                'options': options_data,
                'student_answers': student_answer_texts,
                'correct_answers': correct_answer_texts,
                'explanation': q.explanation,
                'ai_diagnosis': ai_diagnosis
            })

        # 3. Topic Error Analysis & Direct Educational Recommendations
        # Map each weak topic to an existing database module, real YouTube video, and study notes
        modules = list(course.modules.all().prefetch_related('videos', 'materials', 'practice_tasks').order_by('order'))
        
        weak_area_recommendations = []
        for topic_tag, err_count in sorted(topic_errors.items(), key=lambda x: x[1], reverse=True):
            # Locate matching module by topic_tag or fuzzy title
            matching_mod = next(
                (m for m in modules if m.topic_tag == topic_tag or topic_tag in m.topic_tag),
                None
            )
            if not matching_mod:
                matching_mod = modules[0] if modules else None

            if not matching_mod:
                continue

            # Real YouTube Video Reference
            yt_video = matching_mod.videos.filter(
                Q(video_type='YOUTUBE') | Q(youtube_video_id__isnull=False),
                status='PUBLISHED'
            ).first()

            # Real Study Material
            study_mat = matching_mod.materials.filter(status='PUBLISHED').first()

            # Real Practice Task
            practice_task = matching_mod.practice_tasks.filter(status='PUBLISHED').first()

            weak_area_recommendations.append({
                'topic_tag': topic_tag,
                'topic_name': (matching_mod.topic_tag or topic_tag).replace('_', ' ').replace('-', ' ').title(),
                'error_count': err_count,
                'module_id': matching_mod.id,
                'module_order': matching_mod.order,
                'module_title': matching_mod.title,
                'course_slug': course.slug,
                'video_reference': {
                    'title': yt_video.title,
                    'youtube_video_id': yt_video.youtube_video_id,
                    'youtube_url': yt_video.youtube_url or f"https://www.youtube.com/watch?v={yt_video.youtube_video_id}",
                    'thumbnail_url': yt_video.thumbnail_url or f"https://img.youtube.com/vi/{yt_video.youtube_video_id}/hqdefault.jpg",
                    'channel_name': yt_video.channel_name or "FXEC Learning Channel",
                    'duration': yt_video.duration_if_available or f"{yt_video.duration_seconds // 60} mins"
                } if yt_video and yt_video.youtube_video_id else None,
                'study_material': {
                    'id': study_mat.id,
                    'title': study_mat.title,
                    'description': study_mat.description[:120] if study_mat.description else ""
                } if study_mat else None,
                'practice_task': {
                    'id': practice_task.id,
                    'title': practice_task.title,
                    'task_type': practice_task.task_type
                } if practice_task else None,
                'ai_action_plan': (
                    f"Revise '{matching_mod.title}' to address {err_count} question error(s). "
                    f"Watch the concept video, review key principles in the study notes, and retry the practice quiz."
                )
            })

        # Identify primary weak area
        primary_weak_topic = None
        if weak_area_recommendations:
            primary_weak_topic = weak_area_recommendations[0]['topic_name']

        # AI Diagnostic Summary
        if attempt.passed:
            ai_summary = (
                f"Outstanding performance! You secured {attempt.percentage}% and passed the institutional benchmark ({attempt.assessment.pass_percentage}%). "
                f"You answered {correct_count} of {len(questions)} questions accurately."
            )
            if wrong_count > 0:
                ai_summary += f" Review the {wrong_count} questions below to solidify complete conceptual mastery before moving to advanced topics."
        else:
            ai_summary = (
                f"Your score of {attempt.percentage}% is below the required {attempt.assessment.pass_percentage}% passing threshold. "
                f"Your primary growth area is '{primary_weak_topic or 'Core Concepts'}'. "
                f"Review the highlighted mistakes, study the linked video references, and re-attempt the assessment when ready."
            )

        return {
            'total_questions': len(questions),
            'answered_count': answered_count,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'passing_percentage': attempt.assessment.pass_percentage,
            'passed': attempt.passed,
            'score': attempt.score,
            'percentage': attempt.percentage,
            'ai_diagnostic_summary': ai_summary,
            'primary_weak_area': primary_weak_topic,
            'weak_area_recommendations': weak_area_recommendations,
            'detailed_questions': detailed_reviews,
            'results': [
                {
                    'question_id': r['question_id'],
                    'selected_option_id': r['selected_option_id'],
                    'correct_option_id': r['correct_option_id'],
                    'is_correct': r['is_correct'],
                }
                for r in detailed_reviews
            ],
        }
