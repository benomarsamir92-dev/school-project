from django.conf import settings

def school_info(request):
    return {
        'school_name': "Trust Academy",
        'school_phone': "+213 540 804 219", 
        'school_email': "info@trustacademy.edu.dz",
        'academic_year': "2025-2026",
    }

def language_context(request):
    """Custom language context without gettext dependency"""
    return {
        'LANGUAGES': settings.LANGUAGES,
        'CURRENT_LANGUAGE': getattr(request, 'LANGUAGE_CODE', 'en')
    }
