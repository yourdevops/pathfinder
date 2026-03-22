import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from core.validators import dns_label_validator


class User(AbstractUser):
    """Custom user model with UUID for external references."""

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )
    source = models.CharField(
        max_length=20,
        choices=[("local", "Local"), ("oidc", "OIDC"), ("ldap", "LDAP")],
        default="local",
    )
    external_id = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "core_user"

    def __str__(self):
        return self.username


class Group(models.Model):
    """Custom group model with SystemRole support."""

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(
        max_length=63,
        unique=True,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
    )
    description = models.TextField(blank=True)
    source = models.CharField(
        max_length=20,
        choices=[("local", "Local"), ("oidc", "OIDC"), ("ldap", "LDAP")],
        default="local",
    )
    external_id = models.CharField(max_length=255, blank=True, default="")
    system_roles = models.JSONField(default=list)  # ['admin', 'operator', 'auditor']
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_group"

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    """Many-to-many relationship between User and Group."""

    group = models.ForeignKey("core.Group", on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_group_membership"
        unique_together = ["group", "user"]

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class ApiToken(models.Model):
    """API token for authenticating external API calls (e.g., step validation).

    The `key` field stores a SHA-256 hash of the actual token.
    The raw token is shown only once at creation time.
    """

    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=64, unique=True, db_index=True, help_text="SHA-256 hash of the token")
    key_prefix = models.CharField(max_length=8, blank=True, default="", help_text="First 8 chars for identification")
    name = models.CharField(max_length=100, help_text="Human-readable label for this token")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_api_token"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
