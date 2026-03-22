import uuid

from django.db import models

from core.validators import dns_label_validator


class Template(models.Model):
    """A service template repository with pathfinder.yaml manifest."""

    SYNC_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("syncing", "Syncing"),
        ("synced", "Synced"),
        ("error", "Error"),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(
        max_length=63,
        unique=True,
        validators=[dns_label_validator],
        help_text="DNS-compatible name from pathfinder.yaml manifest.",
    )
    description = models.TextField(blank=True)
    git_url = models.URLField(max_length=500)
    connection = models.ForeignKey(
        "core.IntegrationConnection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="templates",
    )
    runtimes = models.JSONField(default=list)  # e.g., [{"python": ">=3.11"}]
    required_vars = models.JSONField(default=dict)  # e.g., {"DATABASE_URL": "PostgreSQL connection string"}
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default="pending")
    sync_error = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_synced_sha = models.CharField(max_length=40, blank=True)
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_template"
        ordering = ["name"]

    def __str__(self):
        return self.name


class TemplateVersion(models.Model):
    """A tagged version of a service template."""

    id = models.BigAutoField(primary_key=True)
    template = models.ForeignKey("core.Template", on_delete=models.CASCADE, related_name="versions")
    tag_name = models.CharField(max_length=100)  # e.g., "v2.1.0"
    commit_sha = models.CharField(max_length=40)
    available = models.BooleanField(default=True)  # False if tag disappeared from remote
    synced_at = models.DateTimeField(auto_now_add=True)
    sort_key = models.CharField(max_length=100, blank=True)  # for semver ordering

    class Meta:
        db_table = "core_template_version"
        ordering = ["-sort_key"]
        unique_together = ["template", "tag_name"]

    def __str__(self):
        return f"{self.template.name} {self.tag_name}"


class ProjectTemplateConfig(models.Model):
    """Per-project template configuration (parallels ProjectCIConfig)."""

    project = models.OneToOneField("core.Project", on_delete=models.CASCADE, related_name="template_config")
    default_template = models.ForeignKey(
        "core.Template",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_projects",
    )
    allowed_templates = models.ManyToManyField("core.Template", blank=True, related_name="allowed_in_projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_project_template_config"

    def __str__(self):
        return f"Template Config for {self.project.name}"
