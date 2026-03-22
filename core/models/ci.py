import hashlib
import uuid

from django.conf import settings
from django.db import models

from core.validators import dns_label_validator


def compute_manifest_hash(manifest_content: str) -> str:
    """Compute SHA-256 hash of manifest content for build authorization."""
    return hashlib.sha256(manifest_content.encode("utf-8")).hexdigest()


class RuntimeFamily(models.Model):
    """
    A runtime family discovered from a steps repository.

    Examples: python, node, go, java. Each family has a list
    of supported versions.
    """

    id = models.BigAutoField(primary_key=True)
    repository = models.ForeignKey("core.StepsRepository", on_delete=models.CASCADE, related_name="runtimes")
    name = models.CharField(max_length=63)  # e.g., 'python', 'node'
    display_name = models.CharField(max_length=100, blank=True)  # e.g., 'Python', 'Node.js'
    versions = models.JSONField(default=list)  # e.g., ["3.11", "3.12", "3.13"]

    class Meta:
        db_table = "core_runtime_family"
        unique_together = [["repository", "name"]]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.repository.name})"


class CIStep(models.Model):
    """
    A single CI step discovered from a steps repository.

    Each step corresponds to a directory containing an action.yml
    file that defines inputs, outputs, and execution.
    """

    PHASE_CHOICES = [
        ("setup", "Setup"),
        ("build", "Build"),
        ("test", "Test"),
        ("package", "Package"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("archived", "Archived"),
    ]

    CHANGE_TYPE_CHOICES = [
        ("interface", "Interface"),
        ("metadata", "Metadata"),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    repository = models.ForeignKey("core.StepsRepository", on_delete=models.CASCADE, related_name="steps")
    engine = models.CharField(
        max_length=63,
        default="github_actions",
        help_text="CI engine this step belongs to",
    )
    directory_name = models.CharField(max_length=255)  # e.g., 'setup-python'
    name = models.CharField(max_length=255)  # from action.yml 'name'
    description = models.TextField(blank=True)  # from action.yml 'description'
    slug = models.CharField(
        max_length=255,
        blank=True,
        help_text="URL-safe identifier derived from x-pathfinder.name",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path from repo root to the step definition file",
    )
    last_change_type = models.CharField(
        max_length=20,
        blank=True,
        choices=CHANGE_TYPE_CHOICES,
        help_text="Type of change detected in the last scan",
    )
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, blank=True)
    runtime_constraints = models.JSONField(default=dict)  # e.g., {"python": ">=3.10"}
    tags = models.JSONField(default=list)
    produces = models.JSONField(null=True, blank=True)  # e.g., {"type": "container-image"}
    inputs_schema = models.JSONField(default=dict)  # full inputs from action.yml
    outputs_schema = models.JSONField(
        default=dict,
        help_text="Output declarations from step definition (e.g., action.yml outputs block)",
    )
    commit_sha = models.CharField(max_length=40, blank=True)
    raw_metadata = models.JSONField(default=dict)  # full parsed action.yml
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_ci_step"
        ordering = ["phase", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["engine", "slug"],
                name="unique_step_slug_per_engine",
            ),
        ]

    def __str__(self):
        return self.name


