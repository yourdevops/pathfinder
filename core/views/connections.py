"""Connection management views."""
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from core.models import IntegrationConnection
from core.permissions import OperatorRequiredMixin, IntegrationsReadMixin, has_system_role
from plugins.base import registry


class ConnectionListView(LoginRequiredMixin, ListView):
    """List all integration connections."""
    model = IntegrationConnection
    template_name = 'core/connections/list.html'
    context_object_name = 'connections'

    def get_queryset(self):
        return IntegrationConnection.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plugins'] = registry.all()
        # Group connections by category
        context['scm_connections'] = [c for c in context['connections'] if self._get_category(c) == 'scm']
        context['deploy_connections'] = [c for c in context['connections'] if self._get_category(c) == 'deploy']
        context['other_connections'] = [c for c in context['connections'] if self._get_category(c) not in ('scm', 'deploy')]
        # Add permission context
        context['can_manage'] = (
            has_system_role(self.request.user, 'admin') or
            has_system_role(self.request.user, 'operator')
        )
        context['can_view_details'] = (
            context['can_manage'] or
            has_system_role(self.request.user, 'auditor')
        )
        return context

    def _get_category(self, connection):
        plugin = connection.get_plugin()
        return plugin.category if plugin else 'unknown'


class ConnectionDetailView(LoginRequiredMixin, IntegrationsReadMixin, DetailView):
    """Connection detail page."""
    model = IntegrationConnection
    template_name = 'core/connections/detail.html'
    context_object_name = 'connection'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        connection = self.object
        plugin = connection.get_plugin()
        context['plugin'] = plugin

        # Get config for display (non-sensitive only)
        context['config'] = connection.config
        context['plugin_missing'] = connection.plugin_missing

        # Get usage counts (for Phase 5+)
        context['project_attachments'] = []  # Will be populated in Plan 06
        context['environment_attachments'] = []

        return context


class ConnectionTestView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Test connection health."""

    def post(self, request, uuid):
        connection = get_object_or_404(IntegrationConnection, uuid=uuid)
        plugin = connection.get_plugin()

        if not plugin:
            return JsonResponse({
                'status': 'unknown',
                'message': 'Plugin not available',
            }, status=400)

        # Run health check
        config = connection.get_config()
        result = plugin.health_check(config)

        # Update connection status
        connection.health_status = result['status']
        connection.last_health_check = timezone.now()
        connection.last_health_message = result.get('message', '')
        connection.save(update_fields=['health_status', 'last_health_check', 'last_health_message'])

        # Return result for HTMX or JSON
        if request.headers.get('HX-Request'):
            # Return HTML partial for HTMX
            from django.template.loader import render_to_string
            html = render_to_string('core/connections/_health_status.html', {
                'connection': connection,
                'result': result,
            }, request=request)
            return HttpResponse(html)

        return JsonResponse(result)


class ConnectionDeleteView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Delete a connection."""

    def post(self, request, uuid):
        connection = get_object_or_404(IntegrationConnection, uuid=uuid)

        # Check for usage (will be expanded in Plan 06)
        # For now, allow deletion

        name = connection.name
        connection.delete()
        messages.success(request, f'Connection "{name}" deleted.')
        return redirect('connections:list')


class ConnectionCreateDispatchView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Dispatch to plugin-specific create view."""

    def get(self, request, plugin_name):
        plugin = registry.get(plugin_name)
        if not plugin:
            messages.error(request, f'Plugin "{plugin_name}" not found.')
            return redirect('connections:list')

        # Redirect to plugin-specific create URL
        return redirect(f'{plugin_name}:create')


class PluginListView(LoginRequiredMixin, ListView):
    """List all installed plugins with connection counts."""
    template_name = 'core/connections/plugins.html'
    context_object_name = 'plugins_list'

    def get_queryset(self):
        """Return list of plugin dicts with connection counts."""
        plugins_data = []
        for name, plugin in registry.all().items():
            connection_count = IntegrationConnection.objects.filter(plugin_name=name).count()
            plugins_data.append({
                'name': name,
                'display_name': plugin.display_name,
                'category': plugin.category,
                'connection_count': connection_count,
                'can_remove': connection_count == 0,  # Only removable if no connections
            })
        return plugins_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ['scm', 'deploy', 'ci']  # For filter dropdown
        context['can_manage'] = (
            has_system_role(self.request.user, 'admin') or
            has_system_role(self.request.user, 'operator')
        )
        return context
