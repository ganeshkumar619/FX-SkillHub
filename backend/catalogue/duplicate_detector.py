import re
from typing import Dict, Any, Optional
from .models import Skill


def normalize_title(text: str) -> str:
    """Removes punctuation and extra spaces, lowercases for robust token comparison."""
    if not text:
        return ""
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', text).strip().lower()
    return re.sub(r'\s+', ' ', clean)


def check_skill_duplicate(
    name: str,
    category_id: Optional[int] = None,
    exclude_skill_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluates whether a proposed skill name or concept already exists in the catalogue.
    Checks:
    1. Exact case-insensitive match
    2. Normalized alphanumeric match
    3. Token overlap / substring match (e.g. 'Python Programming' vs 'Python')
    """
    if not name or not name.strip():
        return {'is_duplicate': False, 'matches': []}

    target_norm = normalize_title(name)
    target_tokens = set(target_norm.split())

    qs = Skill.objects.all()
    if exclude_skill_id:
        qs = qs.exclude(id=exclude_skill_id)

    matches = []

    for existing in qs.select_related('category', 'domain', 'department'):
        existing_norm = normalize_title(existing.name)
        existing_tokens = set(existing_norm.split())

        # 1. Exact Match
        if existing_norm == target_norm:
            matches.append({
                'skill_id': existing.id,
                'name': existing.name,
                'category': existing.category.name if existing.category else None,
                'domain': existing.domain.name if existing.domain else None,
                'level': existing.level,
                'source_type': existing.source_type,
                'approval_status': existing.approval_status,
                'match_type': 'EXACT',
                'confidence': 1.0,
                'similarity_reason': f"A skill with the exact name '{existing.name}' is already registered in '{existing.category.name if existing.category else 'General'}'.",
                'suggested_action': 'MERGE_OR_USE_EXISTING'
            })
            continue

        # 2. Substring / Containment Match
        if (target_norm in existing_norm or existing_norm in target_norm) and min(len(target_norm), len(existing_norm)) > 3:
            matches.append({
                'skill_id': existing.id,
                'name': existing.name,
                'category': existing.category.name if existing.category else None,
                'domain': existing.domain.name if existing.domain else None,
                'level': existing.level,
                'source_type': existing.source_type,
                'approval_status': existing.approval_status,
                'match_type': 'SUBSTRING',
                'confidence': 0.85,
                'similarity_reason': f"Skill '{name}' shares significant naming overlap with existing skill '{existing.name}' ({existing.category.name if existing.category else 'General'}).",
                'suggested_action': 'REVIEW_BEFORE_CREATION'
            })
            continue

        # 3. Jaccard Token Overlap
        if target_tokens and existing_tokens:
            intersection = target_tokens.intersection(existing_tokens)
            union = target_tokens.union(existing_tokens)
            jaccard = len(intersection) / len(union) if union else 0
            if jaccard >= 0.5:
                matches.append({
                    'skill_id': existing.id,
                    'name': existing.name,
                    'category': existing.category.name if existing.category else None,
                    'domain': existing.domain.name if existing.domain else None,
                    'level': existing.level,
                    'source_type': existing.source_type,
                    'approval_status': existing.approval_status,
                    'match_type': 'TOKEN_SIMILARITY',
                    'confidence': round(jaccard, 2),
                    'similarity_reason': f"Shared keyword overlap ({', '.join(intersection)}) with existing skill '{existing.name}'.",
                    'suggested_action': 'REVIEW_BEFORE_CREATION'
                })

    is_duplicate = len(matches) > 0
    return {
        'is_duplicate': is_duplicate,
        'has_exact_match': any(m['match_type'] == 'EXACT' for m in matches),
        'matches': sorted(matches, key=lambda x: x['confidence'], reverse=True)
    }
