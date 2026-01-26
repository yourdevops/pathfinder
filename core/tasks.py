"""Background tasks for health checks and periodic operations.

Run the worker with: python manage.py db_worker

For periodic health checks, set up a cron job or systemd timer to call
schedule_health_checks periodically.
"""
from django_tasks import task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@task(queue_name='health_checks')
def check_connection_health(connection_id: int) -> dict:
    """
    Check health of a single connection.
    Called by scheduler or manual "Check Now" action.
    """
    from core.models import IntegrationConnection

    try:
        connection = IntegrationConnection.objects.get(id=connection_id)
    except IntegrationConnection.DoesNotExist:
        logger.warning(f'Connection {connection_id} not found for health check')
        return {'error': 'Connection not found'}

    plugin = connection.get_plugin()
    if not plugin:
        connection.health_status = 'unknown'
        connection.last_health_message = 'Plugin not available'
        connection.last_health_check = timezone.now()
        connection.save(update_fields=['health_status', 'last_health_message', 'last_health_check'])
        return {'status': 'unknown', 'error': 'Plugin missing'}

    # Run health check
    try:
        config = connection.get_config()
        result = plugin.health_check(config)
    except Exception as e:
        logger.exception(f'Health check failed for connection {connection_id}')
        result = {
            'status': 'unhealthy',
            'message': f'Health check error: {str(e)}',
            'details': {}
        }

    # Update connection
    connection.health_status = result['status']
    connection.last_health_message = result.get('message', '')
    connection.last_health_check = timezone.now()
    connection.save(update_fields=['health_status', 'last_health_message', 'last_health_check'])

    logger.info(f'Health check for {connection.name}: {result["status"]}')
    return result


@task(queue_name='health_checks')
def schedule_health_checks() -> dict:
    """
    Schedule health checks for all active connections.
    Spreads checks evenly across the interval to avoid load spikes.

    This should be called periodically (e.g., every HEALTH_CHECK_INTERVAL seconds)
    by running: python manage.py db_worker
    """
    from core.models import IntegrationConnection

    interval_seconds = getattr(settings, 'HEALTH_CHECK_INTERVAL', 900)

    connections = IntegrationConnection.objects.filter(status='active')
    count = connections.count()

    if count == 0:
        logger.info('No active connections to check')
        return {'scheduled': 0}

    # Calculate delay between each check to spread evenly
    delay_between = interval_seconds / count

    scheduled = 0
    for i, connection in enumerate(connections):
        # Calculate when this check should run
        run_after = timezone.now() + timedelta(seconds=i * delay_between)
        check_connection_health.using(run_after=run_after).enqueue(connection_id=connection.id)
        scheduled += 1

    logger.info(f'Scheduled {scheduled} health checks over {interval_seconds}s interval')
    return {'scheduled': scheduled, 'interval': interval_seconds}


def check_all_connections_now() -> dict:
    """
    Immediately queue health checks for all active connections.
    Used for manual "Check All" action.
    """
    from core.models import IntegrationConnection

    connections = IntegrationConnection.objects.filter(status='active')
    queued = 0

    for connection in connections:
        check_connection_health.enqueue(connection_id=connection.id)
        queued += 1

    return {'queued': queued}


