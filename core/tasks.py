"""Background tasks for health checks and periodic operations.

Run the worker with: python manage.py db_worker

For periodic health checks, set up a cron job or systemd timer to call
schedule_health_checks periodically.
"""

import logging
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
        connection.save(
            update_fields=["health_status", "last_health_message", "last_health_check"]
        )
        return {"status": "unknown", "error": "Plugin missing"}

    # Run health check
    try:
        config = connection.get_config()
        result = plugin.health_check(config)
    except Exception as e:
        logger.exception(f"Health check failed for connection {connection_id}")
        result = {
            "status": "unhealthy",
            "message": f"Health check error: {str(e)}",
            "details": {},
        }

    # Update connection
    connection.health_status = result["status"]
    connection.last_health_message = result.get("message", "")
    connection.last_health_check = timezone.now()
    connection.save(
        update_fields=["health_status", "last_health_message", "last_health_check"]
    )

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
        check_connection_health.using(run_after=run_after).enqueue(
            connection_id=connection.id
        )
        scheduled += 1

    logger.info(
        f"Scheduled {scheduled} health checks over {interval_seconds}s interval"
    )
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
    from core.models import Service, IntegrationConnection
    from core.git_utils import (
        get_template_variables,
        scaffold_new_repository,
        scaffold_existing_repository,
    )

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
        # Note: Template-based scaffolding. CI Workflow template support to be added in future phase.
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
        service.save(update_fields=["scaffold_status", "scaffold_error", "repo_url"])

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
    from core.models import StepsRepository, RuntimeFamily, CIStep
    from core.git_utils import (
        build_authenticated_git_url,
        clone_repo_shallow,
        cleanup_repo,
        parse_runtimes_yml,
        scan_ci_steps,
    )

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
            auth_url = build_authenticated_git_url(
                repository.git_url, repository.connection
            )

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
        RuntimeFamily.objects.filter(repository=repository).exclude(
            name__in=scanned_runtime_names
        ).delete()

        # Scan CI steps
        steps_data = scan_ci_steps(temp_dir)

        # Get HEAD commit SHA
        head_sha = repo_obj.head.commit.hexsha

        # Create/update CIStep records
        scanned_dir_names = set()
        for step_info in steps_data:
            CIStep.objects.update_or_create(
                repository=repository,
                directory_name=step_info["directory_name"],
                defaults={
                    "name": step_info["name"],
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
            scanned_dir_names.add(step_info["directory_name"])

        # Delete removed steps
        CIStep.objects.filter(repository=repository).exclude(
            directory_name__in=scanned_dir_names
        ).delete()

        # Mark as scanned
        repository.scan_status = "scanned"
        repository.scan_error = ""
        repository.last_scanned_at = timezone.now()
        repository.save(update_fields=["scan_status", "scan_error", "last_scanned_at"])

        logger.info(
            f"Scanned steps repository {repository.name}: "
            f"{len(steps_data)} steps, {len(runtimes_data)} runtimes"
        )
        return {"steps": len(steps_data), "runtimes": len(runtimes_data)}

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
