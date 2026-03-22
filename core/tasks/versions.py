"""Workflow version auto-update and cleanup tasks."""

import logging
from datetime import timedelta

from django.utils import timezone
from django_scheduled_tasks import cron_task
from django_tasks import task

logger = logging.getLogger(__name__)


def is_patch_bump(current_version_str: str, new_version_str: str) -> bool:
    """Check if new_version is a patch bump from current_version (same major.minor)."""
    import semver as semver_lib

    try:
        current = semver_lib.Version.parse(current_version_str)
        new = semver_lib.Version.parse(new_version_str)
        return new.major == current.major and new.minor == current.minor and new > current
    except ValueError:
        return False


@task(queue_name="default")
def auto_update_services(workflow_id: int, version_id: int) -> dict:
    """Auto-update services when a patch version is published.

    Finds services that have auto_update_patch=True and a pinned version
    that is a patch-level predecessor of the new version. Updates their
    ci_workflow_version FK and enqueues push_ci_manifest for each.
    """
    from core.models import CIWorkflow, CIWorkflowVersion, Service
    from core.tasks.ci_setup import push_ci_manifest

    try:
        workflow = CIWorkflow.objects.get(id=workflow_id)
    except CIWorkflow.DoesNotExist:
        logger.error("CIWorkflow %s not found for auto-update", workflow_id)
        return {"error": "Workflow not found"}

    try:
        new_version = CIWorkflowVersion.objects.get(id=version_id)
    except CIWorkflowVersion.DoesNotExist:
        logger.error("CIWorkflowVersion %s not found for auto-update", version_id)
        return {"error": "Version not found"}

    if new_version.status != CIWorkflowVersion.Status.AUTHORIZED:
        logger.info("Version %s is not authorized, skipping auto-update", version_id)
        return {"skipped": True, "reason": "not authorized"}

    # Find eligible services: auto-update enabled, has a pinned version
    services = Service.objects.filter(
        ci_workflow_id=workflow_id,
        auto_update_patch=True,
        ci_workflow_version__isnull=False,
    ).select_related("ci_workflow_version")

    updated = 0
    skipped = 0

    for service in services:
        ci_wf_version = service.ci_workflow_version
        assert ci_wf_version is not None  # filtered by ci_workflow_version__isnull=False
        current_version_str = ci_wf_version.version
        if not current_version_str or not is_patch_bump(current_version_str, new_version.version):
            skipped += 1
            continue

        # Update service FK to new version
        service.ci_workflow_version = new_version
        service.ci_manifest_status = "pending_pr"
        service.save(update_fields=["ci_workflow_version", "ci_manifest_status"])

        # Enqueue manifest push
        push_ci_manifest.enqueue(service_id=service.id)
        updated += 1

        logger.info("Auto-updated service %s: %s -> %s", service.name, current_version_str, new_version.version)

    logger.info("Auto-update complete for workflow %s: %s updated, %s skipped", workflow.name, updated, skipped)
    return {"updated": updated, "skipped": skipped}


def cleanup_old_versions() -> dict:
    """Clean up old version manifest content and delete unreferenced versions.

    Two-phase cleanup:
    1. Clear manifest_content for old authorized/revoked versions (keep hash for verification).
    2. Delete revoked version records that have no Build or Service references
       and are older than the retention period.

    Returns dict with content_cleared and versions_deleted counts.
    """
    from core.models import CIWorkflowVersion, SiteConfiguration

    config = SiteConfiguration.get_instance()
    retention_days = config.version_retention_days
    cutoff = timezone.now() - timedelta(days=retention_days)

    # Step 1: Clear manifest_content for old authorized/revoked versions
    # Keep manifest_hash for verification. Only clear content, not the record.
    old_versions = CIWorkflowVersion.objects.filter(
        status__in=["authorized", "revoked"],
        published_at__lt=cutoff,
        manifest_content__isnull=False,
    ).exclude(manifest_content="")
    content_cleared = old_versions.update(manifest_content="")

    # Step 2: Delete version records that meet ALL criteria:
    # - No Build references (Build.workflow_version FK)
    # - Not pinned by any service (Service.ci_workflow_version FK)
    # - Older than retention period
    # - Status is "revoked" (don't delete authorized versions)
    deleted_count = 0
    for version in CIWorkflowVersion.objects.filter(
        status="revoked",
        published_at__lt=cutoff,
    ):
        if version.builds.exists():
            continue
        if version.pinned_services.exists():
            continue
        version.delete()
        deleted_count += 1

    # Update last_cleanup_at
    config.last_cleanup_at = timezone.now()
    config.save(update_fields=["last_cleanup_at"])

    logger.info("Version cleanup: %s manifest(s) cleared, %s version(s) deleted", content_cleared, deleted_count)
    return {
        "content_cleared": content_cleared,
        "versions_deleted": deleted_count,
    }


@cron_task(cron_schedule="0 3 * * *")
@task(queue_name="default")
def scheduled_cleanup_versions() -> dict:
    """Daily cleanup of old version manifest content and unreferenced versions."""
    return cleanup_old_versions()
