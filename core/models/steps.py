import uuid

from django.db import models

from core.validators import dns_label_validator


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
        "core.IntegrationConnection",
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
    repository = models.ForeignKey("core.StepsRepository", on_delete=models.CASCADE, related_name="sync_logs")
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
    sync_log = models.ForeignKey("core.StepsRepoSyncLog", on_delete=models.CASCADE, related_name="entries")
    step_slug = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="info")
    message = models.TextField(blank=True)

    class Meta:
        db_table = "core_step_sync_entry"
        ordering = ["id"]

    def __str__(self):
        return f"[{self.severity}] {self.step_slug}: {self.action}"
