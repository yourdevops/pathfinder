from django import template
from auditlog.models import LogEntry

register = template.Library()


@register.filter
def format_audit_entry(entry):
    """Format a LogEntry into human-readable text.

    Examples:
    - "John created user Alice"
    - "John updated group admins"
    - "John deleted user Bob"
    """
    action_map = {
        LogEntry.Action.CREATE: 'created',
        LogEntry.Action.UPDATE: 'updated',
        LogEntry.Action.DELETE: 'deleted',
    }

    actor_name = entry.actor.username if entry.actor else 'System'
    action = action_map.get(entry.action, 'modified')
    model_name = entry.content_type.model if entry.content_type else 'object'
    object_repr = entry.object_repr or 'unknown'

    return f"{actor_name} {action} {model_name} {object_repr}"


@register.filter
def action_badge_class(action):
    """Return CSS classes for action badge."""
    if action == LogEntry.Action.CREATE:
        return 'bg-green-900/30 text-green-400'
    elif action == LogEntry.Action.UPDATE:
        return 'bg-blue-900/30 text-blue-400'
    elif action == LogEntry.Action.DELETE:
        return 'bg-red-900/30 text-red-400'
    return 'bg-dark-border text-dark-muted'


@register.filter
def action_label(action):
    """Return human-readable action label."""
    action_map = {
        LogEntry.Action.CREATE: 'Created',
        LogEntry.Action.UPDATE: 'Updated',
        LogEntry.Action.DELETE: 'Deleted',
    }
    return action_map.get(action, 'Modified')
