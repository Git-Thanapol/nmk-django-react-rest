from django import template
from pybaht import bahttext

register = template.Library()

@register.filter(name='bahttext')
def to_bahttext(value):
    """
    Converts a number to Thai Baht text.
    Usage: {{ 100.50|bahttext }} -> หนึ่งร้อยบาทห้าสิบสตางค์
    """
    try:
        # bahttext library expects a float or decimal
        return bahttext(float(value))
    except (ValueError, TypeError):
        return value