"""CI manifest push and webhook registration tasks."""

import logging

from django.utils import timezone
from django_tasks import task

logger = logging.getLogger(__name__)


def _register_webhook(service, connection, repo_url: str) -> bool:
    """Register SCM webhook for build notifications. Returns True on success."""
    from core.git_utils import parse_git_url
    from core.models import SiteConfiguration

    site_config = SiteConfiguration.get_instance()
    if not (site_config and site_config.external_url and repo_url):
        return False

    plugin = connection.get_plugin()
    config = connection.get_config()
    webhook_url = plugin.get_webhook_url(site_config.external_url)
    if not webhook_url:
        return False

    try:
        parsed = parse_git_url(repo_url)
        if not parsed:
            return False
        repo_name = f"{parsed['owner']}/{parsed['repo']}"
        plugin.configure_webhook(config, repo_name, webhook_url, events=["workflow_run", "pull_request"])
        logger.info("Registered webhook for %s", service.name)
        return True
    except Exception as e:
        logger.warning("Failed to register webhook for %s: %s", service.name, e)
        return False


@task(queue_name="repository_scaffolding")
def push_ci_manifest(service_id: int) -> dict:
    """
    Push the CI manifest for a service to its repository via Pull Request.

    Uses manifest_id(workflow) for file path and respects manually-pinned
    ci_workflow_version for versioned manifest generation. Uses a fixed
    branch name "pathfinder/ci-manifest" per repo (digest PR pattern):
    if an open PR already exists on that branch, a new commit is added;
    otherwise a new branch and PR are created.

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
        logger.error("Service %s not found for CI manifest push", service_id)
        return {"error": "Service not found"}

    # Validate workflow is assigned
    if not service.ci_workflow:
        logger.error("Service %s has no CI workflow assigned", service_id)
        return {"error": "No CI workflow assigned"}

    try:
        # Resolve CI plugin from workflow engine
        engine = service.ci_workflow.engine
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
            logger.error("No default SCM connection for project %s", service.project.name)
            service.ci_manifest_status = "out_of_sync"
            service.save(update_fields=["ci_manifest_status"])
            return {"error": "No SCM connection configured"}

        connection = project_connection.connection
        plugin = connection.get_plugin()
        config = connection.get_config()

        if not plugin:
            logger.error("Plugin not available for connection %s", connection.name)
            return {"error": "SCM plugin not available"}

        # Parse repo URL to get owner/repo
        parsed = parse_git_url(service.repo_url)
        if not parsed:
            logger.error("Cannot parse repo URL: %s", service.repo_url)
            return {"error": "Invalid repository URL"}

        repo_name = f"{parsed['owner']}/{parsed['repo']}"
        source_branch = service.repo_branch or "main"

        # Resolve manifest file path from workflow
        manifest_file_path = ci_plugin.manifest_id(service.ci_workflow)

        # Compare with current manifest in repo — skip PR if content already matches
        existing_content = ci_plugin.fetch_manifest_content(config, repo_name, manifest_file_path, source_branch)
        if existing_content is not None and existing_content.rstrip() == manifest_yaml.rstrip():
            logger.info("Manifest already in sync for service %s, skipping PR", service.name)
            service.ci_manifest_status = "synced"
            service.ci_manifest_pushed_at = timezone.now()
            service.save(update_fields=["ci_manifest_status", "ci_manifest_pushed_at"])
            return {"status": "already_synced"}

        # Build version-aware commit message
        version_str = service.ci_workflow_version.version if service.ci_workflow_version else "draft"
        commit_message = f"ci: update {manifest_file_path} to v{version_str}"

        # Digest PR pattern: fixed branch name per repo
        feature_branch = "pathfinder/ci-manifest"

        # Check for existing open PR on this branch
        existing_pr = plugin.find_open_pr(config, repo_name, feature_branch)

        if existing_pr:
            # Open PR exists: add a new commit to the existing branch (no force-push)
            plugin.update_or_create_file(
                config,
                repo_name,
                manifest_file_path,
                manifest_yaml,
                commit_message,
                branch=feature_branch,
            )
            pr_url = existing_pr.get("html_url", "")
            logger.info("Added commit to existing digest PR #%s for %s", existing_pr["number"], service.name)
        else:
            # No open PR: create new branch from default HEAD and open PR
            try:
                plugin.create_branch(config, repo_name, feature_branch, source_branch)
            except Exception:
                # Branch may already exist (closed PR), continue
                logger.info("Branch %s may already exist, continuing", feature_branch)

            # Write manifest file
            plugin.update_or_create_file(
                config,
                repo_name,
                manifest_file_path,
                manifest_yaml,
                commit_message,
                branch=feature_branch,
            )

            # Build runtime display from runtime_constraints
            rc = service.ci_workflow.runtime_constraints or {}
            runtimes_display = ", ".join(f"{k} {v}" for k, v in rc.items()) if rc else "No runtime constraints"

            # Create pull request
            pr_result = plugin.create_pull_request(
                config,
                service.repo_url,
                f"Update CI manifests for {service.project.name}",
                f"Updates CI workflow manifests managed by Pathfinder.\n\n"
                f"Service: **{service.name}**\n"
                f"Workflow: **{service.ci_workflow.name}**\n"
                f"Runtimes: {runtimes_display}\n\n"
                f"Generated by Pathfinder.",
                feature_branch,
                source_branch,
            )
            pr_url = pr_result.get("html_url", "")

        # Register webhook for build notifications
        if _register_webhook(service, connection, service.repo_url):
            service.webhook_registered = True

        # Update service status — PR created/updated but not yet merged
        service.ci_manifest_status = "pending_pr"
        service.ci_manifest_pushed_at = timezone.now()
        service.ci_manifest_pr_url = pr_url
        service.save(
            update_fields=["ci_manifest_status", "ci_manifest_pushed_at", "ci_manifest_pr_url", "webhook_registered"]
        )

        logger.info("Successfully pushed CI manifest for service %s: %s", service.name, pr_url)
        return {"status": "success", "pr_url": pr_url}

    except Exception as e:
        error_msg = str(e)
        logger.exception("Failed to push CI manifest for service %s", service_id)
        return {"status": "failed", "error": error_msg}
