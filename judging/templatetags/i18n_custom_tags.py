from django import template
from django.urls import translate_url
from django.conf import settings

register = template.Library()

@register.simple_tag(takes_context=True)
def get_next_url_for_language_switch(context):
    request = context.get('request')
    if not request:
        return ''
    
    # Жорий full_path'ни оламиз
    current_full_path = request.get_full_path()
    
    # Асосий тилга translate_url қиламиз
    # Бу current_full_path'дан жорий тил префиксини олиб ташлашга ҳаракат қилади,
    # агар жорий тил асосий тил бўлмаса.
    # Агар жорий тил асосий тил бўлса, ўзини қайтаради.
    path_for_default_lang = translate_url(current_full_path, settings.LANGUAGE_CODE)
    
    return path_for_default_lang