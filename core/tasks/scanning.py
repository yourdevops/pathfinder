"""CI steps repository scanning tasks."""

import logging
import os

from django.utils import timezone
from django_scheduled_tasks import cron_task
from django_tasks import task

logger = logging.getLogger(__name__)


def _classify_change(old_step, new_fields: dict) -> str | None:
    """Compare old step fields with new fields to classify change type.

    Returns 'interface' if inputs/outputs/runtimes/phase changed,
    'metadata' if only tags/description changed, None if no meaningful change.
    """
    interface_fields = {
        "inputs_schema": old_step.inputs_schema,
        "outputs_schema": old_step.outputs_schema,
        "runtime_constraints": old_step.runtime_constraints,
        "produces": old_step.produces,
        "phase": old_step.phase,
    }
    metadata_fields = {
        "tags": old_step.tags,
        "description": old_step.description,
    }

    interface_changed = any(interface_fields.get(k) != new_fields.get(k) for k in interface_fields)
    metadata_changed = any(metadata_fields.get(k) != new_fields.get(k) for k in metadata_fields)

    if interface_changed:
        return "interface"
    if metadata_changed:
        return "metadata"
    return None


@task(queue_name="steps_scan")
def scan_steps_repository(repository_id: int, trigger: str = "manual") -> dict:
    """
    Scan a CI steps repository for step definitions and runtimes.

    Clones the repository, parses runtimes.yml, scans ci-steps/ for
    action.yml files, and creates/updates CIStep and RuntimeFamily records.
    Creates a StepsRepoSyncLog with per-step StepSyncEntry records.

    Args:
        repository_id: ID of the StepsRepository to scan
        trigger: How this scan was initiated ("manual", "webhook", "scheduled")

    Returns:
        Dict with counts: {"steps": N, "runtimes": M, "sync_log_id": N}
    """
    from core.ci_steps import parse_runtimes_yml
    from core.git_utils import (
        build_authenticated_git_url,
        cleanup_repo,
        clone_repo_full,
        parse_git_url,
    )
    from core.models import CIStep, RuntimeFamily, StepsRepository, StepsRepoSyncLog, StepSyncEntry

    repo_obj = None
    temp_dir = None
    sync_log = None

    try:
        repository = StepsRepository.objects.get(id=repository_id)
    except StepsRepository.DoesNotExist:
        logger.error("StepsRepository %s not found for scanning", repository_id)
        return {"error": "Repository not found"}

    # Mark as scanning
    repository.scan_status = "scanning"
    repository.scan_error = ""
    repository.save(update_fields=["scan_status", "scan_error"])

    # Create sync log
    previous_sha = repository.last_scanned_sha or ""
    sync_log = StepsRepoSyncLog.objects.create(
        repository=repository,
        commit_sha="",
        previous_sha=previous_sha,
        status="running",
        started_at=timezone.now(),
        trigger=trigger,
    )

    try:
        # Build authenticated URL if connection is set
        auth_url = None
        if repository.connection:
            auth_url = build_authenticated_git_url(repository.git_url, repository.connection)

        # Clone repository (full history for per-file SHA computation)
        repo_obj, temp_dir = clone_repo_full(
            git_url=repository.git_url,
            branch=repository.default_branch,
            auth_url=auth_url,
        )

        # Get HEAD SHA and update sync log
        head_sha = repo_obj.head.commit.hexsha
        sync_log.commit_sha = head_sha
        sync_log.save(update_fields=["commit_sha"])

        # Skip optimization: SHA unchanged since last scan
        if head_sha == previous_sha:
            sync_log.status = "skipped"
            sync_log.completed_at = timezone.now()
            sync_log.save(update_fields=["status", "completed_at"])
            repository.scan_status = "scanned"
            repository.save(update_fields=["scan_status"])
            cleanup_repo(repo_obj, temp_dir)
            repo_obj = None
            temp_dir = None
            return {"status": "skipped", "sync_log_id": sync_log.id}

        # Branch protection check (non-blocking -- log result but don't abort scan)
        from plugins.base import get_ci_plugin_for_engine

        engine = repository.engine
        ci_plugin = get_ci_plugin_for_engine(engine)

        protection_result = {"valid": False, "message": "No connection configured"}
        if repository.connection and ci_plugin:
            parsed = parse_git_url(repository.git_url)
            if parsed:
                repo_name = f"{parsed['owner']}/{parsed['repo']}"
                config = repository.connection.get_config()
                protection_result = ci_plugin.check_branch_protection(config, repo_name, repository.default_branch)

        sync_log.protection_valid = bool(protection_result.get("valid", False))
        sync_log.save(update_fields=["protection_valid"])
        repository.protection_valid = bool(protection_result.get("valid", False))
        repository.save(update_fields=["protection_valid"])

        if not protection_result.get("valid", False):
            StepSyncEntry.objects.create(
                sync_log=sync_log,
                step_slug="",
                action="skipped",
                severity="warning",
                message=f"Branch protection: {protection_result.get('message', 'unknown')}",
            )

        # Parse runtimes.yml
        runtimes_data = parse_runtimes_yml(temp_dir)

        # Create/update RuntimeFamily records
        scanned_runtime_names = set()
        for family_name, versions in runtimes_data.items():
            RuntimeFamily.objects.update_or_create(
                repository=repository,
                name=family_name,
                defaults={
                    "display_name": family_name.capitalize(),
                    "versions": versions,
                },
            )
            scanned_runtime_names.add(family_name)

        # Delete removed runtimes
        RuntimeFamily.objects.filter(repository=repository).exclude(name__in=scanned_runtime_names).delete()

        # Scan CI steps using engine-agnostic discovery + plugin parsing
        from core.ci_steps import discover_steps

        if not ci_plugin:
            logger.warning("No CI plugin found for engine '%s', skipping step scan", engine)
            raw_steps = []
        else:
            raw_steps = discover_steps(temp_dir, ci_plugin.engine_file_name)

        # Reset last_change_type for all active steps in this repo before scan
        CIStep.objects.filter(repository=repository, status="active").update(last_change_type="")

        # Pre-fetch all existing steps for this engine to avoid N+1 queries.
        # UniqueConstraint(engine, slug) guarantees at most one step per slug.
        existing_steps_by_slug: dict[str, CIStep] = {
            s.slug: s for s in CIStep.objects.filter(engine=engine).select_related("repository")
        }

        scanned_slugs = set()
        stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped_collision": 0, "archived": 0}
        bulk_create_steps: list[CIStep] = []
        bulk_update_steps: list[CIStep] = []
        bulk_reactivate_steps: list[CIStep] = []
        bulk_sync_entries: list[StepSyncEntry] = []

        _update_fields = [
            "name",
            "description",
            "phase",
            "runtime_constraints",
            "tags",
            "produces",
            "inputs_schema",
            "outputs_schema",
            "commit_sha",
            "raw_metadata",
            "file_path",
            "directory_name",
            "slug",
            "status",
            "last_change_type",
            "updated_at",
        ]

        for raw_step in raw_steps:
            assert ci_plugin is not None  # guaranteed: raw_steps is [] when ci_plugin is None
            step_info = ci_plugin.parse_step_file(raw_step["raw_content"])
            dir_name = os.path.basename(raw_step["directory_path"])
            file_path = raw_step["file_path"]

            # Per-file commit SHA
            per_file_sha = repo_obj.git.log("-1", "--format=%H", "--", file_path).strip()
            if not per_file_sha:
                per_file_sha = repo_obj.head.commit.hexsha  # Fallback

            # Derive slug via CI plugin (three-tier: x-pathfinder.name -> native name -> full path)
            slug = ci_plugin.derive_step_slug(raw_step["raw_content"], raw_step["directory_path"])
            if not slug:
                logger.warning("Could not derive slug for step in %s, skipping", dir_name)
                continue

            scanned_slugs.add(slug)

            # Collision detection + same-repo match via pre-fetched dict (O(1) lookup)
            existing = existing_steps_by_slug.get(slug)
            if existing and existing.repository_id != repository.id:
                logger.warning(
                    "Slug collision: '%s' (engine=%s) already exists from repository '%s', skipping step from '%s'",
                    slug,
                    engine,
                    existing.repository.name,
                    repository.name,
                )
                stats["skipped_collision"] += 1
                bulk_sync_entries.append(
                    StepSyncEntry(
                        sync_log=sync_log,
                        step_slug=slug,
                        action="skipped",
                        severity="warning",
                        message=f"Slug collision with repository '{existing.repository.name}'",
                    )
                )
                continue

            # existing is either from this repo or None
            existing_same_repo = existing if existing else None

            if existing_same_repo:
                # SHA unchanged? Skip (no entry -- too noisy)
                if existing_same_repo.commit_sha == per_file_sha:
                    stats["unchanged"] += 1
                    # Re-activate if it was archived (step file returned)
                    if existing_same_repo.status == "archived":
                        existing_same_repo.status = "active"
                        bulk_reactivate_steps.append(existing_same_repo)
                    continue

                # SHA changed: re-parse and classify
                new_fields = {
                    "inputs_schema": step_info["inputs"],
                    "outputs_schema": step_info.get("outputs", {}),
                    "runtime_constraints": step_info["runtime_constraints"],
                    "produces": step_info["produces"],
                    "phase": step_info["phase"],
                    "tags": step_info["tags"],
                    "description": step_info["description"],
                }
                change_type = _classify_change(existing_same_repo, new_fields)

                # Update existing step in-memory; flush via bulk_update later
                existing_same_repo.name = step_info["name"] or dir_name
                existing_same_repo.description = step_info["description"]
                existing_same_repo.phase = step_info["phase"]
                existing_same_repo.runtime_constraints = step_info["runtime_constraints"]
                existing_same_repo.tags = step_info["tags"]
                existing_same_repo.produces = step_info["produces"]
                existing_same_repo.inputs_schema = step_info["inputs"]
                existing_same_repo.outputs_schema = step_info.get("outputs", {})
                existing_same_repo.commit_sha = per_file_sha
                existing_same_repo.raw_metadata = step_info["raw_metadata"]
                existing_same_repo.file_path = file_path
                existing_same_repo.directory_name = dir_name
                existing_same_repo.slug = slug
                existing_same_repo.status = "active"
                existing_same_repo.last_change_type = change_type or ""
                existing_same_repo.updated_at = timezone.now()
                bulk_update_steps.append(existing_same_repo)
                stats["updated"] += 1
                severity = "warning" if change_type == "interface" else "info"
                bulk_sync_entries.append(
                    StepSyncEntry(
                        sync_log=sync_log,
                        step_slug=slug,
                        action="updated",
                        severity=severity,
                        message=f"Change type: {change_type or 'content'}" if change_type else "Content updated",
                    )
                )
            else:
                # New step: collect for bulk_create
                new_step = CIStep(
                    repository=repository,
                    engine=engine,
                    directory_name=dir_name,
                    slug=slug,
                    name=step_info["name"] or dir_name,
                    description=step_info["description"],
                    phase=step_info["phase"],
                    runtime_constraints=step_info["runtime_constraints"],
                    tags=step_info["tags"],
                    produces=step_info["produces"],
                    inputs_schema=step_info["inputs"],
                    outputs_schema=step_info.get("outputs", {}),
                    commit_sha=per_file_sha,
                    raw_metadata=step_info["raw_metadata"],
                    file_path=file_path,
                    status="active",
                    last_change_type="",
                )
                bulk_create_steps.append(new_step)
                # Track in index so later iterations see this step
                existing_steps_by_slug[slug] = new_step
                stats["created"] += 1
                bulk_sync_entries.append(
                    StepSyncEntry(
                        sync_log=sync_log,
                        step_slug=slug,
                        action="added",
                        severity="info",
                        message=f"New step discovered: {step_info['name'] or dir_name}",
                    )
                )

        # Flush bulk operations
        if bulk_create_steps:
            CIStep.objects.bulk_create(bulk_create_steps)
        if bulk_update_steps:
            CIStep.objects.bulk_update(bulk_update_steps, fields=_update_fields)
        if bulk_reactivate_steps:
            CIStep.objects.bulk_update(bulk_reactivate_steps, fields=["status"])

        # Archive steps no longer found in repo (capture slugs before update)
        to_archive_qs = CIStep.objects.filter(repository=repository, status="active").exclude(slug__in=scanned_slugs)
        archived_slugs_list = list(to_archive_qs.values_list("slug", "name"))
        archived_count = to_archive_qs.update(status="archived")
        stats["archived"] = archived_count
        for a_slug, a_name in archived_slugs_list:
            bulk_sync_entries.append(
                StepSyncEntry(
                    sync_log=sync_log,
                    step_slug=a_slug,
                    action="archived",
                    severity="warning",
                    message=f"Step '{a_name}' no longer found in repository",
                )
            )

        # Flush all sync log entries in one INSERT
        if bulk_sync_entries:
            StepSyncEntry.objects.bulk_create(bulk_sync_entries)

        # Finalize sync log
        has_errors = sync_log.entries.filter(severity="error").exists()
        sync_log.status = "partial" if has_errors else "success"
        sync_log.completed_at = timezone.now()
        sync_log.steps_added = stats["created"]
        sync_log.steps_updated = stats["updated"]
        sync_log.steps_archived = stats["archived"]
        sync_log.save()

        # Update repository tracking fields
        repository.last_scanned_sha = head_sha
        repository.scan_status = "scanned"
        repository.scan_error = ""
        repository.last_scanned_at = timezone.now()
        repository.save(update_fields=["scan_status", "scan_error", "last_scanned_at", "last_scanned_sha"])

        logger.info(
            "Scanned steps repository %s: %s created, %s updated, %s unchanged, %s archived, %s collisions, %s runtimes",
            repository.name,
            stats["created"],
            stats["updated"],
            stats["unchanged"],
            stats["archived"],
            stats["skipped_collision"],
            len(runtimes_data),
        )
        return {
            "steps": stats["created"] + stats["updated"] + stats["unchanged"],
            "runtimes": len(runtimes_data),
            "sync_log_id": sync_log.id,
            **stats,
        }

    except Exception as e:
        from core.git_utils import scrub_credentials

        error_msg = scrub_credentials(str(e))
        logger.exception("Failed to scan steps repository %s", repository_id)
        repository.scan_status = "error"
        repository.scan_error = error_msg
        repository.save(update_fields=["scan_status", "scan_error"])
        if sync_log:
            sync_log.status = "failed"
            sync_log.completed_at = timezone.now()
            sync_log.save(update_fields=["status", "completed_at"])
            StepSyncEntry.objects.create(
                sync_log=sync_log,
                step_slug="",
                action="skipped",
                severity="error",
                message=f"Scan failed: {error_msg}",
            )
        return {"error": error_msg}

    finally:
        if repo_obj and temp_dir:
            cleanup_repo(repo_obj, temp_dir)


