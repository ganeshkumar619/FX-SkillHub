import re
from rest_framework import serializers

ALLOWED_INSTITUTIONAL_DOMAINS = [
    'francisxavier.ac.in',
    'fxec.ac.in',  # Institutional acronym alias for Francis Xavier Engineering College
]

DISALLOWED_EXTERNAL_PATTERNS = [
    'gmail.com',
    'yahoo.com',
    'outlook.com',
    'hotmail.com',
    'protonmail.com',
    'icloud.com',
    'aol.com',
    'mail.com',
]


def normalize_email(email: str) -> str:
    """Lowercases, strips, and cleans email address."""
    if not email:
        return ''
    return email.strip().lower()


def validate_institutional_email(email: str) -> str:
    """
    Validates that the provided email belongs strictly to Francis Xavier Engineering College.
    Rejects generic external domains (@gmail.com, @yahoo.com, etc.) and arbitrary domains.
    Returns normalized lowercase email on success or raises serializers.ValidationError.
    """
    clean_email = normalize_email(email)

    if not clean_email:
        raise serializers.ValidationError("Institutional email is required.")

    # Basic email syntax check
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, clean_email):
        raise serializers.ValidationError("Please provide a valid email address.")

    domain = clean_email.split('@')[-1]

    # Explicit rejection check for common external email providers
    for disallowed in DISALLOWED_EXTERNAL_PATTERNS:
        if domain == disallowed or domain.endswith('.' + disallowed):
            raise serializers.ValidationError(
                f"External email domains (@{domain}) are strictly forbidden. "
                "Please use your official institutional email ending in @francisxavier.ac.in."
            )

    # Enforce institutional domain
    if domain not in ALLOWED_INSTITUTIONAL_DOMAINS and not any(clean_email.endswith('@' + d) for d in ALLOWED_INSTITUTIONAL_DOMAINS):
        raise serializers.ValidationError(
            f"Unauthorized domain '@{domain}'. "
            "Institutional email must end with @francisxavier.ac.in."
        )

    return clean_email
