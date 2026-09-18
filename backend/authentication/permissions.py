from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """Allows access only to authenticated students."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'STUDENT')

class IsFaculty(permissions.BasePermission):
    """Allows access only to authenticated faculty, mentors, or superusers."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.role in ('FACULTY', 'MENTOR') or request.user.is_superuser)
        )

# Backward compatibility alias
IsMentor = IsFaculty

class IsAdmin(permissions.BasePermission):
    """Allows access only to institutional administrators or superusers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.role == 'ADMIN' or request.user.is_superuser))

# Backward compatibility alias
IsAdminOnly = IsAdmin

class IsFacultyOrAdmin(permissions.BasePermission):
    """Allows access to faculty, mentors, admins, or superusers."""
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and 
            (request.user.role in ('FACULTY', 'MENTOR', 'ADMIN') or request.user.is_superuser)
        )

# Backward compatibility alias
IsMentorOrAdmin = IsFacultyOrAdmin
