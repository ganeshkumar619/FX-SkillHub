from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('STUDENT', 'Student'),
        ('FACULTY', 'Faculty'),
        ('MENTOR', 'Mentor / Faculty'),
        ('ADMIN', 'Institutional Administrator'),
    )

    VERIFICATION_STATUS_CHOICES = (
        ('PENDING_EMAIL_VERIFICATION', 'Pending Email Verification'),
        ('VERIFIED', 'Verified / Active'),
        ('BLOCKED', 'Blocked'),
    )

    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default='STUDENT', db_index=True)
    verification_status = models.CharField(
        max_length=32,
        choices=VERIFICATION_STATUS_CHOICES,
        default='VERIFIED',
        db_index=True,
        help_text="Institutional email verification status"
    )
    department = models.ForeignKey('catalogue.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    register_number = models.CharField(max_length=32, blank=True, null=True, help_text="Official college registration / roll number")
    year = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Academic year of study (1-4)")
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_demo = models.BooleanField(default=False, db_index=True, help_text="Designates if this account is a synthetic demo user")
    avatar_url = models.URLField(blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True, help_text="Google OAuth subject identifier (sub)")
    auth_provider = models.CharField(max_length=32, default='LOCAL', help_text="Authentication provider (LOCAL, GOOGLE)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_student(self):
        return self.role == 'STUDENT'

    def is_faculty(self):
        return self.role in ('FACULTY', 'MENTOR') or self.is_superuser

    def is_mentor(self):
        return self.is_faculty()

    def is_admin_user(self):
        return self.role == 'ADMIN' or self.is_superuser

    def is_verified(self):
        return self.verification_status == 'VERIFIED'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()} - {self.verification_status})"


class EmailVerificationOTP(models.Model):
    """
    Time-limited, cryptographically hashed One-Time Password for institutional email verification.
    Plaintext OTPs are NEVER persisted in the database or logged.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_otps', null=True, blank=True)
    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=255, help_text="Cryptographically salted hash of OTP (PBKDF2)")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    attempts_count = models.PositiveIntegerField(default=0, help_text="Number of failed attempts with this OTP")
    max_attempts = models.PositiveIntegerField(default=5)
    resend_count = models.PositiveIntegerField(default=0)
    last_resend_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def has_exceeded_attempts(self):
        return self.attempts_count >= self.max_attempts

    def __str__(self):
        return f"OTP for {self.email} (Expired: {self.is_expired()}, Used: {self.is_used})"


class ApprovedStudentDirectory(models.Model):
    """
    Approved institutional student directory for Francis Xavier Engineering College.
    If populated, student registration validates against official institutional records.
    """
    register_number = models.CharField(max_length=32, unique=True, db_index=True, help_text="Official institutional register / roll number")
    email = models.EmailField(unique=True, db_index=True, help_text="Official institutional student email")
    full_name = models.CharField(max_length=150, blank=True)
    department = models.ForeignKey('catalogue.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_students')
    year = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Year of study (1-4)")
    is_active_student = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Approved Student Directory Entry"
        verbose_name_plural = "Approved Student Directory"
        ordering = ['register_number']

    def __str__(self):
        return f"{self.register_number} - {self.email} ({self.full_name or 'Student'})"


class FacultyInvitation(models.Model):
    """
    Cryptographically secure, time-limited, single-use invitation for newly provisioned faculty.
    The plaintext token is NEVER persisted in the database; only its SHA-256 digest is stored.
    """
    faculty = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField(db_index=True, help_text="Exact faculty email to which invitation was dispatched")
    token_hash = models.CharField(max_length=64, db_index=True, help_text="SHA-256 hash of single-use invitation token")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invitation for {self.email} (Expired: {self.is_expired()}, Used: {self.is_used})"

