from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from ..decorators import AdminRequiredMixin
from ..forms import RetentionSettingsForm, SiteConfigurationForm
from ..models import SiteConfiguration


class GeneralSettingsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """General settings page - Pathfinder URLs configuration."""

    template_name = "core/settings/general.html"

    def get(self, request):
        config = SiteConfiguration.get_instance()
        form = SiteConfigurationForm(instance=config)
        return render(
            request,
            self.template_name,
            {
                "active_section": "general",
                "form": form,
                "config": config,
            },
        )

    def post(self, request):
        config = SiteConfiguration.get_instance()
        form = SiteConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved successfully.")
            return redirect("settings:general")
        return render(
            request,
            self.template_name,
            {
                "active_section": "general",
                "form": form,
                "config": config,
            },
        )


class UserManagementView(LoginRequiredMixin, AdminRequiredMixin, View):
    """User management hub - links to Users and Groups pages."""

    template_name = "core/settings/user_management.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "active_section": "user_management",
            },
        )


class AuditLogsSettingsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Audit logs settings page."""

    template_name = "core/settings/audit_logs.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "active_section": "audit_logs",
            },
        )


class ApiTokensView(LoginRequiredMixin, AdminRequiredMixin, View):
    """API and tokens management page."""

    template_name = "core/settings/api_tokens.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "active_section": "api_tokens",
            },
        )


class NotificationsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Notification settings page."""

    template_name = "core/settings/notifications.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "active_section": "notifications",
            },
        )


class CIConfigSettingsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """CI Configuration settings page - retention management and manual cleanup trigger."""

    template_name = "core/settings/ci_config.html"

    def get(self, request):
        config = SiteConfiguration.get_instance()
        form = RetentionSettingsForm(instance=config)
        return render(
            request,
            self.template_name,
            {
                "active_section": "settings",
                "active_settings_section": "ci_config",
                "form": form,
                "config": config,
            },
        )

    def post(self, request):
        config = SiteConfiguration.get_instance()
        # Check if this is a cleanup request
        if "run_cleanup" in request.POST:
            from core.tasks import scheduled_cleanup_versions

            scheduled_cleanup_versions.enqueue()
            messages.success(
                request,
                "Version cleanup has been queued. Results will appear shortly.",
            )
            form = RetentionSettingsForm(instance=config)
        else:
            form = RetentionSettingsForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, "Retention settings saved.")
            # else form will show errors
        return render(
            request,
            self.template_name,
            {
                "active_section": "settings",
                "active_settings_section": "ci_config",
                "form": form,
                "config": config,
            },
        )
