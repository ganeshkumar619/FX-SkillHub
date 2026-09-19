import os
import uuid
import hashlib
from django.db import models
from django.conf import settings

class Certificate(models.Model):
    STATUS_CHOICES = (
        ('VALID', 'Valid'),
        ('REVOKED', 'Revoked'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.OneToOneField('learning.Enrollment', on_delete=models.CASCADE, related_name='certificate')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey('catalogue.Course', on_delete=models.CASCADE, related_name='certificates')
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_number = models.CharField(max_length=64, unique=True)
    integrity_hash = models.CharField(max_length=64, help_text="SHA-256 cryptographic digest of certificate metadata")
    qr_url = models.URLField(help_text="Canonical URL to public verification page")
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)

    # Dynamic fields for official certificate display
    skill = models.CharField(max_length=128, blank=True, default='')
    assessment_score = models.CharField(max_length=32, blank=True, default='')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='VALID', db_index=True)
    
    # Revocation controls
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True, null=True)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='revocations_executed')
    
    is_demo = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-issued_at']

    @property
    def certificate_id(self):
        return self.certificate_number

    def save(self, *args, **kwargs):
        # Synchronize status and is_revoked
        if self.is_revoked:
            self.status = 'REVOKED'
        elif self.status == 'REVOKED':
            self.is_revoked = True
        else:
            self.status = 'VALID'
            self.is_revoked = False
        super().save(*args, **kwargs)

    @classmethod
    def generate_integrity_hash(cls, cert_id, student_username, course_title, issued_iso):
        """Generates deterministic SHA-256 digest of credential payload."""
        payload = f"{cert_id}|{student_username}|{course_title}|{issued_iso}|FXEC_AUTONOMOUS_TIRUNELVELI"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def __str__(self):
        return f"Certificate {self.certificate_number} — {self.student.get_full_name() or self.student.username} ({self.course.title})"


class CertificateVerification(models.Model):
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='verifications')
    verified_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-verified_at']

    def __str__(self):
        return f"Verification of {self.certificate.certificate_number} at {self.verified_at}"


class BrandingAsset(models.Model):
    ASSET_TYPE_CHOICES = (
        ('HORIZONTAL_LOGO', 'Horizontal Institutional Logo'),
        ('CIRCULAR_EMBLEM', 'Circular FXEC Emblem'),
        ('WATERMARK', 'Campus / Institutional Watermark'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    )

    asset_type = models.CharField(max_length=32, choices=ASSET_TYPE_CHOICES, db_index=True)
    image = models.FileField(upload_to='branding/')
    filename = models.CharField(max_length=255, blank=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_branding_assets')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version', '-uploaded_at']

    def save(self, *args, **kwargs):
        if not self.filename and self.image:
            self.filename = os.path.basename(self.image.name)
        if self.status == 'ACTIVE':
            # Mark previous active assets of the same type as INACTIVE
            BrandingAsset.objects.filter(asset_type=self.asset_type, status='ACTIVE').exclude(pk=self.pk).update(status='INACTIVE')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_asset_type_display()} v{self.version} ({self.status})"


class CertificateConfig(models.Model):
    institution_name = models.CharField(max_length=255, default="FRANCIS XAVIER ENGINEERING COLLEGE")
    subtext = models.CharField(max_length=255, default="(Autonomous)", blank=True)
    accreditation_text = models.CharField(max_length=255, default="Approved by AICTE & Affiliated to Anna University", blank=True)
    signatory_1_title = models.CharField(max_length=128, default="Authorized Signatory")
    signatory_1_name = models.CharField(max_length=128, blank=True, default="")
    signatory_2_title = models.CharField(max_length=128, default="Course Coordinator")
    signatory_2_name = models.CharField(max_length=128, blank=True, default="")
    cert_id_prefix = models.CharField(max_length=32, default="FXEC-SKILL")
    watermark_enabled = models.BooleanField(default=True)
    watermark_opacity = models.FloatField(default=0.08)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return f"Certificate Configuration ({self.institution_name})"

