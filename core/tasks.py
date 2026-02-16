"""Background tasks for health checks and periodic operations.

Run the worker with: python manage.py db_worker

For periodic health checks, set up a cron job or systemd timer to call
schedule_health_checks periodically.
"""

import logging
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django_tasks import task

logger = logging.getLogger(__name__)


@task(queue_name="health_checks")
def check_connection_health(connection_id: int) -> dict:
    """
    Check health of a single connection.
    Called by scheduler or manual "Check Now" action.
    """
    from core.models import IntegrationConnection

    try:
        connection = IntegrationConnection.objects.get(id=connection_id)
    except IntegrationConnection.DoesNotExist:
        logger.warning(f"Connection {connection_id} not found for health check")
        return {"error": "Connection not found"}

    plugin = connection.get_plugin()
    if not plugin:
        connection.health_status = "unknown"
        connection.last_health_message = "Plugin not available"
        connection.last_health_check = timezone.now()
        connection.save(update_fields=["health_status", "last_health_message", "last_health_check"])
        return {"status": "unknown", "error": "Plugin missing"}

    # Run health check
    try:
        config = connection.get_config()
        result = plugin.health_check(config)
    except Exception as e:
        logger.exception(f"Health check failed for connection {connection_id}")
        result = {
            "status": "unhealthy",
            "message": f"Health check error: {e!s}",
            "details": {},
        }

    # Update connection
    connection.health_status = result["status"]
    connection.last_health_message = result.get("message", "")
    connection.last_health_check = timezone.now()
    connection.save(update_fields=["health_status", "last_health_message", "last_health_check"])

    logger.info(f"Health check for {connection.name}: {result['status']}")
    return result


@task(queue_name="health_checks")
def schedule_health_checks() -> dict:
    """
    Schedule health checks for all active connections.
    Spreads checks evenly across the interval to avoid load spikes.

    This should be called periodically (e.g., every HEALTH_CHECK_INTERVAL seconds)
    by running: python manage.py db_worker
    """
    from core.models import IntegrationConnection

    interval_seconds = getattr(settings, "HEALTH_CHECK_INTERVAL", 900)

    connections = IntegrationConnection.objects.filter(status="active")
    count = connections.count()

    if count == 0:
        logger.info("No active connections to check")
        return {"scheduled": 0}

    # Calculate delay between each check to spread evenly
    delay_between = interval_seconds / count

    scheduled = 0
    for i, connection in enumerate(connections):
        # Calculate when this check should run
        run_after = timezone.now() + timedelta(seconds=i * delay_between)
        check_connection_health.using(run_after=run_after).enqueue(connection_id=connection.id)
        scheduled += 1

    logger.info(f"Scheduled {scheduled} health checks over {interval_seconds}s interval")
    return {"scheduled": scheduled, "interval": interval_seconds}


def check_all_connections_now() -> dict:
    """
    Immediately queue health checks for all active connections.
    Used for manual "Check All" action.
    """
    from core.models import IntegrationConnection

    connections = IntegrationConnection.objects.filter(status="active")
    queued = 0

    for connection in connections:
        check_connection_health.enqueue(connection_id=connection.id)
        queued += 1

    return {"queued": queued}


