# judging/templatetags/judging_extras.py
from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None

@register.filter(is_safe=True)
def jsonify(obj):
    try:
        return mark_safe(json.dumps(list(obj) if hasattr(obj, '__iter__') and not isinstance(obj, (str, dict)) else obj))
    except TypeError:
        return mark_safe(json.dumps([]))

@register.filter
def get_score_range(max_score_value):
    """ 0 дан max_score_value гача (max_score_value ҳам киради) сонлар рўйхатини қайтаради. """
    if isinstance(max_score_value, int) and max_score_value >= 0:
        return range(max_score_value + 1)
    return [] 