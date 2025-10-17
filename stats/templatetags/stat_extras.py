from django import template
from stats.cfb_api import prettify_stat_name

register = template.Library()

@register.filter(name='prettify')
def prettify(value):
    if value is None:
        return ''
    try:
        return prettify_stat_name(str(value))
    except Exception:
        return str(value)

