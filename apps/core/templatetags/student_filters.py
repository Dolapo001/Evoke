# apps/core/templatetags/student_filters.py
from django import template

register = template.Library()

@register.filter
def is_random_id(value):
    """Check if the matric number is a randomly generated ID"""
    return value and value.startswith('RND')

@register.filter
def display_id_type(value):
    """Return the display type for the ID"""
    if value and value.startswith('RND'):
        return "Random ID"
    return "Matric Number"
