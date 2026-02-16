import hashlib
import uuid

from auditlog.registry import auditlog
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from core.validators import dns_label_validator


def compute_manifest_hash(manifest_content: str) -> str:
    """Compute SHA-256 hash of manifest content for build authorization."""
    return hashlib.sha256(manifest_content.encode("utf-8")).hexdigest()


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

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
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


class Project(models.Model):
    """Project model for organizing deployments and services."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("archived", "Archived"),
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
    env_vars = models.JSONField(default=list)  # [{"key": "X", "value": "Y", "lock": false}]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_by = models.CharField(max_length=150, blank=True)  # denormalized username
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_project"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Environment(models.Model):
    """Environment within a project (dev, staging, prod)."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="environments")
    name = models.CharField(
        max_length=63,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
    )  # unique within project via unique_together
    description = models.TextField(blank=True)
    env_vars = models.JSONField(default=list)  # override/extend project env_vars
    is_production = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    order = models.IntegerField(default=10)  # dev=10, staging=20, prod=30
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_environment"
        unique_together = ["project", "name"]
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.project.name}/{self.name}"


class ProjectMembership(models.Model):
    """Links Groups to Projects with project-level roles."""

    PROJECT_ROLE_CHOICES = [
        ("owner", "Owner"),
        ("contributor", "Contributor"),
        ("viewer", "Viewer"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="project_memberships")
    project_role = models.CharField(max_length=20, choices=PROJECT_ROLE_CHOICES)
    added_by = models.CharField(max_length=150, blank=True)  # denormalized username
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_project_membership"
        unique_together = ["project", "group"]

    def __str__(self):
        return f"{self.group.name} -> {self.project.name} ({self.project_role})"


class SiteConfiguration(models.Model):
    """
    Singleton model for site-wide configuration settings.

    Use SiteConfiguration.get_instance() to access the configuration.
    """

    external_url = models.URLField(
        blank=True,
        help_text="Public URL for webhooks and OAuth callbacks (e.g., https://pathfinder.example.com)",
    )

    class Meta:
        db_table = "core_site_configuration"
        verbose_name = "Site Configuration"

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Get or create the singleton configuration instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="connections")
    connection = models.ForeignKey(
        IntegrationConnection,
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
        # Ensure only one default per plugin type per project
        if self.is_default:
            plugin = self.connection.get_plugin()
            if plugin:
                ProjectConnection.objects.filter(
                    project=self.project,
                    connection__plugin_name=self.connection.plugin_name,
                    is_default=True,
                ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class EnvironmentConnection(models.Model):
    """Links deploy connections to Environments."""

    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="connections")
    connection = models.ForeignKey(
        IntegrationConnection,
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
        # Ensure only one default per plugin type per environment
        if self.is_default:
            plugin = self.connection.get_plugin()
            if plugin:
                EnvironmentConnection.objects.filter(
                    environment=self.environment,
                    connection__plugin_name=self.connection.plugin_name,
                    is_default=True,
                ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Service(models.Model):
    """Service represents a deployed application within a project."""

    STATUS_CHOICES = [
        ("draft", "Draft"),  # Created but not built yet
        ("active", "Active"),  # Has successful build
        ("error", "Error"),  # Scaffolding or build failed
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(
        max_length=63,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
    )
    description = models.TextField(blank=True)

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
        "CIWorkflow",
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
        "CIWorkflowVersion",
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
    webhook_registered = models.BooleanField(default=False)

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

    def get_merged_env_vars(self):
        """Return service env vars merged with project vars."""
        merged = {}

        # Project-level vars first
        for var in self.project.env_vars or []:
            merged[var["key"]] = {
                "key": var["key"],
                "value": var["value"],
                "lock": var.get("lock", False),
                "source": "project",
            }

        # Service-level vars override (unless locked)
        for var in self.env_vars or []:
            key = var["key"]
            if key in merged and merged[key]["lock"]:
                continue  # Can't override locked project vars
            merged[key] = {
                "key": var["key"],
                "value": var["value"],
                "lock": var.get("lock", False),
                "source": "service",
            }

        return list(merged.values())


# --- CI Workflow Domain Models ---


class StepsRepository(models.Model):
    """
    A Git repository containing reusable CI step definitions.

    Each repository is scanned to discover action.yml files
    that define individual CI steps.
    """

    SCAN_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("scanning", "Scanning"),
        ("scanned", "Scanned"),
        ("error", "Error"),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(
        max_length=63,
        unique=True,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
    )
    git_url = models.URLField(max_length=500, unique=True)
    default_branch = models.CharField(max_length=100, default="main")
    engine = models.CharField(
        max_length=63,
        default="github_actions",
        help_text="CI engine identifier, e.g., github_actions",
    )
    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="steps_repositories",
    )
    scan_status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default="pending")
    scan_error = models.TextField(blank=True)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    protection_valid = models.BooleanField(
        default=False,
        help_text="Whether branch protection rules are satisfied on the default branch",
    )
    last_scanned_sha = models.CharField(
        max_length=40,
        blank=True,
        help_text="Commit SHA of the last successful scan",
    )
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_steps_repository"
        ordering = ["name"]
        verbose_name_plural = "steps repositories"

    def __str__(self):
        return self.name


class StepsRepoSyncLog(models.Model):
    """
    Log of a single sync operation on a StepsRepository.

    Created at the start of each scan_steps_repository run,
    finalized with status, timing, and per-step entry counts.
    """

    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("partial", "Partial"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]
    TRIGGER_CHOICES = [
        ("manual", "Manual"),
        ("webhook", "Webhook"),
        ("scheduled", "Scheduled"),
    ]

    id = models.BigAutoField(primary_key=True)
    repository = models.ForeignKey(StepsRepository, on_delete=models.CASCADE, related_name="sync_logs")
    commit_sha = models.CharField(max_length=40, blank=True)
    previous_sha = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    protection_valid = models.BooleanField(default=False)
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="manual")
    steps_added = models.IntegerField(default=0)
    steps_updated = models.IntegerField(default=0)
    steps_archived = models.IntegerField(default=0)

    class Meta:
        db_table = "core_steps_repo_sync_log"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Sync {self.repository.name} @ {self.commit_sha[:8]} ({self.status})"


class StepSyncEntry(models.Model):
    """
    A single entry within a sync log, recording an action taken
    on a specific step (added, updated, archived, skipped).
    """

    ACTION_CHOICES = [
        ("added", "Added"),
        ("updated", "Updated"),
        ("archived", "Archived"),
        ("skipped", "Skipped"),
    ]
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    id = models.BigAutoField(primary_key=True)
    sync_log = models.ForeignKey(StepsRepoSyncLog, on_delete=models.CASCADE, related_name="entries")
    step_slug = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="info")
    message = models.TextField(blank=True)

    class Meta:
        db_table = "core_step_sync_entry"
        ordering = ["id"]

    def __str__(self):
        return f"[{self.severity}] {self.step_slug}: {self.action}"


