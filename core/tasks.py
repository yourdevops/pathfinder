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
                # Existing repo: manifest pushed via PR
                pr_url = result.get("pr_url", "")
                if pr_url:
                    service.ci_manifest_status = "synced"
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
        clone_repo_shallow,
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

        # Clone repository
        repo_obj, temp_dir = clone_repo_shallow(
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

        # Get HEAD commit SHA
        head_sha = repo_obj.head.commit.hexsha

        # Create/update CIStep records
        scanned_dir_names = set()
        for raw_step in raw_steps:
            step_info = ci_plugin.parse_step_file(raw_step["raw_content"])
            dir_name = os.path.basename(raw_step["directory_path"])
            CIStep.objects.update_or_create(
                repository=repository,
                directory_name=dir_name,
                defaults={
                    "engine": engine,
                    "name": step_info["name"] or dir_name,
                    "description": step_info["description"],
                    "phase": step_info["phase"],
                    "runtime_constraints": step_info["runtime_constraints"],
                    "tags": step_info["tags"],
                    "produces": step_info["produces"],
                    "inputs_schema": step_info["inputs"],
                    "commit_sha": head_sha,
                    "raw_metadata": step_info["raw_metadata"],
                },
            )
            scanned_dir_names.add(dir_name)

        # Delete removed steps
        CIStep.objects.filter(repository=repository).exclude(directory_name__in=scanned_dir_names).delete()

        # Mark as scanned
        repository.scan_status = "scanned"
        repository.scan_error = ""
        repository.last_scanned_at = timezone.now()
        repository.save(update_fields=["scan_status", "scan_error", "last_scanned_at"])

        logger.info(
            f"Scanned steps repository {repository.name}: {len(scanned_dir_names)} steps, {len(runtimes_data)} runtimes"
        )
        return {"steps": len(scanned_dir_names), "runtimes": len(runtimes_data)}

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

    logger.info(f"Build {build.id} {'created' if created else 'updated'}: {status}")
    return {"build_id": build.id, "status": status, "created": created}


@task(queue_name="repository_scaffolding")
def push_ci_manifest(service_id: int) -> dict:
    """
    Push the CI manifest for a service to its repository.

    Creates a feature branch, writes the generated GitHub Actions manifest file,
    and opens a pull request via the SCM plugin.

    Args:
        service_id: ID of the Service to push the manifest for.

    Returns:
        Dict with status and PR URL, or error information.
    """
    from core.git_utils import parse_git_url
    from core.models import ProjectConnection, Service
    from plugins.base import get_ci_plugin_for_engine

    try:
        service = Service.objects.select_related("project", "ci_workflow").get(id=service_id)
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

        # Generate manifest YAML via plugin
        manifest_yaml = ci_plugin.generate_manifest(service.ci_workflow)

        # Resolve SCM connection
        project_connection = (
            ProjectConnection.objects.filter(project=service.project, is_default=True)
            .select_related("connection")
            .first()
        )

        if not project_connection:
            logger.error(f"No default SCM connection for project {service.project.name}")
            service.ci_manifest_status = "out_of_date"
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
        feature_branch = f"pathfinder/ci-manifest-{service.name}"

        # Create feature branch (may already exist)
        try:
            plugin.create_branch(config, repo_name, feature_branch, source_branch)
        except Exception:
            # Branch may already exist, continue
            logger.info(f"Branch {feature_branch} may already exist, continuing")

        # Write manifest file
        manifest_path = ci_plugin.manifest_path(service)
        plugin.update_or_create_file(
            config,
            repo_name,
            manifest_path,
            manifest_yaml,
            f"Update CI workflow for {service.name}",
            branch=feature_branch,
        )

        # Create pull request
        pr_result = plugin.create_pull_request(
            config,
            service.repo_url,
            f"Update CI workflow for {service.name}",
            f"Updates the CI workflow manifest for service **{service.name}**.\n\n"
            f"Workflow: **{service.ci_workflow.name}** "
            f"({service.ci_workflow.runtime_family} {service.ci_workflow.runtime_version})\n\n"
            f"Generated by Pathfinder.",
            feature_branch,
            source_branch,
        )

        pr_url = pr_result.get("html_url", "")

        # Update service status
        service.ci_manifest_status = "synced"
        service.ci_manifest_pushed_at = timezone.now()
        service.ci_manifest_pr_url = pr_url
        service.save(update_fields=["ci_manifest_status", "ci_manifest_pushed_at", "ci_manifest_pr_url"])

        logger.info(f"Successfully pushed CI manifest for service {service.name}: {pr_url}")
        return {"status": "success", "pr_url": pr_url}

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Failed to push CI manifest for service {service_id}")
        return {"status": "failed", "error": error_msg}
