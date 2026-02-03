import uuid

from auditlog.registry import auditlog
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
            ("synced", "Synced"),
            ("out_of_date", "Out of Date"),
        ],
        default="never_pushed",
    )
    ci_manifest_pushed_at = models.DateTimeField(null=True, blank=True)
    ci_manifest_pr_url = models.URLField(max_length=500, blank=True)

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
    def ci_manifest_out_of_date(self):
        """Check if the manifest needs re-pushing."""
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
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_steps_repository"
        ordering = ["name"]
        verbose_name_plural = "steps repositories"

    def __str__(self):
        return self.name


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
        unique_together = [["repository", "directory_name"]]
        ordering = ["phase", "name"]

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
    dev_workflow = models.CharField(
        max_length=50,
        choices=DEV_WORKFLOW_CHOICES,
        default="trunk_based",
        help_text="Development workflow pattern",
    )
    status = models.CharField(
        max_length=20,
        choices=[("published", "Published"), ("draft", "Draft")],
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_project_ci_config"

    def __str__(self):
        return f"CI Config for {self.project.name}"


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
auditlog.register(CIStep)
auditlog.register(CIWorkflow)
auditlog.register(CIWorkflowStep)
auditlog.register(ProjectApprovedWorkflow)
auditlog.register(ProjectCIConfig)
