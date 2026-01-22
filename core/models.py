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


class Project(models.Model):
    """Project model for organizing deployments and services."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=20, unique=True)  # DNS-compatible
    description = models.TextField(blank=True)
    env_vars = models.JSONField(default=list)  # [{"key": "X", "value": "Y", "lock": false}]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.CharField(max_length=150, blank=True)  # denormalized username
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_project'
        ordering = ['name']

    def __str__(self):
        return self.name


class Environment(models.Model):
    """Environment within a project (dev, staging, prod)."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environments')
    name = models.CharField(max_length=20)  # DNS-compatible, unique within project
    description = models.TextField(blank=True)
    env_vars = models.JSONField(default=list)  # override/extend project env_vars
    is_production = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    order = models.IntegerField(default=10)  # dev=10, staging=20, prod=30
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_environment'
        unique_together = ['project', 'name']
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.project.name}/{self.name}"


class ProjectMembership(models.Model):
    """Links Groups to Projects with project-level roles."""
    PROJECT_ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('contributor', 'Contributor'),
        ('viewer', 'Viewer'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='project_memberships')
    project_role = models.CharField(max_length=20, choices=PROJECT_ROLE_CHOICES)
    added_by = models.CharField(max_length=150, blank=True)  # denormalized username
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_project_membership'
        unique_together = ['project', 'group']

    def __str__(self):
        return f"{self.group.name} -> {self.project.name} ({self.project_role})"


# Register models with auditlog
from auditlog.registry import auditlog

auditlog.register(User, exclude_fields=['password', 'last_login'])
auditlog.register(Group)
auditlog.register(GroupMembership)
auditlog.register(Project)
auditlog.register(Environment)
auditlog.register(ProjectMembership)
