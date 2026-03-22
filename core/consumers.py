import asyncio
import contextlib
import hashlib
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class BasePollingConsumer(AsyncWebsocketConsumer):
    """Base WebSocket consumer with polling pattern for real-time page updates.

    Subclasses must implement:
        entity_id_kwarg: str -- URL route kwarg name for the entity ID
        _entity_exists(): bool -- check if entity exists in DB
        get_current_state(): dict|None -- fetch current state (None = deleted)
        render_updates(state): str -- render HTML for OOB swap
    """

    entity_id_kwarg: str | None = None  # Override in subclass
    poll_interval = 3  # seconds

    def get_poll_interval(self):
        """Return current poll interval. Override for dynamic intervals."""
        return self.poll_interval

    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        self.user = user
        self.entity_id = self.scope["url_route"]["kwargs"][self.entity_id_kwarg]

        if not await self._entity_exists():
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
                logger.exception(
                    "Error in %s poll loop for %s %s", type(self).__name__, self.entity_id_kwarg, self.entity_id
                )

            await asyncio.sleep(self.get_poll_interval())

    @staticmethod
    def compute_hash(state):
        """Compute SHA-256 hash of state dict for change detection."""
        return hashlib.sha256(json.dumps(state, default=str, sort_keys=True).encode()).hexdigest()


class ServiceConsumer(BasePollingConsumer):
    """WebSocket consumer for real-time service page updates."""

    entity_id_kwarg = "service_id"
    FAST_POLL_INTERVAL = 1  # seconds, for newly created services
    FAST_POLL_DURATION = 600  # 10 minutes after creation

    @property
    def service_id(self):
        return self.entity_id

    @database_sync_to_async
    def _entity_exists(self):
        from core.models import Service

        service = Service.objects.filter(id=self.entity_id).values("created_at").first()
        if service is None:
            return False
        self._service_created_at = service["created_at"]
        return True

    def get_poll_interval(self):
        from django.utils import timezone

        age = (timezone.now() - self._service_created_at).total_seconds()
        if age < self.FAST_POLL_DURATION:
            return self.FAST_POLL_INTERVAL
        return self.poll_interval

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
        parts.append(render_to_string("core/services/_source_code_card.html", ctx))

        # Builds tab (always sent; HTMX ignores if element not in DOM)
        parts.append(render_to_string("core/services/_builds_tab.html", ctx))

        # CI manifest status (only when workflow is assigned)
        if ctx["ci_workflow"]:
            parts.append(render_to_string("core/services/_ci_manifest_status.html", ctx))

        return "".join(parts)


class StepsRepoConsumer(BasePollingConsumer):
    """WebSocket consumer for real-time CI Steps Repository detail page updates."""

    entity_id_kwarg = "repo_id"

    @property
    def repo_id(self):
        return self.entity_id

    @database_sync_to_async
    def _entity_exists(self):
        from core.models import StepsRepository

        return StepsRepository.objects.filter(id=self.entity_id).exists()

    @database_sync_to_async
    def get_current_state(self):
        """Fetch all relevant repo data for change detection."""

        from core.models import CIStep, StepsRepository

        try:
            repo = StepsRepository.objects.select_related("connection").get(id=self.repo_id)
        except StepsRepository.DoesNotExist:
            return None

        active_steps = list(
            CIStep.objects.filter(repository=repo, status="active")
            .order_by("phase", "name")
            .values("id", "name", "phase")
        )

        sync_logs = list(
            repo.sync_logs.order_by("-started_at")[:20].values(
                "id",
                "status",
                "trigger",
                "commit_sha",
                "steps_added",
                "steps_updated",
                "steps_archived",
                "started_at",
            )
        )

        runtime_count = repo.runtimes.count()

        return {
            "scan_status": repo.scan_status,
            "scan_error": repo.scan_error,
            "last_scanned_at": repo.last_scanned_at,
            "protection_valid": repo.protection_valid,
            "last_scanned_sha": repo.last_scanned_sha,
            "active_step_count": len(active_steps),
            "active_steps": active_steps,
            "sync_logs": sync_logs,
            "runtime_count": runtime_count,
        }

    def build_template_context(self, state):
        """Build template context mirroring StepsRepoDetailView.get()."""
        from collections import OrderedDict

        from core.models import CIWorkflow, StepsRepository

        repo = StepsRepository.objects.select_related("connection").get(id=self.repo_id)
        active_steps = repo.steps.filter(status="active").order_by("phase", "name")
        archived_steps = repo.steps.filter(status="archived").order_by("name")
        runtimes = repo.runtimes.all().order_by("name")

        # Group active steps by phase (same logic as view)
        phase_order = ["setup", "test", "build", "package"]
        phase_labels = {
            "setup": "Setup",
            "build": "Build",
            "test": "Test",
            "package": "Package",
        }
        steps_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in active_steps if s.phase == phase]
            if phase_steps:
                steps_by_phase[phase_labels[phase]] = phase_steps
        uncategorized = [s for s in active_steps if s.phase not in phase_order]
        if uncategorized:
            steps_by_phase["Other"] = uncategorized

        workflows_using = CIWorkflow.objects.filter(workflow_steps__step__repository=repo).distinct().order_by("name")

        sync_logs = repo.sync_logs.prefetch_related("entries").order_by("-started_at")[:20]

        return {
            "repo": repo,
            "steps_by_phase": steps_by_phase,
            "total_steps": active_steps.count(),
            "archived_steps": archived_steps,
            "runtimes": runtimes,
            "sync_logs": sync_logs,
            "workflows_using": workflows_using,
            "can_manage": False,
            "can_delete": False,
        }

    @database_sync_to_async
    def render_updates(self, state):
        """
        Render OOB HTML partials for WebSocket push.

        Concatenates all OOB-targetable partials into a single message.
        """
        ctx = self.build_template_context(state)
        ctx["oob"] = True
        parts = []

        parts.append(render_to_string("core/ci_workflows/_scan_status.html", ctx))
        parts.append(render_to_string("core/ci_workflows/_sync_history.html", ctx))
        parts.append(render_to_string("core/ci_workflows/_imported_steps.html", ctx))
        parts.append(render_to_string("core/ci_workflows/_repo_info.html", ctx))

        return "".join(parts)
