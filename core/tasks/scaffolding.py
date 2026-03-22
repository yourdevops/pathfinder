"""Repository scaffolding tasks."""

import logging

from django.utils import timezone
from django_tasks import task

logger = logging.getLogger(__name__)


@task(queue_name="repository_scaffolding")
def scaffold_repository(service_id: int, scm_connection_id: int) -> dict:
    """
    Scaffold repository with template-aware scaffolding.

    For new repos with template: Clone template at tag SHA, apply file tree, include CI manifest.
    For new repos without template: Create bare repo with README + optional CI manifest.
    For existing repos: CI workflow manifest push via separate mechanism (push_ci_manifest task).

    Args:
        service_id: ID of the Service to scaffold
        scm_connection_id: ID of the IntegrationConnection for SCM

    Returns:
        Dict with status and repo/PR URLs
    """
    from core.git_utils import (
        build_authenticated_git_url,
        cleanup_repo,
        clone_repo_full,
        parse_git_url,
        scaffold_new_repository,
        scrub_credentials,
    )
    from core.models import IntegrationConnection, Service, TemplateVersion
    from core.tasks.ci_setup import push_ci_manifest

    template_repo_obj = None
    template_temp_dir = None

    # Get service and connection
    try:
        service = Service.objects.select_related("project", "template", "ci_workflow", "ci_workflow_version").get(
            id=service_id
        )
    except Service.DoesNotExist:
        logger.error("Service %s not found for scaffolding", service_id)
        return {"error": "Service not found"}

    try:
        connection = IntegrationConnection.objects.get(id=scm_connection_id)
    except IntegrationConnection.DoesNotExist:
        logger.error("Connection %s not found for scaffolding", scm_connection_id)
        service.scaffold_status = "failed"
        service.scaffold_error = "SCM connection not found"
        service.save(update_fields=["scaffold_status", "scaffold_error"])
        return {"error": "Connection not found"}

    # Mark as running
    service.scaffold_status = "running"
    service.scaffold_error = ""
    service.save(update_fields=["scaffold_status", "scaffold_error"])

    try:
        if service.repo_is_new:
            # Clone template repo if service has a template and version
            if service.template and service.template_version:
                # Find the TemplateVersion record for the selected tag
                version = TemplateVersion.objects.filter(
                    template=service.template,
                    tag_name=service.template_version,
                ).first()

                if version:
                    # Build auth URL for template repo clone
                    template_auth_url = None
                    if service.template.connection:
                        template_auth_url = build_authenticated_git_url(
                            service.template.git_url, service.template.connection
                        )

                    # Full clone template repo
                    template_repo_obj, template_temp_dir = clone_repo_full(
                        git_url=service.template.git_url,
                        auth_url=template_auth_url,
                    )

                    # Checkout the specific tag commit SHA
                    template_repo_obj.git.checkout(version.commit_sha)
                    logger.info(
                        "Checked out template %s at %s (%s)",
                        service.template.name,
                        service.template_version,
                        version.commit_sha[:8],
                    )

            result = scaffold_new_repository(
                service=service,
                connection=connection,
                template_temp_dir=template_temp_dir,
            )
            # Update service with repo URL
            service.repo_url = result.get("repo_url", "")

            # Mark as success
            service.scaffold_status = "success"
            service.scaffold_error = ""
            update_fields = ["scaffold_status", "scaffold_error", "repo_url"]

            # If CI workflow was included in scaffolding, update manifest status
            if service.ci_workflow:
                service.ci_manifest_pushed_at = timezone.now()
                service.ci_manifest_status = "synced"
                update_fields.extend(["ci_manifest_pushed_at", "ci_manifest_status"])

            if result.get("webhook_registered"):
                service.webhook_registered = True
                update_fields.append("webhook_registered")

            service.save(update_fields=update_fields)

        else:
            # Existing repo: scaffold not needed, but auto-push CI manifest if workflow assigned
            service.scaffold_status = "not_required"
            service.scaffold_error = ""
            service.save(update_fields=["scaffold_status", "scaffold_error"])
            result = {"status": "not_required"}

            if service.ci_workflow:
                push_ci_manifest.enqueue(service_id=service.id)

        # Provision CI variables (non-blocking)
        if service.repo_url and connection:
            from plugins.base import CICapableMixin

            plugin = connection.get_plugin()
            if isinstance(plugin, CICapableMixin):
                try:
                    parsed = parse_git_url(service.repo_url)
                    if parsed:
                        repo_full_name = f"{parsed['owner']}/{parsed['repo']}"
                        ci_vars = {
                            "PTF_PROJECT": service.project.name,
                            "PTF_SERVICE": service.name,
                        }
                        ci_result = plugin.provision_ci_variables(connection.get_config(), repo_full_name, ci_vars)
                        # Check for errors
                        has_errors = any("error" in str(v) for v in ci_result.values())
                        if has_errors:
                            service.ci_variables_status = "failed"
                            service.ci_variables_error = str(ci_result)
                        else:
                            service.ci_variables_status = "provisioned"
                            service.ci_variables_error = ""
                        service.save(update_fields=["ci_variables_status", "ci_variables_error"])
                        logger.info("CI variable provisioning for %s: %s", service.name, ci_result)
                except Exception as e:
                    logger.warning("CI variable provisioning failed for %s: %s", service.name, e)
                    service.ci_variables_status = "failed"
                    service.ci_variables_error = str(e)
                    service.save(update_fields=["ci_variables_status", "ci_variables_error"])

        logger.info("Successfully scaffolded service %s: %s", service.id, service.name)
        return result

    except Exception as e:
        # Mark as failed
        error_msg = scrub_credentials(str(e))
        logger.exception("Failed to scaffold service %s", service_id)
        service.scaffold_status = "failed"
        service.scaffold_error = error_msg
        service.save(update_fields=["scaffold_status", "scaffold_error"])
        return {"status": "failed", "error": error_msg}

    finally:
        if template_repo_obj and template_temp_dir:
            cleanup_repo(template_repo_obj, template_temp_dir)