@task(queue_name="repository_scaffolding")
def scaffold_repository(service_id: int, scm_connection_id: int) -> dict:
    """
    Scaffold repository from template.

    For new repos: Create repo, push template to main branch.
    For existing repos: Create feature branch, apply template, open PR.

    Args:
        service_id: ID of the Service to scaffold
        scm_connection_id: ID of the IntegrationConnection for SCM

    Returns:
        Dict with status and repo/PR URLs
    """
    from core.git_utils import (
        get_template_variables,
        scaffold_existing_repository,
        scaffold_new_repository,
    )
    from core.models import IntegrationConnection, Service

    # Get service and connection
    try:
        service = Service.objects.select_related("project").get(id=service_id)
    except Service.DoesNotExist:
        logger.error(f"Service {service_id} not found for scaffolding")
        return {"error": "Service not found"}

    try:
        connection = IntegrationConnection.objects.get(id=scm_connection_id)
    except IntegrationConnection.DoesNotExist:
        logger.error(f"Connection {scm_connection_id} not found for scaffolding")
        service.scaffold_status = "failed"
        service.scaffold_error = "SCM connection not found"
        service.save(update_fields=["scaffold_status", "scaffold_error"])
        return {"error": "Connection not found"}

    # Mark as running
    service.scaffold_status = "running"
    service.scaffold_error = ""
    service.save(update_fields=["scaffold_status", "scaffold_error"])

    try:
        # Get template variables
        variables = get_template_variables(service)

        # Scaffold based on mode
        if service.repo_is_new:
            result = scaffold_new_repository(
                service=service,
                connection=connection,
                template_temp_dir=None,
                variables=variables,
            )
            # Update service with repo URL
            service.repo_url = result.get("repo_url", "")
        else:
            result = scaffold_existing_repository(
                service=service,
                connection=connection,
                template_temp_dir=None,
                variables=variables,
            )

        # Mark as success
        service.scaffold_status = "success"
        service.scaffold_error = ""
        update_fields = ["scaffold_status", "scaffold_error", "repo_url"]

        # If CI workflow was included in scaffolding, update manifest status
        if service.ci_workflow:
            service.ci_manifest_pushed_at = timezone.now()
            update_fields.append("ci_manifest_pushed_at")

            if service.repo_is_new:
                # New repo: manifest pushed directly to main
                service.ci_manifest_status = "synced"
                update_fields.append("ci_manifest_status")
            else:
                # Existing repo: manifest pushed via PR — not yet merged
                pr_url = result.get("pr_url", "")
                if pr_url:
                    service.ci_manifest_status = "pending_pr"
                    service.ci_manifest_pr_url = pr_url
                    update_fields.extend(["ci_manifest_status", "ci_manifest_pr_url"])

        service.save(update_fields=update_fields)

        logger.info(f"Successfully scaffolded service {service.id}: {service.name}")
        return result

    except Exception as e:
        # Mark as failed
        error_msg = str(e)
        logger.exception(f"Failed to scaffold service {service_id}")
        service.scaffold_status = "failed"
        service.scaffold_error = error_msg
        service.save(update_fields=["scaffold_status", "scaffold_error"])
        return {"status": "failed", "error": error_msg}


def _derive_step_slug(pathfinder_name: str, directory_name: str) -> str:
    """Derive URL-safe slug from x-pathfinder.name, falling back to directory_name."""
    from django.utils.text import slugify

    name = pathfinder_name or directory_name
    slug = slugify(name)
    if not slug:
        slug = slugify(directory_name)
    return slug