class RuntimeFamily(models.Model):
    """
    A runtime family discovered from a steps repository.

    Examples: python, node, go, java. Each family has a list
    of supported versions.
    """

    id = models.BigAutoField(primary_key=True)
    repository = models.ForeignKey(StepsRepository, on_delete=models.CASCADE, related_name="runtimes")
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
    repository = models.ForeignKey(StepsRepository, on_delete=models.CASCADE, related_name="steps")
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
    runtime_family = models.CharField(max_length=63)  # e.g., 'python'
    runtime_version = models.CharField(max_length=20)  # e.g., '3.12'
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
    workflow = models.ForeignKey(CIWorkflow, on_delete=models.CASCADE, related_name="workflow_steps")
    step = models.ForeignKey(CIStep, on_delete=models.PROTECT, related_name="workflow_usages")
    order = models.IntegerField()
    input_config = models.JSONField(default=dict)  # per-step overrides
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

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="approved_workflows")
    workflow = models.ForeignKey(CIWorkflow, on_delete=models.CASCADE, related_name="project_approvals")
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

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="ci_config")
    default_workflow = models.ForeignKey(
        CIWorkflow,
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

    workflow = models.ForeignKey(CIWorkflow, on_delete=models.PROTECT, related_name="versions")
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
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="builds")

    # CI engine identifiers
    ci_run_id = models.BigIntegerField(unique=True, db_index=True)
    run_number = models.IntegerField(null=True, blank=True)

    # Workflow identification (captured at build time for categorization)
    workflow_name = models.CharField(max_length=255, blank=True)

    # Manifest verification fields (build authorization)
    manifest_id = models.CharField(max_length=255, blank=True, db_index=True)
    manifest_hash = models.CharField(max_length=64, blank=True)
    workflow_version = models.ForeignKey(
        "CIWorkflowVersion",
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


def get_available_workflows_for_project(project):
    """Return queryset of CI workflows available for a project."""
    try:
        ci_config = project.ci_config
    except ProjectCIConfig.DoesNotExist:
        ci_config = None
    if ci_config and ci_config.approve_all_published:
        return CIWorkflow.objects.filter(status="published")
    approved_ids = project.approved_workflows.values_list("workflow_id", flat=True)
    return CIWorkflow.objects.filter(id__in=approved_ids, status="published")


# Register models with auditlog
auditlog.register(User, exclude_fields=["password", "last_login"])
auditlog.register(Group)
auditlog.register(GroupMembership)
auditlog.register(Project)
auditlog.register(Environment)
auditlog.register(ProjectMembership)
auditlog.register(SiteConfiguration)
auditlog.register(IntegrationConnection, exclude_fields=["config_encrypted"])
auditlog.register(ProjectConnection)
auditlog.register(EnvironmentConnection)
auditlog.register(Service)
auditlog.register(StepsRepository)
auditlog.register(StepsRepoSyncLog)
auditlog.register(StepSyncEntry)
auditlog.register(CIStep)
auditlog.register(CIWorkflow)
auditlog.register(CIWorkflowStep)
auditlog.register(ProjectApprovedWorkflow)
auditlog.register(ProjectCIConfig)
auditlog.register(CIWorkflowVersion)
auditlog.register(Build)
