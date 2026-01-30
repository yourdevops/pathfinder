"""Connection management views."""

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import DetailView, ListView, View

from core.models import IntegrationConnection
from core.permissions import (
    IntegrationsReadMixin,
    OperatorRequiredMixin,
    has_system_role,
)
from plugins.base import registry


class ConnectionListView(LoginRequiredMixin, ListView):
    """List all integration connections."""

    model = IntegrationConnection
    template_name = "core/connections/list.html"
    context_object_name = "connections"

    def get_queryset(self):
        return IntegrationConnection.objects.all().order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugins"] = registry.all()

        # Add category attribute to each connection for filtering
        for connection in context["connections"]:
            plugin = connection.get_plugin()
            category = plugin.category if plugin else "unknown"
            # Normalize to 'other' for unknown/unrecognized categories
            if category not in ("scm", "deploy"):
                category = "other"
            connection.category = category

        # Add permission context
        context["can_manage"] = has_system_role(self.request.user, "admin") or has_system_role(
            self.request.user, "operator"
        )
        context["can_view_details"] = context["can_manage"] or has_system_role(self.request.user, "auditor")

        # Lazy health check scheduling: enqueue checks for stale connections
        self._schedule_stale_health_checks()

        return context

    def _schedule_stale_health_checks(self):
        """Enqueue health checks for connections that need them.

        This provides lazy scheduling without needing cron/periodic tasks.
        Checks are enqueued when:
        - Connection has never been checked (last_health_check is None)
        - Last check was more than HEALTH_CHECK_INTERVAL seconds ago
        """
        from core.tasks import check_connection_health

        interval_seconds = getattr(settings, "HEALTH_CHECK_INTERVAL", 900)  # 15 min default
        stale_threshold = timezone.now() - timedelta(seconds=interval_seconds)

        # Find connections needing health check (limit to 5 to avoid flooding)
        stale_connections = IntegrationConnection.objects.filter(status="active").filter(
            # Never checked OR checked before threshold
            Q(last_health_check__isnull=True) | Q(last_health_check__lt=stale_threshold)
        )[:5]

        for connection in stale_connections:
            check_connection_health.enqueue(connection_id=connection.id)


class ConnectionDetailView(LoginRequiredMixin, IntegrationsReadMixin, DetailView):
    """Connection detail page."""

    model = IntegrationConnection
    template_name = "core/connections/detail.html"
    context_object_name = "connection"
    slug_field = "name"
    slug_url_kwarg = "connection_name"
    object: IntegrationConnection  # Type hint for Pylance

    def get_context_data(self, **kwargs):
        from core.forms import ConnectionConfigUpdateForm

        context = super().get_context_data(**kwargs)
        connection = self.object
        plugin = connection.get_plugin()
        context["plugin"] = plugin
        context["plugin_missing"] = connection.plugin_missing

        # Get config schema to know which fields are sensitive
        config_schema = plugin.get_config_schema() if plugin else {}
        context["config_schema"] = config_schema

        # Build display config from actual config (sensitive ones masked)
        full_config = connection.get_config() if plugin else {}

        display_config = {}
        for field_name, value in full_config.items():
            field_info = config_schema.get(field_name, {})
            is_sensitive = field_info.get("sensitive", False)

            if is_sensitive:
                display_config[field_name] = {
                    "value": "••••••••" if value else "Not set",
                    "label": field_info.get("label", field_name),
                    "sensitive": True,
                    "editable": field_info.get("editable", False),
                    "is_set": bool(value),
                }
            elif value or field_info.get("editable"):  # Show non-sensitive values or editable fields
                display_config[field_name] = {
                    "value": value if value else "",
                    "label": field_info.get("label", field_name),
                    "sensitive": False,
                    "editable": field_info.get("editable", False),
                    "is_set": bool(value),
                }
        context["display_config"] = display_config

        # Check for usage
        has_usage = connection.project_attachments.exists() or connection.environment_attachments.exists()
        context["has_usage"] = has_usage

        # Form for editing
        context["config_form"] = ConnectionConfigUpdateForm(connection=connection)

        # Check if user can manage (for edit/delete buttons)
        context["can_manage"] = has_system_role(self.request.user, "admin") or has_system_role(
            self.request.user, "operator"
        )

        return context


