import asyncio
import contextlib
import hashlib
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class ServiceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time service page updates.

    Polls the database every 3 seconds, computes a state hash,
    and sends HTML updates only when the state changes.
    """

    async def connect(self):
        # Reject unauthenticated connections
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        self.user = user
        self.service_id = self.scope["url_route"]["kwargs"]["service_id"]

        # Verify service exists
        if not await self._service_exists():
            await self.close()
            return

        await self.accept()

        self.last_state_hash = None
        self.poll_task = asyncio.create_task(self.poll_loop())

    async def disconnect(self, close_code):
        if hasattr(self, "poll_task"):
            self.poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.poll_task

    async def poll_loop(self):
        """Poll database for state changes and send updates when detected."""
        while True:
            try:
                state = await self.get_current_state()
                if state is None:
                    # Service was deleted
                    await self.close()
                    return

                state_hash = self.compute_hash(state)

                if state_hash != self.last_state_hash:
                    self.last_state_hash = state_hash
                    html = await self.render_updates(state)
                    if html:
                        await self.send(text_data=html)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error in ServiceConsumer poll loop for service %s", self.service_id)

            await asyncio.sleep(3)

    @database_sync_to_async
    def _service_exists(self):
        from core.models import Service

        return Service.objects.filter(id=self.service_id).exists()

    def _can_edit(self, project):
        from core.permissions import get_user_project_role

        role = get_user_project_role(self.user, project)
        return role in ("contributor", "owner")

    @database_sync_to_async
    def get_current_state(self):
        """Fetch all relevant service data for change detection."""
        from core.models import Build, Service

        try:
            service = Service.objects.select_related(
                "ci_workflow",
                "ci_workflow_version",
                "project",
            ).get(id=self.service_id)
        except Service.DoesNotExist:
            return None

        # Fetch last 20 builds
        builds = list(
            Build.objects.filter(service_id=self.service_id)
            .order_by("-created_at")[:20]
            .values(
                "id",
                "status",
                "commit_sha",
                "commit_message",
                "branch",
                "created_at",
                "started_at",
                "duration_seconds",
                "ci_job_url",
                "verification_status",
            )
        )

        # Build stats
        total_count = Build.objects.filter(service_id=self.service_id).count()
        success_count = Build.objects.filter(service_id=self.service_id, status="success").count()
        completed_count = Build.objects.filter(
            service_id=self.service_id, status__in=["success", "failed", "cancelled"]
        ).count()

        # Average duration for completed builds
        completed_builds = Build.objects.filter(
            service_id=self.service_id,
            duration_seconds__isnull=False,
        )
        avg_duration = None
        if completed_builds.exists():
            from django.db.models import Avg

            avg_duration = completed_builds.aggregate(avg=Avg("duration_seconds"))["avg"]

        return {
            "service_status": service.status,
            "scaffold_status": service.scaffold_status,
            "repo_url": service.repo_url,
            "ci_manifest_status": service.ci_manifest_status,
            "ci_manifest_pr_url": service.ci_manifest_pr_url,
            "webhook_registered": service.webhook_registered,
            "ci_variables_status": service.ci_variables_status,
            "ci_workflow_id": service.ci_workflow_id,
            "ci_workflow_name": service.ci_workflow.name if service.ci_workflow else None,
            "ci_workflow_version_id": service.ci_workflow_version_id,
            "builds": builds,
            "stats": {
                "total": total_count,
                "success": success_count,
                "completed": completed_count,
                "avg_duration": avg_duration,
            },
        }

    @staticmethod
    def compute_hash(state):
        """Compute SHA-256 hash of state dict for change detection."""
        return hashlib.sha256(json.dumps(state, default=str, sort_keys=True).encode()).hexdigest()

    def build_template_context(self, state):
        """Build template context matching ServiceDetailView.get_context_data."""
        from core.models import Build, Service

        service = Service.objects.select_related(
            "ci_workflow",
            "ci_workflow_version",
            "project",
        ).get(id=self.service_id)

        project = service.project

        # Build stats
        builds_qs = Build.objects.filter(service=service).order_by("-created_at")
        total_builds = state["stats"]["total"]
        last_build = builds_qs.first()
        completed_count = state["stats"]["completed"]
        success_count = state["stats"]["success"]
        success_rate = round(success_count * 100 / completed_count) if completed_count > 0 else None

        avg_duration = state["stats"]["avg_duration"]
        avg_build_time_seconds = round(avg_duration) if avg_duration else None

        recent_builds = list(builds_qs[:5])

        # CI workflow info
        ci_workflow = service.ci_workflow
        ci_workflow_version = service.ci_workflow_version

        # Builds tab: first page, default sort, no filters
        from django.core.paginator import Paginator

        paginator = Paginator(builds_qs, 20)
        page_obj = paginator.get_page(1)

        # Check running builds and any builds
        has_running_builds = Build.objects.filter(service=service, status__in=["pending", "running"]).exists()
        has_any_builds = total_builds > 0

        # Workflow tabs for builds
        current_workflow_name = ci_workflow.name if ci_workflow else None
        all_builds = Build.objects.filter(service=service)
        if current_workflow_name:
            other_builds_qs = all_builds.exclude(workflow_name=current_workflow_name)
        else:
            other_builds_qs = all_builds
        show_workflow_tabs = other_builds_qs.exists()

        return {
            "service": service,
            "project": project,
            "total_builds": total_builds,
            "last_build": last_build,
            "success_rate": success_rate,
            "avg_build_time_seconds": avg_build_time_seconds,
            "recent_builds": recent_builds,
            "ci_workflow": ci_workflow,
            "ci_workflow_version": ci_workflow_version,
            "show_empty_state": total_builds == 0,
            # Builds tab context
            "builds": page_obj,
            "page_obj": page_obj,
            "has_running_builds": has_running_builds,
            "has_any_builds": has_any_builds,
            "status_filter": "all",
            "sort_by": "-started_at",
            "search_query": "",
            "status_choices": [
                ("all", "All"),
                ("running", "Running"),
                ("success", "Success"),
                ("failed", "Failed"),
            ],
            "show_workflow_tabs": show_workflow_tabs,
            "other_builds_count": other_builds_qs.count(),
            "current_workflow_name": current_workflow_name,
            "active_build_tab": "current",
            # CI manifest status context
            "ci_manifest_status": service.ci_manifest_status,
            "ci_manifest_out_of_sync": service.ci_manifest_out_of_sync,
            "ci_manifest_pr_url": service.ci_manifest_pr_url,
            "ci_manifest_pushed_at": service.ci_manifest_pushed_at,
            "can_edit": self._can_edit(project),
        }

    @database_sync_to_async
    def render_updates(self, state):
        """
        Render HTML for out-of-band swap updates.

        Renders all OOB-targetable partials and concatenates them into a single
        WS message. HTMX silently ignores OOB swaps for IDs not present in DOM.
        """
        ctx = self.build_template_context(state)
        ctx["oob"] = True
        parts = []

        # Dashboard sections
        # Skip empty-state OOB swap: the initial HTTP render has correct can_edit + CSRF.
        # Only swap when builds exist (transitioning empty → stats row).
        if ctx["total_builds"] == 0:
            pass
        else:
            parts.append(render_to_string("core/services/_stats_row.html", ctx))

        parts.append(render_to_string("core/services/_recent_builds.html", ctx))
        parts.append(render_to_string("core/services/_ci_pipeline_card.html", ctx))
        parts.append(render_to_string("core/services/_repo_info_card.html", ctx))

        # Builds tab (always sent; HTMX ignores if element not in DOM)
        parts.append(render_to_string("core/services/_builds_tab.html", ctx))

        # CI manifest status (only when workflow is assigned)
        if ctx["ci_workflow"]:
            parts.append(render_to_string("core/services/_ci_manifest_status.html", ctx))

        # Scaffold badge (only when relevant)
        if state.get("scaffold_status") in ("pending", "running", "failed"):
            scaffold_display = state["scaffold_status"].replace("_", " ").title()
            status_class = {
                "pending": "bg-gray-500/20 text-gray-300",
                "running": "bg-blue-500/20 text-blue-300",
                "failed": "bg-red-500/20 text-red-300",
            }.get(state["scaffold_status"], "bg-gray-500/20 text-gray-300")
            parts.append(
                f'<span id="scaffold-badge" hx-swap-oob="true"'
                f' class="px-2 py-0.5 text-xs rounded {status_class}">'
                f"Scaffold: {scaffold_display}</span>"
            )

        return "".join(parts)
