from catalogue.models import Module

class SkillGapService:
    @staticmethod
    def analyze_skill_gap(attempt):
        """
        Analyzes topic mastery from a completed pre-assessment attempt
        and maps weak topics (< 70%) to active database course modules.
        """
        topic_breakdown = attempt.topic_breakdown or {}
        weak_topics = []
        strong_topics = []

        for topic, pct in topic_breakdown.items():
            if pct < 70.0:
                weak_topics.append({
                    'topic_tag': topic,
                    'mastery_percent': pct,
                    'status': 'NEEDS_FOCUS'
                })
            else:
                strong_topics.append({
                    'topic_tag': topic,
                    'mastery_percent': pct,
                    'status': 'PROFICIENT'
                })

        # Query database modules matching weak topic tags
        weak_tags = [w['topic_tag'] for w in weak_topics]
        recommended_modules = Module.objects.filter(
            course=attempt.assessment.course,
            topic_tag__in=weak_tags
        ).order_by('order')

        recommendations = []
        for mod in recommended_modules:
            score_entry = next((w for w in weak_topics if w['topic_tag'] == mod.topic_tag), None)
            mastery = score_entry['mastery_percent'] if score_entry else 0.0
            recommendations.append({
                'module_id': mod.id,
                'order': mod.order,
                'title': mod.title,
                'topic_tag': mod.topic_tag,
                'duration_minutes': mod.duration_minutes,
                'reason': f"Diagnostic mastery in '{mod.topic_tag.replace('_', ' ').title()}' is {mastery}% (below institutional 70% threshold).",
                'priority': 'HIGH' if mastery < 50.0 else 'MEDIUM'
            })

        # Structured diagnostic diagnosis
        summary_text = (
            f"Based on your diagnostic pre-assessment for '{attempt.assessment.course.title}', "
            f"you demonstrated proficiency in {len(strong_topics)} topic area(s) and need reinforcement in "
            f"{len(weak_topics)} foundational module(s). Follow the tailored roadmap below before final certification."
        )

        return {
            'course_title': attempt.assessment.course.title,
            'overall_diagnostic_percentage': attempt.percentage,
            'topic_breakdown': topic_breakdown,
            'weak_topics': weak_topics,
            'strong_topics': strong_topics,
            'recommended_modules': recommendations,
            'diagnostic_summary': summary_text,
            'ai_engine': 'FXEC Deterministic Skill-Diagnostic Engine v1.0',
        }