def _classify_change(old_step, new_fields: dict) -> str | None:
    """Compare old step fields with new fields to classify change type.

    Returns 'interface' if inputs/outputs/runtimes/phase changed,
    'metadata' if only tags/description changed, None if no meaningful change.
    """
    interface_fields = {
        "inputs_schema": old_step.inputs_schema,
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
def scan_steps_repository(repository_id: int) -> dict:
    """
    Scan a CI steps repository for step definitions and runtimes.

    Clones the repository, parses runtimes.yml, scans ci-steps/ for
    action.yml files, and creates/updates CIStep and RuntimeFamily records.

    Args:
        repository_id: ID of the StepsRepository to scan

    Returns:
        Dict with counts: {"steps": N, "runtimes": M}
    """
    from core.ci_steps import parse_runtimes_yml
    from core.git_utils import (
        build_authenticated_git_url,
        cleanup_repo,
        clone_repo_full,
    )
    from core.models import CIStep, RuntimeFamily, StepsRepository

    repo_obj = None
    temp_dir = None

    try:
        repository = StepsRepository.objects.get(id=repository_id)
    except StepsRepository.DoesNotExist:
        logger.error(f"StepsRepository {repository_id} not found for scanning")
        return {"error": "Repository not found"}

    # Mark as scanning
    repository.scan_status = "scanning"
    repository.scan_error = ""
    repository.save(update_fields=["scan_status", "scan_error"])

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
        from plugins.base import get_ci_plugin_for_engine

        engine = repository.engine
        ci_plugin = get_ci_plugin_for_engine(engine)
        if ci_plugin:
            raw_steps = discover_steps(temp_dir, ci_plugin.engine_file_name)
        else:
            raw_steps = []
            logger.warning(f"No CI plugin found for engine '{engine}', skipping step scan")

        # Reset last_change_type for all active steps in this repo before scan
        CIStep.objects.filter(repository=repository, status="active").update(last_change_type="")

        scanned_slugs = set()
        stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped_collision": 0, "archived": 0}

        for raw_step in raw_steps:
            step_info = ci_plugin.parse_step_file(raw_step["raw_content"])
            dir_name = os.path.basename(raw_step["directory_path"])
            file_path = raw_step["file_path"]

            # Per-file commit SHA
            per_file_sha = repo_obj.git.log("-1", "--format=%H", "--", file_path).strip()
            if not per_file_sha:
                per_file_sha = repo_obj.head.commit.hexsha  # Fallback

            # Derive slug
            slug = _derive_step_slug(step_info["name"], dir_name)
            if not slug:
                logger.warning(f"Could not derive slug for step in {dir_name}, skipping")
                continue

            scanned_slugs.add(slug)

            # Collision detection: check if slug+engine exists from a DIFFERENT repository
            existing = CIStep.objects.filter(engine=engine, slug=slug).first()
            if existing and existing.repository_id != repository.id:
                logger.warning(
                    f"Slug collision: '{slug}' (engine={engine}) already exists from "
                    f"repository '{existing.repository.name}', skipping step from '{repository.name}'"
                )
                stats["skipped_collision"] += 1
                continue

            # Check same-repo match by slug+engine (normal update path)
            existing_same_repo = CIStep.objects.filter(repository=repository, engine=engine, slug=slug).first()

            if existing_same_repo:
                # SHA unchanged? Skip
                if existing_same_repo.commit_sha == per_file_sha:
                    stats["unchanged"] += 1
                    # Re-activate if it was archived (step file returned)
                    if existing_same_repo.status == "archived":
                        existing_same_repo.status = "active"
                        existing_same_repo.save(update_fields=["status"])
                    continue

                # SHA changed: re-parse and classify
                new_fields = {
                    "inputs_schema": step_info["inputs"],
                    "runtime_constraints": step_info["runtime_constraints"],
                    "produces": step_info["produces"],
                    "phase": step_info["phase"],
                    "tags": step_info["tags"],
                    "description": step_info["description"],
                }
                change_type = _classify_change(existing_same_repo, new_fields)

                # Update existing step
                existing_same_repo.name = step_info["name"] or dir_name
                existing_same_repo.description = step_info["description"]
                existing_same_repo.phase = step_info["phase"]
                existing_same_repo.runtime_constraints = step_info["runtime_constraints"]
                existing_same_repo.tags = step_info["tags"]
                existing_same_repo.produces = step_info["produces"]
                existing_same_repo.inputs_schema = step_info["inputs"]
                existing_same_repo.commit_sha = per_file_sha
                existing_same_repo.raw_metadata = step_info["raw_metadata"]
                existing_same_repo.file_path = file_path
                existing_same_repo.directory_name = dir_name
                existing_same_repo.slug = slug
                existing_same_repo.status = "active"
                existing_same_repo.last_change_type = change_type or ""
                existing_same_repo.save()
                stats["updated"] += 1
            else:
                # New step: create
                CIStep.objects.create(
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
                    commit_sha=per_file_sha,
                    raw_metadata=step_info["raw_metadata"],
                    file_path=file_path,
                    status="active",
                    last_change_type="",
                )
                stats["created"] += 1

        # Archive steps no longer found in repo (soft-delete instead of hard-delete)
        archived_count = (
            CIStep.objects.filter(repository=repository, status="active")
            .exclude(slug__in=scanned_slugs)
            .update(status="archived")
        )
        stats["archived"] = archived_count

        # Mark as scanned
        repository.scan_status = "scanned"
        repository.scan_error = ""
        repository.last_scanned_at = timezone.now()
        repository.save(update_fields=["scan_status", "scan_error", "last_scanned_at"])

        logger.info(
            f"Scanned steps repository {repository.name}: "
            f"{stats['created']} created, {stats['updated']} updated, "
            f"{stats['unchanged']} unchanged, {stats['archived']} archived, "
            f"{stats['skipped_collision']} collisions, {len(runtimes_data)} runtimes"
        )
        return {
            "steps": stats["created"] + stats["updated"] + stats["unchanged"],
            "runtimes": len(runtimes_data),
            **stats,
        }

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Failed to scan steps repository {repository_id}")
        repository.scan_status = "error"
        repository.scan_error = error_msg
        repository.save(update_fields=["scan_status", "scan_error"])
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
    logger.info(f"Cleaned up {deleted_count} unreferenced archived steps")
    return {"deleted": deleted_count}


def activate_service_on_first_success(build):
    """
    Transition service from draft to active on first successful build.

    Args:
        build: The Build instance that succeeded.
    """
    from core.models import Build

    service = build.service
    if service.status != "draft":
        return  # Already active or in error state

    # Check if this is actually the first success
    has_prior_success = Build.objects.filter(service=service, status="success").exclude(id=build.id).exists()

    if has_prior_success:
        return  # Not the first success

    # Activate the service
    service.status = "active"
    service.current_build_id = build.id
    service.save(update_fields=["status", "current_build_id", "updated_at"])
    logger.info(f"Service {service.name} activated on first successful build {build.id}")


@task(queue_name="build_updates")
def verify_build(build_id: int, connection_id: int, repo_name: str) -> dict:
    """
    Verify build manifest against authorized workflow versions.
    Implements the 7-step verification flow from docs/ci-workflows/build-authorization.md.

    Args:
        build_id: ID of the Build to verify.
        connection_id: ID of the IntegrationConnection to use.
        repo_name: Full repository name (owner/repo).

    Returns:
        Dict with verification status or skip/error reason.
    """
    from core.models import Build, CIWorkflowVersion, IntegrationConnection, compute_manifest_hash
    from plugins.base import get_ci_plugin_for_engine

    try:
        build = Build.objects.select_related("service__ci_workflow").get(id=build_id)
    except Build.DoesNotExist:
        return {"error": "Build not found"}

    # Skip if already verified or not terminal
    if build.verification_status:
        return {"skipped": True, "reason": "already verified"}
    if build.status not in ("success", "failed", "cancelled"):
        return {"skipped": True, "reason": "not terminal"}

    service = build.service
    workflow = service.ci_workflow
    if not workflow:
        build.verification_status = "unauthorized"
        build.save(update_fields=["verification_status"])
        return {"status": "unauthorized", "reason": "no workflow assigned"}

    # Resolve CI plugin from workflow's first step engine
    first_step = workflow.workflow_steps.select_related("step").first()
    engine = first_step.step.engine if first_step else "github_actions"
    ci_plugin = get_ci_plugin_for_engine(engine)
    if not ci_plugin:
        build.verification_status = "unauthorized"
        build.save(update_fields=["verification_status"])
        return {"status": "unauthorized", "reason": f"no CI plugin for engine {engine}"}

    # Get manifest_id for this workflow
    m_id = ci_plugin.manifest_id(workflow)
    build.manifest_id = m_id

    # Fetch manifest content at build's commit SHA
    try:
        connection = IntegrationConnection.objects.get(id=connection_id)
        config = connection.get_config()
    except IntegrationConnection.DoesNotExist:
        build.verification_status = "unauthorized"
        build.save(update_fields=["manifest_id", "verification_status"])
        return {"status": "unauthorized", "reason": "connection not found"}

    content = ci_plugin.fetch_manifest_content(config, repo_name, m_id, build.commit_sha)
    if not content:
        build.verification_status = "unauthorized"
        build.save(update_fields=["manifest_id", "verification_status"])
        return {"status": "unauthorized", "reason": "manifest not found at commit"}

    # Compute hash of fetched content (includes header per design doc)
    manifest_hash = compute_manifest_hash(content)
    build.manifest_hash = manifest_hash

    # Look up hash in CIWorkflowVersion for this workflow
    version_match = CIWorkflowVersion.objects.filter(workflow=workflow, manifest_hash=manifest_hash).first()

    if version_match:
        if version_match.status == CIWorkflowVersion.Status.AUTHORIZED:
            verification_status = "verified"
        elif version_match.status == CIWorkflowVersion.Status.DRAFT:
            verification_status = "draft"
        else:  # revoked
            verification_status = "unauthorized"
        build.workflow_version = version_match
    else:
        verification_status = "unauthorized"

    build.verification_status = verification_status
    build.save(update_fields=["manifest_id", "manifest_hash", "workflow_version", "verification_status"])

    # Transition pending_pr → synced when the build's verified version matches
    # the service's pinned version. This confirms the manifest PR was merged
    # and the correct workflow version is now active on the default branch.
    if (
        service.ci_manifest_status == "pending_pr"
        and version_match
        and service.ci_workflow_version_id
        and version_match.id == service.ci_workflow_version_id
        and build.branch == (service.repo_branch or "main")
    ):
        service.ci_manifest_status = "synced"
        service.save(update_fields=["ci_manifest_status"])
        logger.info(f"Service {service.name} manifest synced (version {version_match})")

    logger.info(
        f"Build {build.id} verified: {verification_status} (hash={manifest_hash[:12]}..., version={version_match})"
    )
    return {"status": verification_status, "build_id": build.id}


@task(queue_name="build_updates")
def poll_build_details(
    run_id: int,
    repo_name: str,
    connection_id: int,
    service_id: int,
    artifact_ref: str = "",
) -> dict:
    """
    Poll GitHub API for workflow run details and update Build record.

    Fetches the workflow run details from GitHub, retrieves the commit message,
    and creates or updates the Build record.

    Args:
        run_id: The GitHub workflow run ID.
        repo_name: Full repository name (owner/repo).
        connection_id: ID of the IntegrationConnection to use.
        service_id: ID of the Service associated with the build.
        artifact_ref: Artifact reference for deployment (optional).

    Returns:
        Dict with build_id, status, and created flag.
    """
    from core.models import Build, IntegrationConnection, Service

    try:
        connection = IntegrationConnection.objects.get(id=connection_id)
    except IntegrationConnection.DoesNotExist:
        logger.error(f"Connection {connection_id} not found")
        return {"error": "Connection not found"}

    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        logger.error(f"Service {service_id} not found")
        return {"error": "Service not found"}

    plugin = connection.get_plugin()
    if not plugin:
        logger.error(f"Plugin not available for connection {connection.name}")
        return {"error": "Plugin not available"}

    # Fetch run details from GitHub
    try:
        run_data = plugin.get_workflow_run(connection.get_config(), repo_name, run_id)
    except Exception as e:
        logger.exception(f"Failed to fetch workflow run {run_id}")
        return {"error": str(e)}

    # Fetch commit message from GitHub API
    commit_message = ""
    head_sha = run_data.get("head_sha", "")
    if head_sha:
        try:
            commit_data = plugin.get_commit(connection.get_config(), repo_name, head_sha)
            # Get first line of commit message
            full_message = commit_data.get("message", "")
            commit_message = full_message.split("\n")[0] if full_message else ""
        except Exception as e:
            logger.warning(f"Failed to fetch commit {head_sha}: {e}")
            # Continue without commit message - not critical

    # Map GitHub status to our status
    status = Build.map_github_status(run_data["status"], run_data.get("conclusion"))

    # Extract workflow name (e.g., "ci-python-docker" → "python-docker")
    raw_workflow_name = run_data.get("name", "")
    workflow_name = raw_workflow_name[3:] if raw_workflow_name.startswith("ci-") else raw_workflow_name

    # Calculate duration if completed
    duration = None
    completed_at = None
    if run_data["status"] == "completed" and run_data["created_at"] and run_data["updated_at"]:
        completed_at = run_data["updated_at"]
        duration = int((completed_at - run_data["created_at"]).total_seconds())

    # Update or create Build record
    build, created = Build.objects.update_or_create(
        github_run_id=run_id,
        defaults={
            "service": service,
            "run_number": run_data.get("run_number"),
            "workflow_name": workflow_name,
            "status": status,
            "commit_sha": head_sha,
            "commit_message": commit_message,
            "branch": run_data.get("head_branch", ""),
            "author": run_data.get("actor", {}).get("login", ""),
            "author_avatar_url": run_data.get("actor", {}).get("avatar_url", ""),
            "ci_job_url": run_data.get("html_url", ""),
            "artifact_ref": artifact_ref,
            "started_at": run_data.get("created_at"),
            "completed_at": completed_at,
            "duration_seconds": duration,
        },
    )

    # Activate service on first successful build
    if status == "success":
        activate_service_on_first_success(build)

    # Trigger build verification for terminal builds
    if status in ("success", "failed", "cancelled"):
        verify_build.enqueue(
            build_id=build.id,
            connection_id=connection_id,
            repo_name=repo_name,
        )

    logger.info(f"Build {build.id} {'created' if created else 'updated'}: {status}")
    return {"build_id": build.id, "status": status, "created": created}


@task(queue_name="repository_scaffolding")
def push_ci_manifest(service_id: int) -> dict:
    """
    Push the CI manifest for a service to its repository via Pull Request.

    Uses manifest_id(workflow) for file path and respects manually-pinned
    ci_workflow_version for versioned manifest generation. Creates a feature
    branch and opens a PR with the manifest changes.

    Args:
        service_id: ID of the Service to push the manifest for.

    Returns:
        Dict with status and PR URL, or error information.
    """
    from core.git_utils import parse_git_url
    from core.models import ProjectConnection, Service
    from plugins.base import get_ci_plugin_for_engine

    try:
        service = Service.objects.select_related("project", "ci_workflow", "ci_workflow_version").get(id=service_id)
    except Service.DoesNotExist:
        logger.error(f"Service {service_id} not found for CI manifest push")
        return {"error": "Service not found"}

    # Validate workflow is assigned
    if not service.ci_workflow:
        logger.error(f"Service {service_id} has no CI workflow assigned")
        return {"error": "No CI workflow assigned"}

    try:
        # Resolve CI plugin from workflow steps engine
        first_step = service.ci_workflow.workflow_steps.select_related("step").first()
        engine = first_step.step.engine if first_step else "github_actions"
        ci_plugin = get_ci_plugin_for_engine(engine)
        if not ci_plugin:
            return {"error": f"No CI plugin for engine: {engine}"}

        # Use stored manifest content from pinned version (immutable, hash-verified),
        # or generate fresh draft manifest if no version is pinned
        if service.ci_workflow_version and service.ci_workflow_version.manifest_content:
            manifest_yaml = service.ci_workflow_version.manifest_content
        else:
            manifest_yaml = ci_plugin.generate_manifest(service.ci_workflow, version=None)

        # Resolve SCM connection
        project_connection = (
            ProjectConnection.objects.filter(project=service.project, is_default=True)
            .select_related("connection")
            .first()
        )

        if not project_connection:
            logger.error(f"No default SCM connection for project {service.project.name}")
            service.ci_manifest_status = "out_of_sync"
            service.save(update_fields=["ci_manifest_status"])
            return {"error": "No SCM connection configured"}

        connection = project_connection.connection
        plugin = connection.get_plugin()
        config = connection.get_config()

        if not plugin:
            logger.error(f"Plugin not available for connection {connection.name}")
            return {"error": "SCM plugin not available"}

        # Parse repo URL to get owner/repo
        parsed = parse_git_url(service.repo_url)
        if not parsed:
            logger.error(f"Cannot parse repo URL: {service.repo_url}")
            return {"error": "Invalid repository URL"}

        repo_name = f"{parsed['owner']}/{parsed['repo']}"
        source_branch = service.repo_branch or "main"

        # Use manifest_id (workflow-based) instead of manifest_path (service-based)
        manifest_file_path = ci_plugin.manifest_id(service.ci_workflow)
        commit_message = f"Update CI workflow {service.ci_workflow.name} for {service.name}"

        # PR mode: create feature branch and open PR
        feature_branch = f"pathfinder/ci-manifest-{service.name}"

        # Create feature branch (may already exist)
        try:
            plugin.create_branch(config, repo_name, feature_branch, source_branch)
        except Exception:
            # Branch may already exist, continue
            logger.info(f"Branch {feature_branch} may already exist, continuing")

        # Write manifest file
        plugin.update_or_create_file(
            config,
            repo_name,
            manifest_file_path,
            manifest_yaml,
            commit_message,
            branch=feature_branch,
        )

        # Create pull request
        pr_result = plugin.create_pull_request(
            config,
            service.repo_url,
            f"Update CI workflow {service.ci_workflow.name} for {service.name}",
            f"Updates the CI workflow manifest for service **{service.name}**.\n\n"
            f"Workflow: **{service.ci_workflow.name}** "
            f"({service.ci_workflow.runtime_family} {service.ci_workflow.runtime_version})\n\n"
            f"Generated by Pathfinder.",
            feature_branch,
            source_branch,
        )
        pr_url = pr_result.get("html_url", "")

        # Register webhook for build notifications
        from core.models import SiteConfiguration

        site_config = SiteConfiguration.get_instance()
        if site_config and site_config.external_url:
            webhook_url = f"{site_config.external_url.rstrip('/')}/webhooks/build/"
            try:
                plugin.configure_webhook(
                    config,
                    repo_name,
                    webhook_url,
                    events=["workflow_run"],
                )
                service.webhook_registered = True
                logger.info(f"Registered webhook for service {service.name}")
            except Exception as e:
                # Log but don't fail the manifest push
                logger.warning(f"Failed to register webhook for service {service.name}: {e}")
        else:
            logger.warning(f"External URL not configured, skipping webhook registration for {service.name}")

        # Update service status — PR created but not yet merged
        service.ci_manifest_status = "pending_pr"
        service.ci_manifest_pushed_at = timezone.now()
        service.ci_manifest_pr_url = pr_url
        service.save(
            update_fields=["ci_manifest_status", "ci_manifest_pushed_at", "ci_manifest_pr_url", "webhook_registered"]
        )

        logger.info(f"Successfully pushed CI manifest for service {service.name}: {pr_url}")
        return {"status": "success", "pr_url": pr_url}

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Failed to push CI manifest for service {service_id}")
        return {"status": "failed", "error": error_msg}
