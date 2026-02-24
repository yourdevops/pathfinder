import asyncio
import contextlib
import hashlib
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

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
            "ci_manifest_status": service.ci_manifest_status,
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

    @database_sync_to_async
    def render_updates(self, state):
        """
        Render HTML for out-of-band swap updates.

        Placeholder: will be expanded in Plan 03 when template partials are ready.
        Returns empty string for now -- the consumer structure and polling loop
        are fully functional.
        """
        return ""
