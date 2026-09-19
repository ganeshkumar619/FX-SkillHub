"""
Django settings for fx_skillhub project.
FX SkillHub — Francis Xavier Engineering College (Autonomous), Tirunelveli
"""

import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from project root or backend directory (override=True ensures freshest values)
load_dotenv(BASE_DIR / '.env', override=True)
load_dotenv(BASE_DIR.parent / '.env', override=True)

SECRET_KEY = os.getenv('SECRET_KEY', 'fx-skillhub-dev-insecure-secret-key-change-in-production-2026')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',') if h.strip()]
if DEBUG and 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'corsheaders',
    'anymail',
    
    # Core Domain Apps
    'authentication',
    'catalogue',
    'learning',
    'assessments',
    'proctoring',
    'certificates',
    'notifications',
    'audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fx_skillhub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fx_skillhub.wsgi.application'

# Database
# Supports PostgreSQL in production and zero-friction SQLite in local development
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=not DEBUG,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static & Media files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Institutional Portal Domain & Frontend URLs (For QR codes, invitation links & emails)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://fx-skillhub-frontend.onrender.com' if not DEBUG else 'http://localhost:5173').rstrip('/')
PUBLIC_PORTAL_URL = os.getenv('PUBLIC_PORTAL_URL', FRONTEND_URL).rstrip('/')

# Email Configuration — Resend HTTPS API (Port 443) & SMTP Fallback
ANYMAIL_RESEND_API_KEY = os.getenv('ANYMAIL_RESEND_API_KEY', os.getenv('RESEND_API_KEY', '')).strip()
ANYMAIL = {
    'RESEND_API_KEY': ANYMAIL_RESEND_API_KEY,
}

# Legacy SMTP fallback configuration
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '').replace(' ', '')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 't')

# Email Backend Resolution:
# 1. Explicit EMAIL_BACKEND environment variable
# 2. If ANYMAIL_RESEND_API_KEY is configured, route to anymail Resend HTTPS backend
# 3. If in production (not DEBUG), default to anymail Resend HTTPS backend
# 4. If EMAIL_HOST_USER configured in local dev, fallback to SMTP
# 5. Default local dev to console backend
if os.getenv('EMAIL_BACKEND'):
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND')
elif ANYMAIL_RESEND_API_KEY:
    EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'
elif not DEBUG:
    EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'
elif EMAIL_HOST_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Sender configuration
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'FX SkillHub <onboarding@resend.dev>' if 'anymail' in str(EMAIL_BACKEND) else (
        f'FX SkillHub <{EMAIL_HOST_USER}>' if EMAIL_HOST_USER else 'FX SkillHub <skills@francisxavier.ac.in>'
    )
)
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', 10))


# Structured Server Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {process:d} {thread:d} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
