"""Build polling, verification, and service activation tasks."""

import logging

from django_tasks import task

logger = logging.getLogger(__name__)


def activate_service_on_first_success(build):
    """
    Transition service from draft to active on first successful build.

    No extra query needed: if a prior success existed, the service would
    already be active (there is no active → draft transition).

    Args:
        build: The Build instance that succeeded.
    """
    if build.status != "success":
        return

    service = build.service
    if service.status != "draft":
        return

    service.status = "active"
    service.current_build_id = build.id
    service.save(update_fields=["status", "current_build_id", "updated_at"])
    logger.info("Service %s activated on first successful build %s", service.name, build.id)


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

    # Resolve CI plugin from workflow engine
    engine = workflow.engine
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
        elif version_match.status == CIWorkflowVersion.Status.REVOKED:
            verification_status = "revoked"
        else:
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
        logger.info("Service %s manifest synced (version %s)", service.name, version_match)

    logger.info(
        "Build %s verified: %s (hash=%s..., version=%s)",
        build.id,
        verification_status,
        manifest_hash[:12],
        version_match,
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
        logger.error("Connection %s not found", connection_id)
        return {"error": "Connection not found"}

    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        logger.error("Service %s not found", service_id)
        return {"error": "Service not found"}

    plugin = connection.get_plugin()
    if not plugin:
        logger.error("Plugin not available for connection %s", connection.name)
        return {"error": "Plugin not available"}

    # Fetch run details from GitHub
    try:
        run_data = plugin.get_workflow_run(connection.get_config(), repo_name, run_id)
    except Exception as e:
        logger.exception("Failed to fetch workflow run %s", run_id)
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
            logger.warning("Failed to fetch commit %s: %s", head_sha, e)
            # Continue without commit message - not critical

    # Map GitHub status to our status
    status = plugin.map_run_status(run_data["status"], run_data.get("conclusion"))

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
        ci_run_id=run_id,
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

    # Resolve artifact reference via CI plugin for completed builds
    if status in ("success",) and not artifact_ref:
        from plugins.base import CICapableMixin

        if isinstance(plugin, CICapableMixin):
            try:
                resolved_ref = plugin.resolve_artifact_ref(connection.get_config(), repo_name, run_id)
                if resolved_ref:
                    build.artifact_ref = resolved_ref
                    build.save(update_fields=["artifact_ref"])
                    logger.info("Resolved artifact ref for build %s: %s", build.id, resolved_ref)
            except Exception as e:
                logger.warning("Failed to resolve artifact ref for build %s: %s", build.id, e)

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

    logger.info("Build %s %s: %s", build.id, "created" if created else "updated", status)
    return {"build_id": build.id, "status": status, "created": created}