@task(queue_name="steps_scan")
def cleanup_archived_steps() -> dict:
    """Delete archived steps that are not referenced by any workflow.

    CIWorkflowStep.step has on_delete=PROTECT, so we must check for
    zero references before deleting to avoid ProtectedError.
    """
    from core.models import CIStep, CIWorkflowStep

    referenced_step_ids = CIWorkflowStep.objects.values_list("step_id", flat=True)
    deleted_count, _ = CIStep.objects.filter(status="archived").exclude(id__in=referenced_step_ids).delete()
    logger.info("Cleaned up %s unreferenced archived steps", deleted_count)
    return {"deleted": deleted_count}


@cron_task(cron_schedule="0 2 * * *")
@task(queue_name="steps_scan")
def scheduled_scan_all_steps_repos() -> dict:
    """Daily scan of all steps repositories.

    Runs at 02:00 UTC via django-scheduled-tasks.
    Enqueues individual scan tasks for each repository.
    """
    from core.models import StepsRepository

    repos = StepsRepository.objects.all()
    enqueued = 0
    skipped = 0

    for repo in repos:
        if repo.scan_status == "scanning":
            logger.info("Skipping %s (already scanning)", repo.name)
            skipped += 1
            continue

        scan_steps_repository.enqueue(repository_id=repo.id, trigger="scheduled")
        enqueued += 1

    logger.info("Scheduled scan: enqueued %s, skipped %s", enqueued, skipped)
    return {"enqueued": enqueued, "skipped": skipped}
