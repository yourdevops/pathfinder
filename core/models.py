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


class SiteConfiguration(models.Model):
    """
    Singleton model for site-wide configuration settings.

    Use SiteConfiguration.get_instance() to access the configuration.
    """
    external_url = models.URLField(
        blank=True,
        help_text="Public URL for webhooks and OAuth callbacks (e.g., https://devssp.example.com)"
    )

    class Meta:
        db_table = 'core_site_configuration'
        verbose_name = "Site Configuration"

    def __str__(self):
        return "Site Configuration"

    @classmethod
    def get_instance(cls):
        """Get or create the singleton configuration instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)


class IntegrationConnection(models.Model):
    """
    Stores configuration for external integration connections.

    Sensitive configuration fields (tokens, passwords, etc.) are stored
    encrypted in config_encrypted. Non-sensitive fields are stored in config.
    """
    HEALTH_STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('unhealthy', 'Unhealthy'),
        ('unknown', 'Unknown'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=63, unique=True)  # DNS-compatible
    description = models.TextField(blank=True)
    plugin_name = models.CharField(max_length=63)  # References plugin by name

    # Configuration storage
    config = models.JSONField(default=dict)  # Non-sensitive config
    config_encrypted = models.BinaryField(null=True, blank=True)  # Encrypted sensitive fields

    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    health_status = models.CharField(max_length=20, choices=HEALTH_STATUS_CHOICES, default='unknown')
    last_health_check = models.DateTimeField(null=True, blank=True)
    last_health_message = models.TextField(blank=True)

    # Audit fields
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_integration_connection'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.plugin_name})"

    def set_config(self, full_config: dict):
        """
        Separate and store config, encrypting sensitive fields.

        Sensitive fields are determined by the plugin's is_sensitive_field method.
        """
        from plugins.base import registry
        plugin = registry.get(self.plugin_name)

        sensitive = {}
        non_sensitive = {}

        for key, value in full_config.items():
            if value and plugin and plugin.is_sensitive_field(key):
                sensitive[key] = value
            else:
                non_sensitive[key] = value

        self.config = non_sensitive
        if sensitive:
            from core.encryption import encrypt_config
            self.config_encrypted = encrypt_config(sensitive)
        else:
            self.config_encrypted = None

    def get_config(self) -> dict:
        """Return merged config with decrypted sensitive fields."""
        result = dict(self.config)
        if self.config_encrypted:
            from core.encryption import decrypt_config
            decrypted = decrypt_config(self.config_encrypted)
            result.update(decrypted)
        return result

    def get_plugin(self):
        """Return the plugin instance for this connection."""
        from plugins.base import registry
        return registry.get(self.plugin_name)

    @property
    def plugin_missing(self) -> bool:
        """Check if plugin is no longer available."""
        return self.get_plugin() is None


class ProjectConnection(models.Model):
    """Links SCM/CI connections to Projects."""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='connections'
    )
    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name='project_attachments'
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = 'core_project_connection'
        unique_together = ['project', 'connection']

    def __str__(self):
        return f"{self.project.name} -> {self.connection.name}"

    def save(self, *args, **kwargs):
        # Ensure only one default per plugin type per project
        if self.is_default:
            plugin = self.connection.get_plugin()
            if plugin:
                ProjectConnection.objects.filter(
                    project=self.project,
                    connection__plugin_name=self.connection.plugin_name,
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class EnvironmentConnection(models.Model):
    """Links deploy connections to Environments."""
    environment = models.ForeignKey(
        Environment,
        on_delete=models.CASCADE,
        related_name='connections'
    )
    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name='environment_attachments'
    )
    is_default = models.BooleanField(default=False)
    config_override = models.JSONField(default=dict, blank=True)  # Environment-specific config
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = 'core_environment_connection'
        unique_together = ['environment', 'connection']

    def __str__(self):
        return f"{self.environment} -> {self.connection.name}"

    def save(self, *args, **kwargs):
        # Ensure only one default per plugin type per environment
        if self.is_default:
            plugin = self.connection.get_plugin()
            if plugin:
                EnvironmentConnection.objects.filter(
                    environment=self.environment,
                    connection__plugin_name=self.connection.plugin_name,
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


# Register models with auditlog
from auditlog.registry import auditlog

auditlog.register(User, exclude_fields=['password', 'last_login'])
auditlog.register(Group)
auditlog.register(GroupMembership)
auditlog.register(Project)
auditlog.register(Environment)
auditlog.register(ProjectMembership)
auditlog.register(SiteConfiguration)
auditlog.register(IntegrationConnection, exclude_fields=['config_encrypted'])
auditlog.register(ProjectConnection)
auditlog.register(EnvironmentConnection)
