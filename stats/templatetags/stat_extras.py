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


@register.filter(name='percentile')
def percentile(rank, total):
    """
    Calculate percentile for ranking (inverted because lower rank is better).
    Returns a percentage for progress bar visualization.
    """
    if not rank or not total:
        return 0
    try:
        rank = int(rank)
        total = int(total)
        if total == 0:
            return 0
        # Invert the percentile (rank 1 should show 100%, last rank should show low %)
        return round(((total - rank + 1) / total) * 100, 1)
    except (ValueError, TypeError):
        return 0


