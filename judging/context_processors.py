# judging/context_processors.py
from django.conf import settings

def site_languages(request):
    return {
        'SITE_LANGUAGES': settings.LANGUAGES,
        'CURRENT_LANGUAGE_CODE': request.LANGUAGE_CODE # Ёки get_language()
    }