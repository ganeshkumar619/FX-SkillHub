from django.contrib import admin
from .models import Certificate, CertificateVerification, BrandingAsset, CertificateConfig

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_number', 'student', 'course', 'skill', 'assessment_score', 'status', 'issued_at', 'is_revoked')
    list_filter = ('status', 'is_revoked', 'is_demo', 'issued_at')
    search_fields = ('certificate_number', 'student__username', 'student__first_name', 'student__last_name', 'course__title', 'integrity_hash')
    readonly_fields = ('id', 'issued_at', 'integrity_hash', 'qr_url')

@admin.register(CertificateVerification)
class CertificateVerificationAdmin(admin.ModelAdmin):
    list_display = ('certificate', 'verified_at', 'ip_address')
    search_fields = ('certificate__certificate_number', 'ip_address')

@admin.register(BrandingAsset)
class BrandingAssetAdmin(admin.ModelAdmin):
    list_display = ('asset_type', 'version', 'filename', 'status', 'uploaded_by', 'uploaded_at')
    list_filter = ('asset_type', 'status')

@admin.register(CertificateConfig)
class CertificateConfigAdmin(admin.ModelAdmin):
    list_display = ('institution_name', 'subtext', 'signatory_1_title', 'signatory_2_title', 'updated_at')

