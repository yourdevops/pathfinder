from auditlog.models import LogEntry
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.models import Environment, Project, Service


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Stats for quick counts
        context["project_count"] = Project.objects.filter(status="active").count()
        context["environment_count"] = Environment.objects.filter(status="active").count()
        context["service_count"] = Service.objects.filter(status="active").count()

        # Recent activity (last 10 entries)
        # For now, show all activity. Can filter by user's project access later if needed.
        context["recent_activity"] = LogEntry.objects.select_related("actor", "content_type").order_by("-timestamp")[
            :10
        ]

        return context
