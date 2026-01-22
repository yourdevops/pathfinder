import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with UUID for external references."""
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active'
    )
    source = models.CharField(
        max_length=20,
        choices=[('local', 'Local'), ('oidc', 'OIDC'), ('ldap', 'LDAP')],
        default='local'
    )
    external_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'core_user'

    def __str__(self):
        return self.username


class Group(models.Model):
    """Custom group model with SystemRole support."""
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=63, unique=True)  # DNS-compatible
    description = models.TextField(blank=True)
    source = models.CharField(
        max_length=20,
        choices=[('local', 'Local'), ('oidc', 'OIDC'), ('ldap', 'LDAP')],
        default='local'
    )
    external_id = models.CharField(max_length=255, blank=True, null=True)
    system_roles = models.JSONField(default=list)  # ['admin', 'operator', 'auditor']
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_group'

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    """Many-to-many relationship between User and Group."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_group_membership'
        unique_together = ['group', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


# Register models with auditlog
from auditlog.registry import auditlog

auditlog.register(User, exclude_fields=['password', 'last_login'])
auditlog.register(Group)
auditlog.register(GroupMembership)
