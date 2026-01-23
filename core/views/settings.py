from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from ..decorators import AdminRequiredMixin


class GeneralSettingsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """General settings page - DevSSP URLs configuration."""
    template_name = 'core/settings/general.html'

    def get(self, request):
        return render(request, self.template_name, {
            'active_section': 'general',
        })


class UserManagementView(LoginRequiredMixin, AdminRequiredMixin, View):
    """User management hub - links to Users and Groups pages."""
    template_name = 'core/settings/user_management.html'

    def get(self, request):
        return render(request, self.template_name, {
            'active_section': 'user_management',
        })


class AuditLogsSettingsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Audit logs settings page."""
    template_name = 'core/settings/audit_logs.html'

    def get(self, request):
        return render(request, self.template_name, {
            'active_section': 'audit_logs',
        })


class ApiTokensView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API and tokens management page."""
    template_name = 'core/settings/api_tokens.html'

    def get(self, request):
        return render(request, self.template_name, {
            'active_section': 'api_tokens',
        })


class NotificationsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Notification settings page."""
    template_name = 'core/settings/notifications.html'

    def get(self, request):
        return render(request, self.template_name, {
            'active_section': 'notifications',
        })
