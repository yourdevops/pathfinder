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
