from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from catalogue.models import Department
from .validators import validate_institutional_email, validate_standard_email, normalize_email

from django.db.models import Q
from .models import User, EmailVerificationOTP, ApprovedStudentDirectory

User = get_user_model()

class DepartmentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'code', 'name']

class UserSerializer(serializers.ModelSerializer):
    department_details = DepartmentBriefSerializer(source='department', read_only=True)
    faculty_id = serializers.CharField(source='register_number', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'verification_status', 'department', 'department_details', 'register_number',
            'faculty_id', 'year', 'phone', 'is_demo', 'is_active', 'avatar_url', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    year = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=4)
    name = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'name', 'first_name', 'last_name',
            'department', 'register_number', 'year'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
        }

    def validate_email(self, value):
        clean_email = validate_institutional_email(value)

        # Check existing active/verified accounts
        existing_user = User.objects.filter(email__iexact=clean_email).first()
        if existing_user:
            if existing_user.verification_status == 'BLOCKED':
                raise serializers.ValidationError("This institutional student account has been blocked by Academic Administration.")
            if existing_user.verification_status == 'VERIFIED' or existing_user.is_active:
                raise serializers.ValidationError("An account with this institutional email already exists. Please sign in.")

        # Check Approved Student Directory if populated by college administration
        if ApprovedStudentDirectory.objects.exists():
            matched_entry = ApprovedStudentDirectory.objects.filter(email__iexact=clean_email, is_active_student=True).first()
            if not matched_entry:
                raise serializers.ValidationError(
                    "This email address was not found in the official Francis Xavier Engineering College student directory. "
                    "Please verify your credentials or contact academic administration."
                )

        return clean_email

    def validate_register_number(self, value):
        if value:
            clean_reg = value.strip().upper()
            existing_user = User.objects.filter(register_number__iexact=clean_reg).first()
            if existing_user and (existing_user.verification_status == 'VERIFIED' or existing_user.is_active):
                raise serializers.ValidationError("An account with this Roll / Register Number already exists.")

            # Check Approved Student Directory if populated
            if ApprovedStudentDirectory.objects.exists():
                matched_entry = ApprovedStudentDirectory.objects.filter(register_number__iexact=clean_reg, is_active_student=True).first()
                if not matched_entry:
                    raise serializers.ValidationError(
                        f"Roll / Register Number '{clean_reg}' is not in the approved institutional student directory."
                    )
            return clean_reg
        return value

    def validate(self, attrs):
        # Handle single 'name' field if provided
        full_name = attrs.pop('name', '').strip()
        if full_name and not attrs.get('first_name'):
            parts = full_name.split(' ', 1)
            attrs['first_name'] = parts[0]
            attrs['last_name'] = parts[1] if len(parts) > 1 else ''

        # Cross-validate email and register_number if ApprovedStudentDirectory exists
        if ApprovedStudentDirectory.objects.exists():
            clean_email = attrs.get('email')
            clean_reg = attrs.get('register_number')
            if clean_email and clean_reg:
                dir_match = ApprovedStudentDirectory.objects.filter(
                    email__iexact=clean_email,
                    register_number__iexact=clean_reg,
                    is_active_student=True
                ).exists()
                if not dir_match:
                    raise serializers.ValidationError(
                        "The entered email and Register Number do not match the institutional directory records."
                    )

        # Auto-generate unique username if not provided
        if not attrs.get('username'):
            reg_num = attrs.get('register_number')
            email = attrs.get('email', '')
            base_username = (reg_num or email.split('@')[0]).replace('.', '_').replace('-', '_').lower()
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exclude(email__iexact=email).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            attrs['username'] = username
        elif User.objects.filter(username=attrs.get('username')).exclude(email__iexact=attrs.get('email', '')).exists():
            raise serializers.ValidationError({'username': "This username is already taken."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data['email']
        
        # Enforce STUDENT role strictly and initial PENDING_EMAIL_VERIFICATION state
        validated_data['role'] = 'STUDENT'
        validated_data['is_active'] = False
        validated_data['verification_status'] = 'PENDING_EMAIL_VERIFICATION'

        # If an unverified pending record already exists for this email, reuse and update it
        existing_pending = User.objects.filter(email__iexact=email, verification_status='PENDING_EMAIL_VERIFICATION').first()
        if existing_pending:
            for field, val in validated_data.items():
                setattr(existing_pending, field, val)
            existing_pending.set_password(password)
            existing_pending.save()
            return existing_pending

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        raw_login = attrs.get('username', '').strip()
        password = attrs.get('password')
        portal_role = attrs.get('role', '').strip().upper() if attrs.get('role') else None

        if not raw_login or not password:
            raise serializers.ValidationError('Email/Username and password are required.')

        normalized_email = normalize_email(raw_login) if '@' in raw_login else None

        # Look up user by exact normalized email if email format provided, else by username
        if normalized_email:
            user = User.objects.filter(email__iexact=normalized_email).first()
            if not user:
                user = User.objects.filter(username__iexact=normalized_email).first()
        else:
            user = User.objects.filter(username__iexact=raw_login).first()

        if not user:
            raise serializers.ValidationError('Invalid username or password.')

        # Verify password securely using Django's check_password
        if not user.check_password(password):
            raise serializers.ValidationError('Invalid username or password.')

        # Verification & Account Status Enforcement
        if user.role == 'STUDENT':
            if user.verification_status == 'BLOCKED':
                raise serializers.ValidationError('This student account has been blocked by Academic Administration.')
            if user.verification_status == 'PENDING_EMAIL_VERIFICATION' or not user.is_active:
                raise serializers.ValidationError('Please verify your institutional email first.')
        elif user.role in ('FACULTY', 'MENTOR'):
            if user.verification_status == 'BLOCKED':
                raise serializers.ValidationError('This faculty account has been blocked by Academic Administration.')
            if not user.is_active:
                raise serializers.ValidationError('This faculty account has been disabled or deactivated by Academic Administration.')
            if user.verification_status == 'PENDING_EMAIL_VERIFICATION':
                raise serializers.ValidationError('Please activate your Faculty account and set your password using the invitation email.')
            if normalized_email and user.email.strip().lower() != normalized_email:
                raise serializers.ValidationError('Access denied. Invalid faculty email identity.')
        elif not user.is_active:
            raise serializers.ValidationError('This user account has been disabled or deactivated by Academic Administration.')

        # Server-side portal role verification
        if portal_role:
            if portal_role == 'FACULTY':
                if user.role not in ('FACULTY', 'MENTOR'):
                    raise serializers.ValidationError('Access denied. This account does not have Faculty privileges.')
                # Verify that faculty logged in with their exact provisioned email address
                if normalized_email and user.email.strip().lower() != normalized_email:
                    raise serializers.ValidationError('Access denied. Invalid faculty email identity.')
            elif portal_role == 'STUDENT':
                if user.role != 'STUDENT':
                    raise serializers.ValidationError('Access denied. This account does not have Student privileges.')
            elif portal_role == 'ADMIN':
                if not user.is_admin_user():
                    raise serializers.ValidationError('Access denied. This account does not have Administrator privileges.')

        attrs['user'] = user
        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=10)

    def validate_email(self, value):
        return normalize_email(value)

    def validate_otp(self, value):
        cleaned = value.strip()
        if not cleaned.isdigit() or len(cleaned) != 6:
            raise serializers.ValidationError("Verification code must be a 6-digit number.")
        return cleaned


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return normalize_email(value)


class AdminFacultySerializer(serializers.ModelSerializer):
    department_details = DepartmentBriefSerializer(source='department', read_only=True)
    faculty_id = serializers.CharField(source='register_number', required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'faculty_id', 'register_number', 'department', 'department_details',
            'phone', 'role', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AdminFacultyCreateSerializer(serializers.Serializer):
    faculty_name = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField()
    faculty_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    register_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(required=False, allow_blank=True, min_length=8)
    is_active = serializers.BooleanField(default=True)

    def validate_email(self, value):
        clean_email = validate_standard_email(value)
        if User.objects.filter(email__iexact=clean_email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return clean_email

    def validate(self, attrs):
        fac_id = attrs.get('faculty_id') or attrs.get('register_number')
        if fac_id:
            fac_id = fac_id.strip().upper()
            if User.objects.filter(register_number__iexact=fac_id).exists():
                raise serializers.ValidationError({'faculty_id': f"A faculty member with ID '{fac_id}' already exists."})
            attrs['register_number'] = fac_id
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        fac_name = validated_data.get('faculty_name', '').strip()
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()

        if fac_name and not first_name:
            parts = fac_name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''

        # Store exact normalized email as the faculty account's unique login identity
        username = email

        raw_password = validated_data.get('password')
        register_num = validated_data.get('register_number') or validated_data.get('faculty_id')

        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            register_number=register_num,
            department=validated_data.get('department'),
            phone=validated_data.get('phone', ''),
            role='FACULTY',
            is_staff=True,
            is_active=validated_data.get('is_active', True),
            verification_status='VERIFIED' if raw_password else 'PENDING_EMAIL_VERIFICATION'
        )
        if raw_password:
            user.set_password(raw_password)
        else:
            user.set_unusable_password()
        user.save()
        return user


class FacultyInvitationVerifySerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class FacultySetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=8, write_only=True)
    password_confirm = serializers.CharField(required=True, min_length=8, write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs


class AdminFacultyUpdateSerializer(serializers.ModelSerializer):
    faculty_id = serializers.CharField(source='register_number', required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'faculty_id', 'department',
            'phone', 'is_active', 'password'
        ]

    def validate_faculty_id(self, value):
        if value:
            clean_id = value.strip().upper()
            existing = User.objects.filter(register_number__iexact=clean_id).exclude(id=self.instance.id).first()
            if existing:
                raise serializers.ValidationError(f"Faculty ID '{clean_id}' is already assigned to another user.")
            return clean_id
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        faculty_id = validated_data.pop('faculty_id', None)
        if faculty_id is not None:
            instance.register_number = faculty_id

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if password:
            instance.set_password(password)

        instance.save()
        return instance