@task(queue_name='blueprint_sync')
def sync_blueprint(blueprint_id: int) -> dict:
    """
    Sync a blueprint from its Git repository.

    Fetches manifest from repository, updates blueprint fields,
    and syncs version tags.

    Uses GitPython for SCM-agnostic operations (works with GitHub,
    GitLab, Bitbucket, or any Git-compatible server).
    """
    from core.models import Blueprint, BlueprintVersion
    from core.git_utils import (
        clone_repo_shallow,
        read_manifest_from_repo,
        list_tags_from_repo,
        cleanup_repo,
        build_authenticated_git_url,
        parse_version_tag,
    )

    # Get blueprint
    try:
        blueprint = Blueprint.objects.get(id=blueprint_id)
    except Blueprint.DoesNotExist:
        logger.warning(f'Blueprint {blueprint_id} not found for sync')
        return {'error': 'Blueprint not found'}

    # Mark as syncing
    blueprint.sync_status = 'syncing'
    blueprint.sync_error = ''
    blueprint.save(update_fields=['sync_status', 'sync_error'])

    repo = None
    temp_dir = None

    try:
        # Build authenticated URL if connection exists
        if blueprint.connection:
            auth_url = build_authenticated_git_url(blueprint.git_url, blueprint.connection)
        else:
            auth_url = None

        # Clone repository
        logger.info(f'Cloning repository for blueprint {blueprint_id}: {blueprint.git_url}')
        repo, temp_dir = clone_repo_shallow(
            blueprint.git_url,
            blueprint.default_branch,
            auth_url
        )

        # Read manifest
        manifest = read_manifest_from_repo(temp_dir)

        # Update blueprint fields from manifest
        blueprint.name = manifest.get('name', '')
        blueprint.description = manifest.get('description', '')
        blueprint.tags = manifest.get('tags', [])
        blueprint.ci_plugin = manifest.get('ci', {}).get('type', '')

        # Get deploy plugin from required_plugins or type
        deploy_config = manifest.get('deploy', {})
        required_plugins = deploy_config.get('required_plugins', [])
        if required_plugins:
            blueprint.deploy_plugin = required_plugins[0]
        else:
            blueprint.deploy_plugin = deploy_config.get('type', '')

        blueprint.manifest = manifest

        # List and sync tags
        tags = list_tags_from_repo(repo)
        logger.info(f'Found {len(tags)} tags for blueprint {blueprint_id}')

        # Track existing tag names for cleanup
        existing_tag_names = set()

        for tag_info in tags:
            tag_name = tag_info['name']
            commit_sha = tag_info['commit_sha']
            existing_tag_names.add(tag_name)

            # Parse version
            version_info = parse_version_tag(tag_name)

            # Update or create version record
            version, created = BlueprintVersion.objects.update_or_create(
                blueprint=blueprint,
                tag_name=tag_name,
                defaults={
                    'commit_sha': commit_sha,
                    'major': version_info['major'],
                    'minor': version_info['minor'],
                    'patch': version_info['patch'],
                    'prerelease': version_info['prerelease'],
                    'is_prerelease': version_info['is_prerelease'],
                    'sort_key': version_info['sort_key'],
                }
            )

            if created:
                logger.debug(f'Created version {tag_name} for blueprint {blueprint_id}')

        # Remove versions for deleted tags
        deleted_count, _ = BlueprintVersion.objects.filter(
            blueprint=blueprint
        ).exclude(
            tag_name__in=existing_tag_names
        ).delete()

        if deleted_count > 0:
            logger.info(f'Removed {deleted_count} deleted tags from blueprint {blueprint_id}')

        # Mark as synced
        blueprint.sync_status = 'synced'
        blueprint.last_synced_at = timezone.now()
        blueprint.save()

        logger.info(f'Successfully synced blueprint {blueprint_id}: {blueprint.name}')

        return {
            'status': 'synced',
            'name': blueprint.name,
            'versions': len(tags),
        }

    except FileNotFoundError as e:
        # Manifest not found
        error_msg = str(e)
        logger.error(f'Manifest not found for blueprint {blueprint_id}: {error_msg}')
        blueprint.sync_status = 'error'
        blueprint.sync_error = error_msg
        blueprint.save(update_fields=['sync_status', 'sync_error'])
        return {'status': 'error', 'error': error_msg}

    except Exception as e:
        # General error
        error_msg = str(e)
        logger.exception(f'Failed to sync blueprint {blueprint_id}')
        blueprint.sync_status = 'error'
        blueprint.sync_error = error_msg
        blueprint.save(update_fields=['sync_status', 'sync_error'])
        return {'status': 'error', 'error': error_msg}

    finally:
        # Always clean up temp directory
        if repo and temp_dir:
            cleanup_repo(repo, temp_dir)