class CIWorkflow(models.Model):
    """
    A composed CI workflow made of ordered CI steps.

    Workflows define the full build pipeline for a service:
    setup -> build -> test -> package.
    """

    DEV_WORKFLOW_CHOICES = [
        ("trunk_based", "Trunk-Based Development"),
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
    runtime_family = models.CharField(max_length=63, blank=True)  # deprecated, kept for migration
    runtime_version = models.CharField(max_length=20, blank=True)  # deprecated, kept for migration
    runtime_constraints = models.JSONField(
        default=dict,
        blank=True,
        help_text="Derived runtime version constraints from composed steps. E.g., {'python': '>=3.11', 'node': '>=18'}",
    )
    artifact_type = models.CharField(max_length=50, blank=True)  # derived from last package step
    engine = models.CharField(
        max_length=63,
        default="github_actions",
        help_text="CI engine identifier, set at creation and immutable",
    )
    dev_workflow = models.CharField(
        max_length=50,
        choices=DEV_WORKFLOW_CHOICES,
        default="trunk_based",
        help_text="Development workflow pattern",
    )
    status = models.CharField(
        max_length=20,
        choices=[("published", "Published"), ("draft", "Draft"), ("archived", "Archived")],
        default="published",
    )
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_ci_workflow"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CIWorkflowStep(models.Model):
    """
    An ordered step within a CI workflow.

    Links a CIStep to a CIWorkflow with a specific order
    and optional per-step input configuration overrides.
    """

    id = models.BigAutoField(primary_key=True)
    workflow = models.ForeignKey("core.CIWorkflow", on_delete=models.CASCADE, related_name="workflow_steps")
    step = models.ForeignKey("core.CIStep", on_delete=models.PROTECT, related_name="workflow_usages")
    order = models.IntegerField()
    input_config = models.JSONField(default=dict)  # per-step overrides
    step_commit_sha = models.CharField(
        max_length=40,
        blank=True,
        help_text="CIStep.commit_sha captured when this workflow was last saved.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_ci_workflow_step"
        unique_together = [["workflow", "order"]]
        ordering = ["order"]

    def __str__(self):
        return f"{self.workflow.name} - Step {self.order}: {self.step.name}"


class ProjectApprovedWorkflow(models.Model):
    """
    Links approved CI workflows to a project (M2M through table).

    Project admins approve specific workflows for use by services
    within their project.
    """

    project = models.ForeignKey("core.Project", on_delete=models.CASCADE, related_name="approved_workflows")
    workflow = models.ForeignKey("core.CIWorkflow", on_delete=models.CASCADE, related_name="project_approvals")
    approved_by = models.CharField(max_length=150, blank=True)  # denormalized username
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_project_approved_workflow"
        unique_together = ["project", "workflow"]

    def __str__(self):
        return f"{self.project.name} -> {self.workflow.name}"


class ProjectCIConfig(models.Model):
    """
    Per-project CI configuration (OneToOne).

    Stores project-level CI settings like the default workflow
    and whether to auto-approve all published workflows.
    """

    project = models.OneToOneField("core.Project", on_delete=models.CASCADE, related_name="ci_config")
    default_workflow = models.ForeignKey(
        "core.CIWorkflow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_projects",
    )
    approve_all_published = models.BooleanField(default=False)
    allow_draft_workflows = models.BooleanField(
        default=False,
        help_text="When enabled, services in this project can use draft workflow versions for pipeline testing in non-production environments.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_project_ci_config"

    def __str__(self):
        return f"CI Config for {self.project.name}"


class CIWorkflowVersion(models.Model):
    """
    A versioned snapshot of a CI Workflow manifest.

    Tracks draft/authorized/revoked states. Each published version produces
    an immutable manifest with a content hash used for build authorization.
    See docs/ci-workflows/versioning.md.
    """

    class Status(models.TextChoices):
        DRAFT = "draft"
        AUTHORIZED = "authorized"
        REVOKED = "revoked"

    workflow = models.ForeignKey("core.CIWorkflow", on_delete=models.PROTECT, related_name="versions")
    version = models.CharField(max_length=32, blank=True)  # semver, blank while draft
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    manifest_hash = models.CharField(max_length=64, blank=True)  # SHA-256
    manifest_content = models.TextField(blank=True)  # full manifest text
    changelog = models.TextField(blank=True)  # publish modal changelog summary
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workflow_versions",
    )
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_ci_workflow_version"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow"],
                condition=models.Q(status="draft"),
                name="unique_draft_per_workflow",
            ),
            models.UniqueConstraint(
                fields=["workflow", "version"],
                condition=~models.Q(version=""),
                name="unique_version_per_workflow",
            ),
        ]

    def __str__(self):
        return f"{self.workflow.name} v{self.version or 'draft'} ({self.status})"


class Build(models.Model):
    """
    A CI/CD build for a service.

    Tracks CI engine workflow runs and their status.
    Created via webhook when builds start/complete.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    service = models.ForeignKey("core.Service", on_delete=models.CASCADE, related_name="builds")

    # CI engine identifiers
    ci_run_id = models.BigIntegerField(unique=True, db_index=True)
    run_number = models.IntegerField(null=True, blank=True)

    # Workflow identification (captured at build time for categorization)
    workflow_name = models.CharField(max_length=255, blank=True)

    # Manifest verification fields (build authorization)
    manifest_id = models.CharField(max_length=255, blank=True, db_index=True)
    manifest_hash = models.CharField(max_length=64, blank=True)
    workflow_version = models.ForeignKey(
        "core.CIWorkflowVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="builds",
    )
    verification_status = models.CharField(
        max_length=16,
        choices=[
            ("verified", "Verified"),
            ("draft", "Draft"),
            ("revoked", "Revoked"),
            ("unauthorized", "Unauthorized"),
        ],
        blank=True,
    )

    # Build status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Commit information
    commit_sha = models.CharField(max_length=40, blank=True)
    commit_message = models.TextField(blank=True)
    branch = models.CharField(max_length=100, blank=True)

    # Actor information (who triggered the build)
    author = models.CharField(max_length=150, blank=True)
    author_avatar_url = models.URLField(max_length=500, blank=True)

    # CI job reference
    ci_job_url = models.URLField(max_length=500, blank=True)

    # Failed step information (populated when build fails)
    failed_job_name = models.CharField(max_length=255, blank=True)
    failed_step_name = models.CharField(max_length=255, blank=True)

    # Artifact reference for Phase 7 deployment
    artifact_ref = models.CharField(max_length=255, blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_build"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Build #{self.run_number or self.ci_run_id} ({self.status})"
