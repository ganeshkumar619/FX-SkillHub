from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerificationOTP, ApprovedStudentDirectory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'verification_status', 'is_active')
    list_filter = ('role', 'verification_status', 'is_active', 'department')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'register_number')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Institutional FX Information', {
            'fields': ('role', 'verification_status', 'department', 'register_number', 'year', 'phone', 'is_demo')
        }),
    )


@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'expires_at', 'attempts_count', 'resend_count', 'is_used')
    list_filter = ('is_used', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('otp_hash', 'created_at')


@admin.register(ApprovedStudentDirectory)
class ApprovedStudentDirectoryAdmin(admin.ModelAdmin):
    list_display = ('register_number', 'email', 'full_name', 'department', 'year', 'is_active_student')
    list_filter = ('department', 'year', 'is_active_student')
    search_fields = ('register_number', 'email', 'full_name')