class ConnectionTestView(LoginRequiredMixin, View):
    """Test connection health. Available to all authenticated users."""

    def post(self, request, connection_name):
        connection = get_object_or_404(IntegrationConnection, name=connection_name)
        plugin = connection.get_plugin()

        if not plugin:
            return JsonResponse(
                {
                    "status": "unknown",
                    "message": "Plugin not available",
                },
                status=400,
            )

        # Run health check
        config = connection.get_config()
        result = plugin.health_check(config)

        # Update connection status
        connection.health_status = result["status"]
        connection.last_health_check = timezone.now()
        connection.last_health_message = result.get("message", "")
        connection.save(update_fields=["health_status", "last_health_check", "last_health_message"])

        # Return result for HTMX or JSON
        if request.headers.get("HX-Request"):
            from django.template.loader import render_to_string

            # Use different templates for list vs detail view
            hx_target = request.headers.get("HX-Target", "")
            if hx_target == "health-status-detail":
                template = "core/connections/_health_status.html"
            else:
                template = "core/connections/_health_status_row.html"
            html = render_to_string(
                template,
                {
                    "connection": connection,
                    "result": result,
                },
                request=request,
            )
            return HttpResponse(html)

        return JsonResponse(result)


class ConnectionDeleteView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Delete a connection."""

    def post(self, request, connection_name):
        connection = get_object_or_404(IntegrationConnection, name=connection_name)

        # Check for usage - prevent deletion if connection is in use
        has_usage = connection.project_attachments.exists() or connection.environment_attachments.exists()
        if has_usage:
            messages.error(
                request,
                f'Cannot delete "{connection.name}" - it is attached to projects or environments.',
            )
            return redirect("connections:detail", connection_name=connection_name)

        name = connection.name
        connection.delete()
        messages.success(request, f'Connection "{name}" deleted.')
        return redirect("connections:list")


class ConnectionConfigUpdateView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Update connection configuration (description + sensitive fields)."""

    def post(self, request, connection_name):
        from core.forms import ConnectionConfigUpdateForm

        connection = get_object_or_404(IntegrationConnection, name=connection_name)
        form = ConnectionConfigUpdateForm(request.POST, connection=connection)

        if form.is_valid():
            # Update description
            connection.description = form.cleaned_data["description"]

            # Update any editable fields that were provided
            config = connection.get_config()
            config_changed = False
            for field_name in form.editable_fields:
                value = form.cleaned_data.get(field_name, "").strip()
                if value and config.get(field_name) != value:
                    # Update if value provided (for sensitive fields, empty means keep current)
                    config[field_name] = value
                    config_changed = True

            if config_changed:
                connection.set_config(config)

            connection.save()
            messages.success(request, "Connection updated successfully.")
        else:
            # Return errors via messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect("connections:detail", connection_name=connection_name)


class ConnectionCreateDispatchView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Dispatch to plugin-specific create view."""

    def get(self, request, plugin_name):
        plugin = registry.get(plugin_name)
        if not plugin:
            messages.error(request, f'Plugin "{plugin_name}" not found.')
            return redirect("connections:list")

        # Redirect to plugin-specific create URL
        return redirect(f"{plugin_name}:create")


class PluginListView(LoginRequiredMixin, ListView):
    """List all installed plugins with connection counts."""

    template_name = "core/connections/plugins.html"
    context_object_name = "plugins_list"

    def get_queryset(self):
        """Return list of plugin dicts with connection counts."""
        plugins_data = []
        for name, plugin in registry.all().items():
            connection_count = IntegrationConnection.objects.filter(plugin_name=name).count()
            plugins_data.append(
                {
                    "name": name,
                    "display_name": plugin.display_name,
                    "category": plugin.category,
                    "connection_count": connection_count,
                    "can_remove": connection_count == 0,  # Only removable if no connections
                }
            )
        return plugins_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ["scm", "deploy", "ci"]  # For filter dropdown
        context["can_manage"] = has_system_role(self.request.user, "admin") or has_system_role(
            self.request.user, "operator"
        )
        return context
