import os
import json
import urllib.parse
import urllib.request
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .authentication import generate_jwt_token

logger = logging.getLogger(__name__)
User = get_user_model()

class GoogleAuthService:
    @staticmethod
    def get_client_id():
        return os.getenv('GOOGLE_OAUTH_CLIENT_ID', '').strip()

    @staticmethod
    def get_client_secret():
        return os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()

    @staticmethod
    def get_redirect_uri():
        return os.getenv('GOOGLE_OAUTH_REDIRECT_URI', 'http://localhost:5173/auth/google/callback').strip()

    @classmethod
    def is_configured(cls):
        return bool(cls.get_client_id() and cls.get_client_secret())

    @classmethod
    def get_authorization_url(cls, state=None):
        """
        Builds the canonical Google OAuth2 authorization URL.
        """
        client_id = cls.get_client_id()
        if not client_id:
            raise ValidationError("Google OAuth Client ID is not configured on the server.")

        redirect_uri = cls.get_redirect_uri()
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'online',
            'prompt': 'select_account',
        }
        if state:
            params['state'] = state

        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    @classmethod
    def exchange_code_for_user_info(cls, code, redirect_uri=None):
        """
        Exchanges authorization code with Google for tokens and userinfo.
        """
        client_id = cls.get_client_id()
        client_secret = cls.get_client_secret()
        resolved_redirect_uri = redirect_uri or cls.get_redirect_uri()

        if not client_id or not client_secret:
            raise ValidationError("Google OAuth credentials are not fully configured in the server environment.")

        # 1. Exchange code for access_token and id_token
        token_endpoint = "https://oauth2.googleapis.com/token"
        token_payload = urllib.parse.urlencode({
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': resolved_redirect_uri,
            'grant_type': 'authorization_code',
        }).encode('utf-8')

        token_req = urllib.request.Request(
            token_endpoint,
            data=token_payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        try:
            with urllib.request.urlopen(token_req, timeout=10) as token_res:
                token_data = json.loads(token_res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            logger.error(f"Google token exchange failed: {err_body}")
            raise ValidationError(f"Google token exchange error: {e.reason}")
        except Exception as e:
            logger.error(f"Google token connection error: {str(e)}")
            raise ValidationError("Could not connect to Google OAuth service.")

        access_token = token_data.get('access_token')
        id_token = token_data.get('id_token')

        if not access_token and not id_token:
            raise ValidationError("Google did not return valid authentication tokens.")

        # 2. Fetch verified user info
        userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
        userinfo_req = urllib.request.Request(
            userinfo_endpoint,
            headers={'Authorization': f"Bearer {access_token}"}
        )

        try:
            with urllib.request.urlopen(userinfo_req, timeout=10) as userinfo_res:
                user_info = json.loads(userinfo_res.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Google userinfo fetch failed: {str(e)}")
            raise ValidationError("Failed to retrieve user profile from Google.")

        return user_info

    @classmethod
    def verify_id_token(cls, id_token):
        """
        Validates a direct Google ID Token (e.g. from Google Identity Services One Tap).
        """
        tokeninfo_endpoint = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}"
        req = urllib.request.Request(tokeninfo_endpoint)

        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                payload = json.loads(res.read().decode('utf-8'))
        except Exception as e:
            raise ValidationError("Invalid or expired Google ID token.")

        client_id = cls.get_client_id()
        if client_id and payload.get('aud') != client_id:
            raise ValidationError("Google token audience mismatch.")

        return payload

    @classmethod
    def get_or_create_user_from_google(cls, user_info):
        """
        Integrates Google identity with existing User model according to authoritative RBAC rules:
        1. IF active FACULTY account exists with exact normalized google_email: authenticate as FACULTY
        2. ELSE IF ADMIN account exists: authenticate as ADMIN
        3. ELSE IF STUDENT account exists or institutional email provided: apply Student institutional rules
        4. ELSE: reject login with clear message
        """
        sub = user_info.get('sub')
        email = (user_info.get('email') or '').strip().lower()
        if not sub or not email:
            raise ValidationError("Google profile did not contain required subject and email fields.")

        email_verified = user_info.get('email_verified', False)
        if isinstance(email_verified, str):
            email_verified = email_verified.lower() == 'true'

        given_name = user_info.get('given_name', '')
        family_name = user_info.get('family_name', '')
        picture = user_info.get('picture', '')

        # -------------------------------------------------------------
        # 1. FACULTY AUTHENTICATION: Match exact provisioned Faculty email
        # -------------------------------------------------------------
        faculty_user = User.objects.filter(email__iexact=email, role__in=['FACULTY', 'MENTOR']).first()
        if not faculty_user and sub:
            faculty_user = User.objects.filter(google_id=sub, role__in=['FACULTY', 'MENTOR']).first()

        if faculty_user:
            # Ensure email matches exact provisioned email
            if faculty_user.email.strip().lower() != email:
                raise ValidationError("Your Google account is not associated with an approved Faculty account. Please contact the administrator.")

            if not faculty_user.is_active or faculty_user.verification_status == 'BLOCKED':
                raise ValidationError("This Faculty account has been disabled or deactivated. Please contact the administrator.")

            update_fields = []
            if not faculty_user.google_id:
                faculty_user.google_id = sub
                update_fields.append('google_id')
            if faculty_user.auth_provider == 'LOCAL':
                faculty_user.auth_provider = 'GOOGLE'
                update_fields.append('auth_provider')
            if picture and not faculty_user.avatar_url:
                faculty_user.avatar_url = picture
                update_fields.append('avatar_url')
            if faculty_user.verification_status == 'PENDING_EMAIL_VERIFICATION':
                faculty_user.verification_status = 'VERIFIED'
                update_fields.append('verification_status')

            if update_fields:
                faculty_user.save(update_fields=list(set(update_fields)))

            token = generate_jwt_token(faculty_user)
            return faculty_user, token

        # -------------------------------------------------------------
        # 2. ADMIN AUTHENTICATION
        # -------------------------------------------------------------
        admin_user = User.objects.filter(email__iexact=email, role='ADMIN').first()
        if not admin_user and sub:
            admin_user = User.objects.filter(google_id=sub, role='ADMIN').first()
        if not admin_user and email == 'fxskillhub@gmail.com':
            admin_user = User.objects.filter(username='fx_admin').first()
            if admin_user:
                admin_user.email = email

        if admin_user:
            if not admin_user.is_active:
                raise ValidationError("This Administrator account has been deactivated.")

            update_fields = []
            if not admin_user.google_id:
                admin_user.google_id = sub
                update_fields.append('google_id')
            if admin_user.auth_provider == 'LOCAL':
                admin_user.auth_provider = 'GOOGLE'
                update_fields.append('auth_provider')
            if picture and not admin_user.avatar_url:
                admin_user.avatar_url = picture
                update_fields.append('avatar_url')
            if admin_user.email == email and 'email' not in update_fields:
                update_fields.append('email')
            if update_fields:
                admin_user.save(update_fields=list(set(update_fields)))

            token = generate_jwt_token(admin_user)
            return admin_user, token

        # Special case: auto-creation for default admin fxskillhub@gmail.com
        if email == 'fxskillhub@gmail.com':
            user = User.objects.create(
                username='fx_admin',
                email=email,
                first_name=given_name or 'FXEC',
                last_name=family_name or 'Administrator',
                google_id=sub,
                auth_provider='GOOGLE',
                role='ADMIN',
                is_staff=True,
                is_superuser=True,
                verification_status='VERIFIED',
                avatar_url=picture,
                is_demo=False
            )
            user.set_unusable_password()
            user.save()
            token = generate_jwt_token(user)
            return user, token

        # -------------------------------------------------------------
        # 3. STUDENT AUTHENTICATION: Strict Institutional Email Domain Check
        # -------------------------------------------------------------
        from .validators import validate_institutional_email
        is_institutional_student = False
        try:
            validate_institutional_email(email)
            is_institutional_student = True
        except Exception:
            is_institutional_student = False

        if is_institutional_student:
            student_user = User.objects.filter(email__iexact=email, role='STUDENT').first()
            if not student_user and sub:
                student_user = User.objects.filter(google_id=sub, role='STUDENT').first()

            if student_user:
                if student_user.verification_status == 'BLOCKED':
                    raise ValidationError("This student account has been blocked by Academic Administration.")

                update_fields = []
                if not student_user.google_id:
                    student_user.google_id = sub
                    update_fields.append('google_id')
                if student_user.auth_provider == 'LOCAL':
                    student_user.auth_provider = 'GOOGLE'
                    update_fields.append('auth_provider')
                if picture and not student_user.avatar_url:
                    student_user.avatar_url = picture
                    update_fields.append('avatar_url')
                if student_user.verification_status == 'PENDING_EMAIL_VERIFICATION':
                    student_user.verification_status = 'VERIFIED'
                    student_user.is_active = True
                    update_fields.extend(['verification_status', 'is_active'])

                if update_fields:
                    student_user.save(update_fields=list(set(update_fields)))

                token = generate_jwt_token(student_user)
                return student_user, token
            else:
                base_username = email.split('@')[0].replace('.', '_').replace('-', '_')
                username = base_username
                suffix = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{suffix}"
                    suffix += 1

                user = User.objects.create(
                    username=username,
                    email=email,
                    first_name=given_name,
                    last_name=family_name,
                    google_id=sub,
                    auth_provider='GOOGLE',
                    role='STUDENT',
                    verification_status='VERIFIED',
                    avatar_url=picture,
                    is_demo=False
                )
                user.set_unusable_password()
                user.save()
                token = generate_jwt_token(user)
                return user, token

        # -------------------------------------------------------------
        # 4. UNPROVISIONED / UNRECOGNIZED GOOGLE ACCOUNT
        # -------------------------------------------------------------
        raise ValidationError("Your Google account is not associated with an approved Faculty account. Please contact the administrator.")
