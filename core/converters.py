"""Custom URL path converters."""


class DnsLabelConverter:
    """
    URL path converter for DNS-compatible names (RFC 1123 label format).

    Matches: lowercase letters, numbers, hyphens
    Can start with letter or digit, max 63 characters
    """

    regex = r"[a-z0-9][a-z0-9-]{0,61}[a-z0-9]|[a-z0-9]"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
