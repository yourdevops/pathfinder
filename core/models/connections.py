import uuid

from django.db import models, transaction

from core.validators import dns_label_validator


class IntegrationConnection(models.Model):
    """
    Stores configuration for external integration connections.

    Sensitive configuration fields (tokens, passwords, etc.) are stored
    encrypted in config_encrypted. Non-sensitive fields are stored in config.
    """

    HEALTH_STATUS_CHOICES = [
        ("healthy", "Healthy"),
        ("unhealthy", "Unhealthy"),
        ("unknown", "Unknown"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("disabled", "Disabled"),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(
        max_length=63,
        unique=True,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
    )
    description = models.TextField(blank=True)
    plugin_name = models.CharField(max_length=63)  # References plugin by name

    # Configuration storage
    config = models.JSONField(default=dict)  # Non-sensitive config
    config_encrypted = models.BinaryField(null=True, blank=True)  # Encrypted sensitive fields

    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    health_status = models.CharField(max_length=20, choices=HEALTH_STATUS_CHOICES, default="unknown")
    last_health_check = models.DateTimeField(null=True, blank=True)
    last_health_message = models.TextField(blank=True)

    # Audit fields
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_integration_connection"
        ordering = ["name"]

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

    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, related_name="connections")
    connection = models.ForeignKey(
        "core.IntegrationConnection",
        on_delete=models.CASCADE,
        related_name="project_attachments",
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = "core_project_connection"
        unique_together = ["project", "connection"]

    def __str__(self):
        return f"{self.project.name} -> {self.connection.name}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Ensure only one default per plugin type per project
            if self.is_default:
                plugin = self.connection.get_plugin()
                if plugin:
                    from core.models.projects import Project

                    Project.objects.select_for_update().filter(pk=self.project_id).first()  # advisory lock
                    ProjectConnection.objects.filter(
                        project=self.project,
                        connection__plugin_name=self.connection.plugin_name,
                        is_default=True,
                    ).exclude(pk=self.pk).update(is_default=False)
            super().save(*args, **kwargs)


class EnvironmentConnection(models.Model):
    """Links deploy connections to Environments."""

    environment = models.ForeignKey("core.Environment", on_delete=models.CASCADE, related_name="connections")
    connection = models.ForeignKey(
        "core.IntegrationConnection",
        on_delete=models.CASCADE,
        related_name="environment_attachments",
    )
    is_default = models.BooleanField(default=False)
    config_override = models.JSONField(default=dict, blank=True)  # Environment-specific config
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = "core_environment_connection"
        unique_together = ["environment", "connection"]

    def __str__(self):
        return f"{self.environment} -> {self.connection.name}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Ensure only one default per plugin type per environment
            if self.is_default:
                plugin = self.connection.get_plugin()
                if plugin:
                    from core.models.projects import Environment

                    Environment.objects.select_for_update().filter(pk=self.environment_id).first()  # advisory lock
                    EnvironmentConnection.objects.filter(
                        environment=self.environment,
                        connection__plugin_name=self.connection.plugin_name,
                        is_default=True,
                    ).exclude(pk=self.pk).update(is_default=False)
            super().save(*args, **kwargs)
