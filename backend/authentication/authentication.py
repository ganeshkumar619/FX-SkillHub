import jwt
import datetime
from django.conf import settings
from rest_framework import authentication, exceptions
from django.contrib.auth import get_user_model

User = get_user_model()

def generate_jwt_token(user):
    """Generates a secure signed JWT token containing user ID, role, and expiration."""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        'iat': datetime.datetime.now(datetime.timezone.utc),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token

class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT Authentication checking Authorization: Bearer <token>
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Authentication token has expired.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid authentication token.')

        user_id = payload.get('user_id')
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No active user associated with this token.')

        return (user, token)
