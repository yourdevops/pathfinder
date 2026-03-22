"""Health check tasks for integration connections."""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django_scheduled_tasks import cron_task
from django_tasks import task

logger = logging.getLogger(__name__)


def run_plugin_health_check(connection) -> dict:
    """Run plugin health check for a connection and persist the result."""
    plugin = connection.get_plugin()
    if not plugin:
        result = {"status": "unknown", "message": "Plugin not available"}
    else:
        try:
            result = plugin.health_check(connection.get_config())
        except Exception as e:
            logger.exception("Plugin health check failed for connection %s", connection.id)
            result = {"status": "unhealthy", "message": f"Health check error: {e!s}"}

    connection.health_status = result.get("status", "unknown")
    connection.last_health_message = result.get("message", "")
    connection.last_health_check = timezone.now()
    connection.save(update_fields=["health_status", "last_health_message", "last_health_check"])

    logger.info("Health check for %s: %s", connection.name, connection.health_status)
    return result


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
        logger.warning("Connection %s not found for health check", connection_id)
        return {"error": "Connection not found"}

    return run_plugin_health_check(connection)


@cron_task(cron_schedule="*/15 * * * *")
@task(queue_name="health_checks")
def schedule_health_checks() -> dict:
    """
    Schedule health checks for all active connections.
    Spreads checks evenly across the interval to avoid load spikes.

    Runs every 15 minutes via django-scheduled-tasks (db_worker).
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

    logger.info("Scheduled %s health checks over %ss interval", scheduled, interval_seconds)
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
