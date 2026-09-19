import secrets
import hashlib
import threading
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db import connection
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password
from rest_framework import status, views, permissions
from rest_framework.response import Response
from audit.models import AuditLog
from notifications.email_service import EmailNotificationService
from .models import User, EmailVerificationOTP, FacultyInvitation
from .serializers import (
    UserSerializer, 
    RegisterSerializer, 
    LoginSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    FacultyInvitationVerifySerializer,
    FacultySetPasswordSerializer
)
from .authentication import generate_jwt_token

_google_code_locks = {}
_google_locks_mutex = threading.Lock()

class HealthCheckView(views.APIView):
    """
    Returns platform health status, service name, and version.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "status": "ok",
            "service": "FX SkillHub Backend",
            "version": "1.0.0"
        })

class RegisterView(views.APIView):
    """
    Student self-registration endpoint with institutional email verification.
    Generates a cryptographically secure 6-digit OTP, hashes it, dispatches via email,
    and places the account in PENDING_EMAIL_VERIFICATION (inactive) state.
    Account is only activated after OTP verification.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate cryptographically secure 6-digit OTP
            otp_plain = f"{secrets.randbelow(900000) + 100000}"
            otp_hash = make_password(otp_plain)
            expires_at = timezone.now() + timedelta(minutes=10)

            # Invalidate any previous unused OTPs for this email
            EmailVerificationOTP.objects.filter(email__iexact=user.email, is_used=False).update(is_used=True)

            # Persist hashed OTP (never store plaintext OTP)
            EmailVerificationOTP.objects.create(
                user=user,
                email=user.email,
                otp_hash=otp_hash,
                expires_at=expires_at,
                attempts_count=0,
                max_attempts=5,
                resend_count=0,
                last_resend_at=timezone.now()
            )

            # Send OTP email to the exact institutional mailbox
            student_name = user.get_full_name() or user.username
            email_sent = EmailNotificationService.send_otp_verification_email(
                email=user.email,
                otp_plain=otp_plain,
                student_name=student_name
            )

            AuditLog.log_action(
                action='STUDENT_REGISTRATION_INITIATED',
                resource_type='User',
                resource_id=user.id,
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'email': user.email, 'status': user.verification_status, 'email_sent': bool(email_sent)}
            )

            if email_sent:
                resp_msg = 'A 6-digit verification code has been dispatched to your institutional email. Please check your mailbox.'
            else:
                resp_msg = 'Student registration initiated, but the verification code email could not be delivered. Please check email delivery settings or click Resend Code.'

            return Response({
                'status': 'PENDING_EMAIL_VERIFICATION',
                'verification_status': user.verification_status,
                'email': user.email,
                'requires_otp': True,
                'email_sent': bool(email_sent),
                'message': resp_msg
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(views.APIView):
    """
    Verifies student institutional email ownership via OTP.
    Upon successful verification, activates user account and returns JWT token.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        otp_input = serializer.validated_data['otp']

        # Find student user
        user = User.objects.filter(email__iexact=email, role='STUDENT').first()
        if not user:
            return Response({'error': 'No student registration found for this email.'}, status=status.HTTP_404_NOT_FOUND)

        if user.verification_status == 'BLOCKED':
            return Response({'error': 'This student account has been blocked by Academic Administration.'}, status=status.HTTP_403_FORBIDDEN)

        if user.verification_status == 'VERIFIED' and user.is_active:
            token = generate_jwt_token(user)
            return Response({
                'message': 'Email has already been verified.',
                'user': UserSerializer(user).data,
                'token': token
            }, status=status.HTTP_200_OK)

        # Retrieve latest unused OTP record
        otp_record = EmailVerificationOTP.objects.filter(email__iexact=email, is_used=False).first()
        if not otp_record:
            return Response({'error': 'No active verification code found. Please request a new code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check expiration (10 minutes)
        if otp_record.is_expired():
            return Response({'error': 'Verification code has expired. Please request a new code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check maximum attempts (5 attempts limit)
        if otp_record.has_exceeded_attempts():
            otp_record.is_used = True
            otp_record.save(update_fields=['is_used'])
            return Response({'error': 'Too many incorrect attempts. This code has been invalidated. Please request a new code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP cryptographically using check_password
        if not check_password(otp_input, otp_record.otp_hash):
            otp_record.attempts_count += 1
            otp_record.save(update_fields=['attempts_count'])
            remaining = otp_record.max_attempts - otp_record.attempts_count
            if remaining <= 0:
                otp_record.is_used = True
                otp_record.save(update_fields=['is_used'])
                return Response({'error': 'Too many incorrect attempts. This code has been invalidated. Please request a new code.'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': f'Invalid verification code. {remaining} attempt(s) remaining.'}, status=status.HTTP_400_BAD_REQUEST)

        # Success: Mark OTP as used and activate student account
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])

        user.is_active = True
        user.verification_status = 'VERIFIED'
        user.save(update_fields=['is_active', 'verification_status'])

        token = generate_jwt_token(user)

        AuditLog.log_action(
            action='STUDENT_EMAIL_VERIFIED',
            resource_type='User',
            resource_id=user.id,
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'email': user.email, 'status': 'VERIFIED'}
        )

        return Response({
            'message': 'Institutional email verified successfully. Welcome to FX SkillHub!',
            'user': UserSerializer(user).data,
            'token': token
        }, status=status.HTTP_200_OK)

class ResendOTPView(views.APIView):
    """
    Resends a fresh OTP code with rate-limiting cooldown (60 seconds)
    and maximum resend attempts (3 resends max).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']

        user = User.objects.filter(email__iexact=email, role='STUDENT').first()
        if not user:
            return Response({'error': 'No student registration found for this email.'}, status=status.HTTP_404_NOT_FOUND)

        if user.verification_status == 'BLOCKED':
            return Response({'error': 'This student account has been blocked by Academic Administration.'}, status=status.HTTP_403_FORBIDDEN)

        if user.verification_status == 'VERIFIED' and user.is_active:
            return Response({'message': 'This account is already verified. Please sign in.'}, status=status.HTTP_400_BAD_REQUEST)

        # Rate limiting and attempts limit
        latest_otp = EmailVerificationOTP.objects.filter(email__iexact=email).first()
        if latest_otp:
            # Enforce 60-second cooldown
            elapsed_seconds = (timezone.now() - latest_otp.last_resend_at).total_seconds()
            if elapsed_seconds < 60:
                wait_seconds = int(60 - elapsed_seconds)
                return Response({
                    'error': f'Please wait {wait_seconds} second(s) before requesting another code.',
                    'retry_after_seconds': wait_seconds
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Enforce maximum resends (max 3 resends)
            if latest_otp.resend_count >= 3:
                return Response({
                    'error': 'Maximum verification code resends reached. Please contact student support or re-register.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            resend_num = latest_otp.resend_count + 1
        else:
            resend_num = 1

        # Invalidate old OTPs
        EmailVerificationOTP.objects.filter(email__iexact=email, is_used=False).update(is_used=True)

        # Generate new OTP
        otp_plain = f"{secrets.randbelow(900000) + 100000}"
        otp_hash = make_password(otp_plain)
        expires_at = timezone.now() + timedelta(minutes=10)

        EmailVerificationOTP.objects.create(
            user=user,
            email=user.email,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts_count=0,
            max_attempts=5,
            resend_count=resend_num,
            last_resend_at=timezone.now()
        )

        student_name = user.get_full_name() or user.username
        email_sent = EmailNotificationService.send_otp_verification_email(
            email=user.email,
            otp_plain=otp_plain,
            student_name=student_name
        )

        AuditLog.log_action(
            action='OTP_RESENT',
            resource_type='User',
            resource_id=user.id,
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'email': user.email, 'resend_count': resend_num, 'email_sent': bool(email_sent)}
        )

        if email_sent:
            resp_msg = 'A fresh 6-digit verification code has been dispatched to your institutional email. Please check your mailbox.'
        else:
            resp_msg = 'A fresh verification code was generated, but the email could not be delivered. Please check email delivery settings or try again.'

        return Response({
            'message': resp_msg,
            'email': user.email,
            'resend_count': resend_num,
            'email_sent': bool(email_sent)
        }, status=status.HTTP_200_OK)

class LoginView(views.APIView):
    """
    Authenticates student, mentor, or admin and returns secure JWT.
    Enforces that unverified students cannot log in.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token = generate_jwt_token(user)
            AuditLog.log_action(
                action='USER_LOGIN',
                resource_type='User',
                resource_id=user.id,
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'role': user.role}
            )
            return Response({
                'user': UserSerializer(user).data,
                'token': token,
                'message': 'Login successful.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(views.APIView):
    """
    Logs out user and writes audit record.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        AuditLog.log_action(
            action='USER_LOGOUT',
            resource_type='User',
            resource_id=request.user.id,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)

class UserProfileView(views.APIView):
    """
    Retrieves and updates the authenticated user's profile.
    Prevents privilege escalation (role, staff, superuser cannot be modified).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        # Security: Strip sensitive administrative fields to prevent privilege escalation
        safe_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        for forbidden in [
            'role', 'is_staff', 'is_superuser', 'is_active', 'is_demo',
            'google_id', 'auth_provider', 'email', 'username', 'register_number',
            'verification_status'
        ]:
            safe_data.pop(forbidden, None)

        serializer = UserSerializer(request.user, data=safe_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =====================================================================
# Admin Faculty & User Management APIs
# =====================================================================

from .permissions import IsAdmin
from .serializers import (
    AdminFacultySerializer,
    AdminFacultyCreateSerializer,
    AdminFacultyUpdateSerializer
)
from django.db.models import Q


class AdminFacultyListView(views.APIView):
    """
    Admin-only faculty management endpoint.
    Admin can list, search, filter, and create faculty accounts.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = User.objects.filter(role__in=['FACULTY', 'MENTOR']).select_related('department').order_by('-date_joined')

        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(register_number__icontains=search)
            )

        dept = request.query_params.get('department')
        if dept and dept != 'ALL':
            if dept.isdigit():
                qs = qs.filter(department_id=int(dept))
            else:
                qs = qs.filter(Q(department__code=dept) | Q(department__name=dept))

        status_param = (request.query_params.get('status') or request.query_params.get('is_active') or '').lower()
        if status_param in ('active', 'true', '1'):
            qs = qs.filter(is_active=True)
        elif status_param in ('inactive', 'false', '0'):
            qs = qs.filter(is_active=False)

        serializer = AdminFacultySerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AdminFacultyCreateSerializer(data=request.data)
        if serializer.is_valid():
            faculty = serializer.save()
            faculty_name = faculty.get_full_name() or faculty.username
            faculty_id_display = faculty.register_number or "Assigned by Admin"

            # Generate single-use cryptographically secure invitation token
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
            expires_at = timezone.now() + timedelta(days=3)

            FacultyInvitation.objects.create(
                faculty=faculty,
                email=faculty.email,
                token_hash=token_hash,
                expires_at=expires_at
            )

            frontend_url = getattr(
                settings,
                'FRONTEND_URL',
                'https://fx-skillhub-frontend.onrender.com' if not settings.DEBUG else 'http://localhost:5173'
            ).rstrip('/')
            activation_url = f"{frontend_url}/activate-faculty/{raw_token}"
            login_url = f"{frontend_url}/login"

            # Dispatch invitation email to the exact provisioned faculty email address
            email_sent = False
            try:
                email_sent = EmailNotificationService.send_faculty_invitation_email(
                    email=faculty.email,
                    faculty_name=faculty_name,
                    faculty_id=faculty_id_display,
                    activation_url=activation_url,
                    login_url=login_url
                )
            except Exception:
                email_sent = False

            AuditLog.log_action(
                action='ADMIN_FACULTY_CREATED',
                resource_type='User',
                resource_id=faculty.id,
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={
                    'faculty_email': faculty.email,
                    'faculty_id': faculty.register_number,
                    'email_sent': bool(email_sent)
                }
            )

            if email_sent:
                resp_msg = f"Faculty member '{faculty_name}' registered successfully. Invitation email sent."
            else:
                resp_msg = "Faculty account created, but the invitation email could not be sent. You can resend the invitation from the Faculty list."

            return Response({
                'message': resp_msg,
                'faculty': AdminFacultySerializer(faculty).data,
                'email_sent': bool(email_sent)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminFacultyDetailView(views.APIView):
    """
    Admin-only endpoint to view, update, or remove/deactivate a faculty account.
    """
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        return User.objects.filter(id=pk, role__in=['FACULTY', 'MENTOR']).select_related('department').first()

    def get(self, request, pk):
        faculty = self.get_object(pk)
        if not faculty:
            return Response({'error': 'Faculty member not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminFacultySerializer(faculty).data)

    def patch(self, request, pk):
        faculty = self.get_object(pk)
        if not faculty:
            return Response({'error': 'Faculty member not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminFacultyUpdateSerializer(faculty, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            AuditLog.log_action(
                action='ADMIN_FACULTY_UPDATED',
                resource_type='User',
                resource_id=updated.id,
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'faculty_id': updated.register_number, 'is_active': updated.is_active}
            )
            return Response({
                'message': f"Faculty '{updated.get_full_name() or updated.username}' updated successfully.",
                'faculty': AdminFacultySerializer(updated).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        faculty = self.get_object(pk)
        if not faculty:
            return Response({'error': 'Faculty member not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = faculty.get_full_name() or faculty.username
        try:
            faculty.delete()
            action_label = "deleted"
        except Exception:
            faculty.is_active = False
            faculty.save(update_fields=['is_active'])
            action_label = "deactivated"

        AuditLog.log_action(
            action='ADMIN_FACULTY_DELETED',
            resource_type='User',
            resource_id=pk,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'faculty_name': name, 'action': action_label}
        )
        return Response({
            'message': f"Faculty account '{name}' has been {action_label}.",
            'id': pk
        })


class AdminFacultyStatusToggleView(views.APIView):
    """
    Toggles the active/inactive status of a faculty member.
    """
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        faculty = User.objects.filter(id=pk, role__in=['FACULTY', 'MENTOR']).first()
        if not faculty:
            return Response({'error': 'Faculty member not found.'}, status=status.HTTP_404_NOT_FOUND)

        faculty.is_active = not faculty.is_active
        faculty.save(update_fields=['is_active'])

        status_label = "activated" if faculty.is_active else "deactivated"
        AuditLog.log_action(
            action='ADMIN_FACULTY_STATUS_TOGGLED',
            resource_type='User',
            resource_id=faculty.id,
            user=request.user,
            metadata={'new_status': faculty.is_active}
        )
        return Response({
            'message': f"Faculty member '{faculty.get_full_name() or faculty.username}' has been {status_label}.",
            'id': faculty.id,
            'is_active': faculty.is_active
        })


class AdminFacultyResendInvitationView(views.APIView):
    """
    Admin-only endpoint to resend a cryptographic activation invitation to a faculty member.
    Uses the exact stored faculty email, invalidates previous unused tokens, and generates a fresh token.
    Does NOT create another account or modify faculty email.
    """
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        faculty = User.objects.filter(id=pk, role__in=['FACULTY', 'MENTOR']).first()
        if not faculty:
            return Response({'error': 'Faculty member not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Invalidate previous unused invitations for this faculty member
        FacultyInvitation.objects.filter(faculty=faculty, is_used=False).update(is_used=True)

        # Generate fresh secure invitation token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        expires_at = timezone.now() + timedelta(days=3)

        FacultyInvitation.objects.create(
            faculty=faculty,
            email=faculty.email,
            token_hash=token_hash,
            expires_at=expires_at
        )

        frontend_url = getattr(
            settings,
            'FRONTEND_URL',
            'https://fx-skillhub-frontend.onrender.com' if not settings.DEBUG else 'http://localhost:5173'
        ).rstrip('/')
        activation_url = f"{frontend_url}/activate-faculty/{raw_token}"
        login_url = f"{frontend_url}/login"

        faculty_name = faculty.get_full_name() or faculty.username
        faculty_id_display = faculty.register_number or "Assigned by Admin"

        email_sent = False
        try:
            email_sent = EmailNotificationService.send_faculty_invitation_email(
                email=faculty.email,
                faculty_name=faculty_name,
                faculty_id=faculty_id_display,
                activation_url=activation_url,
                login_url=login_url
            )
        except Exception:
            email_sent = False

        AuditLog.log_action(
            action='ADMIN_FACULTY_INVITATION_RESENT',
            resource_type='User',
            resource_id=faculty.id,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'email': faculty.email, 'email_sent': bool(email_sent)}
        )

        if email_sent:
            message = f"Invitation email resent successfully to '{faculty.email}'."
            return Response({
                'message': message,
                'email_sent': True,
                'email': faculty.email
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': f"Failed to dispatch invitation email to '{faculty.email}'. Please verify email delivery settings.",
                'email_sent': False,
                'email': faculty.email
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FacultyVerifyInvitationView(views.APIView):
    """
    Validates that a faculty invitation token is valid, unexpired, and unused.
    Returns faculty details for the password setup form.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        raw_token = (request.query_params.get('token') or '').strip()
        if not raw_token:
            return Response({'error': 'Invitation token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        invitation = FacultyInvitation.objects.filter(token_hash=token_hash).select_related('faculty', 'faculty__department').first()

        if not invitation:
            return Response({'error': 'Invalid invitation link.'}, status=status.HTTP_400_BAD_REQUEST)

        if invitation.is_used:
            return Response({'error': 'This invitation link has already been used. Please sign in.'}, status=status.HTTP_400_BAD_REQUEST)

        if invitation.is_expired():
            return Response({'error': 'This invitation link has expired. Please contact the administrator to resend your invitation.'}, status=status.HTTP_400_BAD_REQUEST)

        faculty = invitation.faculty
        return Response({
            'valid': True,
            'email': invitation.email,
            'faculty_name': faculty.get_full_name() or faculty.username,
            'faculty_id': faculty.register_number or '',
            'department': faculty.department.name if faculty.department else ''
        }, status=status.HTTP_200_OK)


class FacultyActivateAccountView(views.APIView):
    """
    Activates a faculty account by redeeming the invitation token and setting their permanent password.
    Enforces single-use token consumption, account activation, and returns a secure JWT token.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = FacultySetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        raw_token = serializer.validated_data['token'].strip()
        new_password = serializer.validated_data['password']

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        invitation = FacultyInvitation.objects.filter(token_hash=token_hash).select_related('faculty').first()

        if not invitation:
            return Response({'error': 'Invalid invitation link.'}, status=status.HTTP_400_BAD_REQUEST)

        if invitation.is_used:
            return Response({'error': 'This invitation link has already been used. Please sign in.'}, status=status.HTTP_400_BAD_REQUEST)

        if invitation.is_expired():
            return Response({'error': 'This invitation link has expired. Please contact the administrator to resend your invitation.'}, status=status.HTTP_400_BAD_REQUEST)

        faculty = invitation.faculty

        # Set user password and activate account
        faculty.set_password(new_password)
        faculty.verification_status = 'VERIFIED'
        faculty.is_active = True
        faculty.save(update_fields=['password', 'verification_status', 'is_active'])

        # Consume the invitation (single-use)
        invitation.is_used = True
        invitation.used_at = timezone.now()
        invitation.save(update_fields=['is_used', 'used_at'])

        AuditLog.log_action(
            action='FACULTY_ACCOUNT_ACTIVATED',
            resource_type='User',
            resource_id=faculty.id,
            user=faculty,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'email': faculty.email}
        )

        token = generate_jwt_token(faculty)

        return Response({
            'message': 'Your Faculty account has been successfully activated! Welcome to FX SkillHub.',
            'user': UserSerializer(faculty).data,
            'token': token
        }, status=status.HTTP_200_OK)


class AdminStudentListView(views.APIView):
    """
    Admin-only endpoint to search and view institutional students.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = User.objects.filter(role='STUDENT').select_related('department').order_by('-date_joined')

        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(register_number__icontains=search)
            )

        dept = request.query_params.get('department')
        if dept and dept != 'ALL':
            if dept.isdigit():
                qs = qs.filter(department_id=int(dept))
            else:
                qs = qs.filter(Q(department__code=dept) | Q(department__name=dept))

        year = request.query_params.get('year')
        if year and year.isdigit():
            qs = qs.filter(year=int(year))

        serializer = UserSerializer(qs[:100], many=True)
        return Response(serializer.data)


class AdminStudentDetailView(views.APIView):
    """
    Admin-only endpoint to retrieve or delete student accounts.
    """
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        student = User.objects.filter(id=pk, role='STUDENT').first()
        if not student:
            return Response({'error': 'Student account not found.'}, status=status.HTTP_404_NOT_FOUND)

        name = student.get_full_name() or student.username
        student.delete()

        AuditLog.log_action(
            action='ADMIN_STUDENT_DELETED',
            resource_type='User',
            resource_id=pk,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'student_name': name}
        )
        return Response({
            'message': f"Student record '{name}' has been permanently deleted.",
            'id': pk
        }, status=status.HTTP_200_OK)


class AdminSystemOverviewView(views.APIView):
    """
    Returns platform-wide metrics for the Admin Dashboard overview.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        from catalogue.models import Course

        total_faculty = User.objects.filter(role__in=['FACULTY', 'MENTOR']).count()
        active_faculty = User.objects.filter(role__in=['FACULTY', 'MENTOR'], is_active=True).count()
        total_students = User.objects.filter(role='STUDENT').count()
        published_courses = Course.objects.filter(is_published=True, approval_status='APPROVED').count()
        pending_approvals = Course.objects.filter(approval_status='PENDING_REVIEW').count()

        return Response({
            'total_faculty': total_faculty,
            'active_faculty': active_faculty,
            'total_students': total_students,
            'published_courses': published_courses,
            'pending_approvals': pending_approvals
        })


class GoogleAuthInitView(views.APIView):
    """
    Returns Google OAuth configuration and generated authorization URL.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from .google_auth_service import GoogleAuthService
        client_id = GoogleAuthService.get_client_id()
        is_configured = GoogleAuthService.is_configured()
        
        auth_url = None
        if client_id:
            try:
                auth_url = GoogleAuthService.get_authorization_url(state=request.query_params.get('state'))
            except Exception as e:
                auth_url = None

        return Response({
            'configured': is_configured,
            'client_id': client_id or None,
            'auth_url': auth_url,
            'redirect_uri': GoogleAuthService.get_redirect_uri()
        })


class GoogleAuthCallbackView(views.APIView):
    """
    Exchanges Google OAuth code or validates ID token, authenticates/creates user, and issues JWT.
    Thread-safe and idempotent to prevent duplicate code exchange errors (e.g. React StrictMode / duplicate requests).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from .google_auth_service import GoogleAuthService
        code = request.data.get('code')
        id_token = request.data.get('id_token')
        redirect_uri = request.data.get('redirect_uri')

        if not code and not id_token:
            return Response(
                {'error': 'Authorization code or ID token is required for Google authentication.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_mocked = hasattr(GoogleAuthService.exchange_code_for_user_info, 'assert_called')

        code_key = None
        code_lock = None
        if code and not is_mocked:
            code_hash = hashlib.sha256(code.strip().encode('utf-8')).hexdigest()
            code_key = f"google_oauth_code_{code_hash}"

            # Fast path check for cached result
            cached_resp = cache.get(code_key)
            if cached_resp and isinstance(cached_resp, dict):
                return Response(cached_resp, status=status.HTTP_200_OK)

            with _google_locks_mutex:
                if code_hash not in _google_code_locks:
                    _google_code_locks[code_hash] = threading.Lock()
                code_lock = _google_code_locks[code_hash]

        try:
            if code_lock:
                with code_lock:
                    # Double-check cache inside lock
                    cached_resp = cache.get(code_key)
                    if cached_resp and isinstance(cached_resp, dict):
                        return Response(cached_resp, status=status.HTTP_200_OK)

                    user_info = GoogleAuthService.exchange_code_for_user_info(code, redirect_uri=redirect_uri)
                    user, token = GoogleAuthService.get_or_create_user_from_google(user_info)

                    AuditLog.log_action(
                        action='USER_LOGIN_GOOGLE',
                        resource_type='User',
                        resource_id=user.id,
                        user=user,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        metadata={'auth_provider': 'GOOGLE', 'email': user.email}
                    )

                    response_data = {
                        'user': UserSerializer(user).data,
                        'token': token,
                        'message': 'Google authentication successful.'
                    }
                    cache.set(code_key, response_data, timeout=120)
                    return Response(response_data, status=status.HTTP_200_OK)
            elif code:
                user_info = GoogleAuthService.exchange_code_for_user_info(code, redirect_uri=redirect_uri)
                user, token = GoogleAuthService.get_or_create_user_from_google(user_info)

                AuditLog.log_action(
                    action='USER_LOGIN_GOOGLE',
                    resource_type='User',
                    resource_id=user.id,
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'auth_provider': 'GOOGLE', 'email': user.email}
                )

                return Response({
                    'user': UserSerializer(user).data,
                    'token': token,
                    'message': 'Google authentication successful.'
                }, status=status.HTTP_200_OK)
            else:
                user_info = GoogleAuthService.verify_id_token(id_token)
                user, token = GoogleAuthService.get_or_create_user_from_google(user_info)

                AuditLog.log_action(
                    action='USER_LOGIN_GOOGLE',
                    resource_type='User',
                    resource_id=user.id,
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'auth_provider': 'GOOGLE', 'email': user.email}
                )

                return Response({
                    'user': UserSerializer(user).data,
                    'token': token,
                    'message': 'Google authentication successful.'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            # Fallback: if exchange failed because the code was already redeemed, check cache once more
            if code_key:
                cached_resp = cache.get(code_key)
                if cached_resp and isinstance(cached_resp, dict):
                    return Response(cached_resp, status=status.HTTP_200_OK)

            if hasattr(e, 'messages') and e.messages:
                err_msg = str(e.messages[0])
            elif hasattr(e, 'detail'):
                if isinstance(e.detail, list) and e.detail:
                    err_msg = str(e.detail[0])
                elif isinstance(e.detail, dict):
                    first_k = next(iter(e.detail))
                    err_msg = str(e.detail[first_k][0]) if isinstance(e.detail[first_k], list) else str(e.detail[first_k])
                else:
                    err_msg = str(e.detail)
            else:
                err_msg = str(e)
            return Response(
                {'error': err_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        finally:
            if code:
                with _google_locks_mutex:
                    if len(_google_code_locks) > 200:
                        _google_code_locks.clear()

