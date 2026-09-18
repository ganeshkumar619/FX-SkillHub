from django.http import JsonResponse
from django.conf import settings

def root_view(request):
    """
    Root endpoint returning service status, frontend URL, and API discovery links.
    """
    return JsonResponse({
        "name": "FX SkillHub",
        "status": "running",
        "frontend": getattr(settings, 'PUBLIC_PORTAL_URL', 'http://localhost:5173'),
        "api": "/api/",
        "health": "/api/health/"
    })

def api_root_view(request):
    """
    API discovery endpoint listing primary domain endpoints.
    """
    return JsonResponse({
        "name": "FX SkillHub API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health/",
            "auth": "/api/auth/",
            "catalogue": "/api/catalogue/",
            "learning": "/api/learning/",
            "assessments": "/api/assessments/",
            "certificates": "/api/certificates/",
            "proctoring": "/api/proctoring/",
            "notifications": "/api/notifications/",
            "audit": "/api/audit/"
        }
    })
