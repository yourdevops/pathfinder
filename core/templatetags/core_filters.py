from django import template

register = template.Library()


@register.filter
def strip_git_suffix(url: str) -> str:
    """Remove .git suffix from repository URLs for browser navigation."""
    if url and url.endswith(".git"):
        return url[:-4]
    return url or ""


@register.filter
def format_duration(seconds) -> str:
    """Convert seconds to human-readable duration: '1h 23m', '3m 42s', '8s'."""
    if seconds is None:
        return "-"
    seconds = int(seconds)
    if seconds < 0:
        return "-"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
