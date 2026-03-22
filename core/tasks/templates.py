"""Template syncing tasks."""

import logging

from django.utils import timezone
from django_tasks import task

logger = logging.getLogger(__name__)


@task(queue_name="steps_scan")
def sync_template(template_id: int) -> dict:
    """
    Sync a service template: re-clone repo, refresh manifest metadata and tag list.

    Clones the template repository, re-reads pathfinder.yaml, refreshes
    TemplateVersion records from tags, and flags unavailable tags.

    Args:
        template_id: ID of the Template to sync.

    Returns:
        Dict with counts: {"versions_added": N, "versions_unavailable": M}
    """
    from core.git_utils import (
        build_authenticated_git_url,
        cleanup_repo,
        clone_repo_full,
        list_tags_from_repo,
        parse_version_tag,
        read_pathfinder_manifest,
        scrub_credentials,
    )
    from core.models import Template, TemplateVersion

    repo_obj = None
    temp_dir = None

    try:
        template = Template.objects.get(id=template_id)
    except Template.DoesNotExist:
        logger.error("Template %s not found for sync", template_id)
        return {"error": "Template not found"}

    # Mark as syncing
    template.sync_status = "syncing"
    template.sync_error = ""
    template.save(update_fields=["sync_status", "sync_error"])

    try:
        # Build authenticated URL if connection is set
        auth_url = None
        if template.connection:
            auth_url = build_authenticated_git_url(template.git_url, template.connection)

        # Full clone to list all tags
        repo_obj, temp_dir = clone_repo_full(
            git_url=template.git_url,
            auth_url=auth_url,
        )

        # Get HEAD SHA - skip if unchanged
        head_sha = repo_obj.head.commit.hexsha
        if head_sha == template.last_synced_sha:
            template.sync_status = "synced"
            template.last_synced_at = timezone.now()
            template.save(update_fields=["sync_status", "last_synced_at"])
            cleanup_repo(repo_obj, temp_dir)
            repo_obj = None
            temp_dir = None
            return {"status": "skipped", "reason": "SHA unchanged"}

        # Read and validate pathfinder.yaml
        manifest = read_pathfinder_manifest(temp_dir)

        # Update Template metadata from manifest (name is immutable)
        template.description = manifest.get("description", "")
        template.runtimes = manifest.get("runtimes", [])
        template.required_vars = manifest.get("required_vars", {})
        template.save(update_fields=["description", "runtimes", "required_vars"])

        # List all tags and filter to semver
        tags = list_tags_from_repo(repo_obj)
        remote_tag_names = []
        versions_added = 0

        for tag_info in tags:
            tag_name = tag_info["name"]
            parsed = parse_version_tag(tag_name)
            # Skip non-semver tags (parse_version_tag returns major=0 for non-semver)
            if parsed["prerelease"] == tag_name:
                continue

            remote_tag_names.append(tag_name)

            _, created = TemplateVersion.objects.get_or_create(
                template=template,
                tag_name=tag_name,
                defaults={
                    "commit_sha": tag_info["commit_sha"],
                    "sort_key": parsed["sort_key"],
                    "available": True,
                },
            )
            if created:
                versions_added += 1

        # Mark tags no longer present on remote as unavailable (don't delete)
        versions_unavailable = (
            TemplateVersion.objects.filter(template=template)
            .exclude(tag_name__in=remote_tag_names)
            .update(available=False)
        )

        # Update Template sync status
        template.sync_status = "synced"
        template.last_synced_at = timezone.now()
        template.last_synced_sha = head_sha
        template.save(update_fields=["sync_status", "last_synced_at", "last_synced_sha"])

        logger.info(
            "Synced template %s: %s versions added, %s marked unavailable",
            template.name,
            versions_added,
            versions_unavailable,
        )
        return {"versions_added": versions_added, "versions_unavailable": versions_unavailable}

    except (FileNotFoundError, ValueError) as e:
        # Manifest missing or invalid
        error_msg = str(e)
        logger.warning("Template sync failed for %s: %s", template_id, error_msg)
        template.sync_status = "error"
        template.sync_error = error_msg
        template.save(update_fields=["sync_status", "sync_error"])
        return {"error": error_msg}

    except Exception as e:
        error_msg = scrub_credentials(str(e))
        logger.exception("Failed to sync template %s", template_id)
        template.sync_status = "error"
        template.sync_error = error_msg
        template.save(update_fields=["sync_status", "sync_error"])
        return {"error": error_msg}

    finally:
        if repo_obj and temp_dir:
            cleanup_repo(repo_obj, temp_dir)
