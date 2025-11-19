from django import template

register = template.Library()

COLOR_MAP = {
    "#FF0000": "Crimson Red",
    "#FFD700": "Gold",
    "#A9A9A9": "Gray",
    "#000000": "Black",
    "#228B22": "Forest Green",
    "#DAA520": "Goldenrod",
    "#2F4F4F": "Dark Slate Gray",
}

@register.filter
def color_name(hex_code):
    return COLOR_MAP.get(hex_code.upper(), hex_code)
