"""Background tasks for health checks, scanning, builds, and periodic operations.

Run the worker with: python manage.py db_worker

For periodic health checks, set up a cron job or systemd timer to call
schedule_health_checks periodically.
"""

from core.tasks.builds import activate_service_on_first_success, poll_build_details, verify_build
from core.tasks.ci_setup import _register_webhook, push_ci_manifest
from core.tasks.health import (
    check_all_connections_now,
    check_connection_health,
    run_plugin_health_check,
    schedule_health_checks,
)
from core.tasks.scaffolding import scaffold_repository
from core.tasks.scanning import (
    cleanup_archived_steps,
    scan_steps_repository,
    scheduled_scan_all_steps_repos,
)
from core.tasks.templates import sync_template
from core.tasks.versions import (
    auto_update_services,
    cleanup_old_versions,
    is_patch_bump,
    scheduled_cleanup_versions,
)

__all__ = [
    "_register_webhook",
    "activate_service_on_first_success",
    "auto_update_services",
    "check_all_connections_now",
    "check_connection_health",
    "cleanup_archived_steps",
    "cleanup_old_versions",
    "is_patch_bump",
    "poll_build_details",
    "push_ci_manifest",
    "run_plugin_health_check",
    "scaffold_repository",
    "scan_steps_repository",
    "schedule_health_checks",
    "scheduled_cleanup_versions",
    "scheduled_scan_all_steps_repos",
    "sync_template",
    "verify_build",
]
