import uuid

from django.db import models

from core.validators import dns_label_validator


class Service(models.Model):
    """Service represents a deployed application within a project."""

    STATUS_CHOICES = [
        ("draft", "Draft"),  # Created but not built yet
        ("active", "Active"),  # Has successful build
        ("error", "Error"),  # Scaffolding or build failed
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, related_name="services")
    name = models.CharField(
        max_length=63,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
    )
    description = models.TextField(blank=True)
    endpoint = models.URLField(
        max_length=500, blank=True, help_text="Service endpoint URL (e.g. https://api.example.com)"
    )

    # Repository configuration
    repo_url = models.URLField(max_length=500, blank=True)
    repo_branch = models.CharField(max_length=100, default="main")
    repo_is_new = models.BooleanField(default=True)  # True if we created the repo

    # Service-level environment variables (merged with project vars at deploy time)
    env_vars = models.JSONField(default=list)  # [{"key": "X", "value": "Y", "lock": bool}]

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    scaffold_status = models.CharField(
        max_length=20,
        choices=[
            ("not_required", "Not Required"),
            ("pending", "Pending"),
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    scaffold_error = models.TextField(blank=True)

    # CI Workflow assignment
    ci_workflow = models.ForeignKey(
        "core.CIWorkflow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )
    ci_manifest_status = models.CharField(
        max_length=20,
        choices=[
            ("never_pushed", "Never Pushed"),
            ("pending_pr", "Pending PR"),
            ("synced", "Synced"),
            ("out_of_sync", "Out of Sync"),
        ],
        default="never_pushed",
    )
    ci_manifest_pushed_at = models.DateTimeField(null=True, blank=True)
    ci_manifest_pr_url = models.URLField(max_length=500, blank=True)
    ci_workflow_version = models.ForeignKey(
        "core.CIWorkflowVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pinned_services",
    )
    ci_manifest_push_method = models.CharField(
        max_length=10,
        choices=[("pr", "Pull Request")],
        default="pr",
    )
    auto_update_patch = models.BooleanField(
        default=True,
        help_text="Automatically update CI manifest when a patch version is published",
    )
    ci_variables_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("provisioned", "Provisioned"),
            ("failed", "Failed"),
        ],
        default="pending",
        blank=True,
    )
    ci_variables_error = models.TextField(blank=True)
    webhook_registered = models.BooleanField(default=False)

    # Service template
    template = models.ForeignKey(
        "core.Template",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )
    template_version = models.CharField(max_length=100, blank=True)  # historical reference, not FK

    # Build tracking (updated by Phase 6)
    current_build_id = models.IntegerField(null=True, blank=True)  # Will be FK to Build in Phase 6
    current_artifact_ref = models.CharField(max_length=255, blank=True)  # e.g., "registry.io/image:tag"

    # Audit fields
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_service"
        unique_together = ["project", "name"]
        ordering = ["name"]

    def __str__(self):
        return f"{self.project.name}/{self.name}"

    @property
    def handler(self):
        """Return service handler: {project-name}-{service-name}."""
        return f"{self.project.name}-{self.name}"

    @property
    def ci_manifest_out_of_sync(self):
        """Check if the manifest needs re-pushing (workflow changed since last push)."""
        if not self.ci_workflow or not self.ci_manifest_pushed_at:
            return False
        return self.ci_workflow.updated_at > self.ci_manifest_pushed_at
