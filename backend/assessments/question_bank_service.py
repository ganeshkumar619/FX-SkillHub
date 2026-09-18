import re
import random
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from django.db.models import Q
from .models import Assessment, Question, QuestionOption


class QuestionBankService:
    """
    Dedicated service for managing AI Question Banks, semantic duplicate detection,
    blueprint-based sampling, and per-attempt question & option randomization.
    """

    STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'were', 'will', 'with', 'which', 'what', 'how', 'when',
        'where', 'why', 'who', 'does', 'do', 'can', 'following'
    }

    @classmethod
    def normalize_tokens(cls, text: str) -> set:
        """
        Strips punctuation, lowercases, and removes common stop words to yield
        a semantic token set.
        """
        if not text:
            return set()
        clean = re.sub(r'[^a-zA-Z0-9\s_]', ' ', text.lower())
        tokens = [t.strip() for t in clean.split() if len(t.strip()) > 1]
        return {t for t in tokens if t not in cls.STOP_WORDS}

    @classmethod
    def compute_semantic_hash(cls, text: str) -> str:
        """
        Computes a deterministic hash of sorted semantic tokens for O(1) duplicate lookup.
        """
        tokens = sorted(list(cls.normalize_tokens(text)))
        token_str = " ".join(tokens)
        return hashlib.sha256(token_str.encode('utf-8')).hexdigest()[:16]

    @classmethod
    def calculate_similarity(cls, text_a: str, text_b: str) -> float:
        """
        Computes Jaccard similarity between two question token sets.
        """
        tokens_a = cls.normalize_tokens(text_a)
        tokens_b = cls.normalize_tokens(text_b)
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / float(len(union))

    @classmethod
    def is_duplicate(cls, course_id: int, text: str, threshold: float = 0.70) -> Tuple[bool, Optional[str]]:
        """
        Checks if a question is semantically identical (> 70% similarity) to any existing question
        in the course question bank or assessment questions.
        """
        candidate_hash = cls.compute_semantic_hash(text)
        
        # 1. Exact token hash match
        exact_match = Question.objects.filter(
            Q(course_id=course_id) | Q(assessment__course_id=course_id),
            semantic_hash=candidate_hash
        ).first()
        if exact_match:
            return True, f"Exact semantic match with question ID {exact_match.id}: '{exact_match.text[:60]}...'"

        # 2. Semantic token overlap match
        existing_questions = Question.objects.filter(
            Q(course_id=course_id) | Q(assessment__course_id=course_id)
        ).only('id', 'text')

        for eq in existing_questions:
            sim = cls.calculate_similarity(text, eq.text)
            if sim >= threshold:
                return True, f"High similarity ({round(sim * 100, 1)}%) with question ID {eq.id}: '{eq.text[:60]}...'"

        return False, None

    @classmethod
    def prepare_attempt_questions(
        cls, 
        assessment: Assessment, 
        randomize_options: bool = True
    ) -> Tuple[List[int], Dict[str, List[int]]]:
        """
        Selects questions from the approved question bank matching the assessment blueprint.
        Randomizes question sequence and option sequence for the specific student attempt.
        Returns:
            (selected_question_ids, question_option_orders_map)
        """
        blueprint = assessment.blueprint or {}
        target_count = blueprint.get('question_count') or assessment.questions.count() or 10
        diff_dist = blueprint.get('difficulty_distribution') or {'EASY': 0.4, 'MEDIUM': 0.5, 'HARD': 0.1}

        # Gather all eligible questions for this assessment (from assessment + course question bank)
        course = assessment.course
        pool_qs = Question.objects.filter(
            Q(assessment=assessment) | (Q(course=course, is_bank_question=True))
        ).distinct().prefetch_related('options')

        all_pool = list(pool_qs)
        if not all_pool:
            return [], {}

        # Categorize by difficulty
        diff_map = {'EASY': [], 'MEDIUM': [], 'HARD': []}
        for q in all_pool:
            d = q.difficulty if q.difficulty in diff_map else 'EASY'
            diff_map[d].append(q)

        # Calculate counts per difficulty according to blueprint
        easy_target = int(round(target_count * diff_dist.get('EASY', 0.4)))
        medium_target = int(round(target_count * diff_dist.get('MEDIUM', 0.5)))
        hard_target = target_count - (easy_target + medium_target)

        selected_questions = []

        def sample_difficulty(category: str, needed: int):
            avail = diff_map[category]
            random.shuffle(avail)
            chosen = avail[:needed]
            selected_questions.extend(chosen)
            diff_map[category] = avail[len(chosen):]
            return needed - len(chosen)

        rem_easy = sample_difficulty('EASY', easy_target)
        rem_med = sample_difficulty('MEDIUM', medium_target)
        rem_hard = sample_difficulty('HARD', hard_target)

        shortfall = rem_easy + rem_med + rem_hard
        if shortfall > 0:
            remaining_pool = [q for q_list in diff_map.values() for q in q_list if q not in selected_questions]
            random.shuffle(remaining_pool)
            selected_questions.extend(remaining_pool[:shortfall])

        if not selected_questions:
            selected_questions = list(all_pool)

        # Shuffle selected questions order for this attempt
        random.shuffle(selected_questions)
        selected_ids = [q.id for q in selected_questions]

        # Randomize options per question for this attempt
        option_orders_map = {}
        for q in selected_questions:
            opt_ids = list(q.options.values_list('id', flat=True))
            if randomize_options:
                random.shuffle(opt_ids)
            option_orders_map[str(q.id)] = opt_ids

        return selected_ids, option_orders_map
