"""Validation utilities for DNS-compatible naming."""

import re
from django.core.validators import RegexValidator

# RFC 1123 label: lowercase letters, numbers, hyphens
# Can start with letter or digit (RFC 1123 relaxed RFC 952's letter-only requirement)
# Max 63 chars, no leading/trailing hyphens
# Single character is also valid
DNS_LABEL_REGEX = r"^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$|^[a-z0-9]$"

dns_label_validator = RegexValidator(
    regex=DNS_LABEL_REGEX,
    message="Name must be DNS-compatible: lowercase letters, numbers, and hyphens only. "
    "Max 63 characters, no leading/trailing hyphens.",
    code="invalid_dns_label",
)
