import json

from django import template

register = template.Library()


@register.filter(name="to_json")
def to_json(value):
    """Serialize a Python value to a JSON string for inline JS use.

    Converts Python dicts/lists to valid JSON (lowercase true/false/null).
    Returns mark_safe since output is intended for inline JS expressions.

    Usage in templates:
        inputs_schema: {{ step.inputs_schema|to_json }}
    """
    if value is None:
        return "{}"
    return json.dumps(value)
