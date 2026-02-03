from django import template

register = template.Library()


@register.filter
def strip_git_suffix(url: str) -> str:
    """Remove .git suffix from repository URLs for browser navigation."""
    if url and url.endswith(".git"):
        return url[:-4]
    return url or ""
