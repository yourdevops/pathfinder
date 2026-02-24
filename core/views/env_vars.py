"""Unified env var HTMX views for project, service, and environment levels."""

import re

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from core.models import Environment, Service
from core.permissions import ProjectContributorMixin, ProjectOwnerMixin
from core.utils import resolve_env_vars


def _get_env_var_urls(target_type, project_name, env_name=None, service_name=None):
    """Build env var URL set for the given target type and identifiers."""
    if target_type == "project":
        kwargs = {"project_name": project_name}
        prefix = "projects:project"
    elif target_type == "environment":
        kwargs = {"project_name": project_name, "env_name": env_name}
        prefix = "projects:env"
    elif target_type == "service":
        kwargs = {"project_name": project_name, "service_name": service_name}
        prefix = "projects:service"
    else:
        raise ValueError(f"Unknown target_type: {target_type}")

    return {
        "env_var_row_url": reverse(f"{prefix}_env_var_row", kwargs=kwargs),
        "env_var_edit_url": reverse(f"{prefix}_env_var_edit_row", kwargs=kwargs),
        "env_var_add_url": reverse(f"{prefix}_env_var_add_row", kwargs=kwargs),
        "env_var_save_url": reverse(f"{prefix}_env_var_save_new", kwargs=kwargs),
        "env_var_delete_url": reverse(f"{prefix}_env_var_delete_new", kwargs=kwargs),
        "env_var_toggle_lock_url": reverse(f"{prefix}_env_var_toggle_lock", kwargs=kwargs),
    }


def _resolve_and_find_var(project, service, environment, key, current_level):
    """Resolve env vars and find a specific variable by key."""
    resolved = resolve_env_vars(project, service, environment)
    for var in resolved:
        if var["key"] == key:
            return var
    return None


def _get_entity_and_context(project, service_name=None, env_name=None):
    """Get the target entity and cascade context objects."""
    service = None
    environment = None

    if service_name:
        service = get_object_or_404(Service, project=project, name=service_name)
    if env_name:
        environment = get_object_or_404(Environment, project=project, name=env_name)

    return service, environment


def _current_level_for(service_name, env_name):
    """Determine current level string from URL kwargs."""
    if env_name:
        return "environment"
    if service_name:
        return "service"
    return "project"


def _get_entity(project, current_level, service=None, environment=None):
    """Return the entity whose env_vars JSONField to modify."""
    if current_level == "environment":
        return environment
    if current_level == "service":
        return service
    return project


# ============================================================================
# Display Row View (GET) - Returns display partial for a single var
# ============================================================================


class EnvVarDisplayRowView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Return _env_var_row.html for a given variable key (used by cancel button)."""

    def get(self, request, *args, **kwargs):
        key = request.GET.get("key", "")
        if not key:
            return HttpResponseBadRequest("Missing key parameter")

        service_name = kwargs.get("service_name")
        env_name = kwargs.get("env_name")
        service, environment = _get_entity_and_context(self.project, service_name, env_name)
        current_level = _current_level_for(service_name, env_name)

        var = _resolve_and_find_var(self.project, service, environment, key, current_level)
        if not var:
            return HttpResponse(status=404)

        urls = _get_env_var_urls(current_level, self.project.name, env_name=env_name, service_name=service_name)
        is_editable = current_level != "system"

        context = {
            "var": var,
            "is_editable": is_editable,
            "current_level": current_level,
            "show_empty_warning": current_level in ("service", "environment"),
            **urls,
        }
        from django.template.loader import render_to_string

        html = render_to_string("core/env_vars/_env_var_row.html", context, request=request)
        return HttpResponse(html)


# ============================================================================
# Edit Row View (GET) - Returns edit partial for a single var
# ============================================================================


class EnvVarEditRowView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Return _env_var_row_edit.html for a given variable key."""

    def get(self, request, *args, **kwargs):
        key = request.GET.get("key", "")
        if not key:
            return HttpResponseBadRequest("Missing key parameter")

        service_name = kwargs.get("service_name")
        env_name = kwargs.get("env_name")
        service, environment = _get_entity_and_context(self.project, service_name, env_name)
        current_level = _current_level_for(service_name, env_name)

        var = _resolve_and_find_var(self.project, service, environment, key, current_level)
        if not var:
            return HttpResponse(status=404)

        urls = _get_env_var_urls(current_level, self.project.name, env_name=env_name, service_name=service_name)

        context = {
            "var": var,
            "editing_key": key,
            "current_level": current_level,
            **urls,
        }
        from django.template.loader import render_to_string

        html = render_to_string("core/env_vars/_env_var_row_edit.html", context, request=request)
        return HttpResponse(html)


# ============================================================================
# Add Row View (GET) - Returns empty row for adding a new var
# ============================================================================


class EnvVarAddRowView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Return _env_var_add_row.html (empty row for adding)."""

    def get(self, request, *args, **kwargs):
        service_name = kwargs.get("service_name")
        env_name = kwargs.get("env_name")
        current_level = _current_level_for(service_name, env_name)

        urls = _get_env_var_urls(current_level, self.project.name, env_name=env_name, service_name=service_name)

        context = {
            "empty_var": {"key": "", "value": "", "lock": False, "description": ""},
            "current_level": current_level,
            **urls,
        }
        from django.template.loader import render_to_string

        html = render_to_string("core/env_vars/_env_var_add_row.html", context, request=request)
        return HttpResponse(html)


# ============================================================================
# Save View (POST) - Create or update a variable
# ============================================================================


class EnvVarSaveView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Save a variable (create or update). Returns display row partial."""

    def post(self, request, *args, **kwargs):
        key = request.POST.get("key", "").strip().upper()
        value = request.POST.get("value", "")
        lock = request.POST.get("lock") == "on"
        description = request.POST.get("description", "").strip()
        editing_key = request.POST.get("editing_key", "").strip()

        # Validate key format
        if not key or not re.match(r"^[A-Z][A-Z0-9_]*$", key):
            return HttpResponseBadRequest(
                "Key must start with a letter and contain only uppercase letters, numbers, and underscores."
            )

        # Reject PTF_* system vars
        if key.startswith("PTF_"):
            return HttpResponseBadRequest("Cannot create or modify system variables (PTF_* prefix).")

        service_name = kwargs.get("service_name")
        env_name = kwargs.get("env_name")
        service, environment = _get_entity_and_context(self.project, service_name, env_name)
        current_level = _current_level_for(service_name, env_name)

        # Check locked upstream vars cannot be overridden
        resolved = resolve_env_vars(self.project, service, environment)
        for var in resolved:
            if var["key"] == key and var["lock"] and var["source"] != current_level:
                return HttpResponseBadRequest(
                    f"Variable '{key}' is locked at {var['locked_by']} level and cannot be overridden."
                )

        # Empty value cannot be locked
        if not value:
            lock = False

        # Environment level never locks
        if current_level == "environment":
            lock = False

        # Get the entity to modify
        entity = _get_entity(self.project, current_level, service, environment)
        env_vars = list(entity.env_vars or [])

        # Update or add
        target_key = editing_key if editing_key else key
        updated = False
        for var in env_vars:
            if var["key"] == target_key:
                var["key"] = key
                var["value"] = value
                var["lock"] = lock
                if description:
                    var["description"] = description
                elif "description" not in var:
                    var["description"] = ""
                updated = True
                break

        if not updated:
            env_vars.append({"key": key, "value": value, "lock": lock, "description": description})

        entity.env_vars = env_vars
        entity.save(update_fields=["env_vars", "updated_at"])

        # Return the display row for the saved var
        saved_var = _resolve_and_find_var(self.project, service, environment, key, current_level)
        urls = _get_env_var_urls(current_level, self.project.name, env_name=env_name, service_name=service_name)
        is_editable = True

        context = {
            "var": saved_var,
            "is_editable": is_editable,
            "current_level": current_level,
            "show_empty_warning": current_level in ("service", "environment"),
            **urls,
        }
        from django.template.loader import render_to_string

        html = render_to_string("core/env_vars/_env_var_row.html", context, request=request)
        return HttpResponse(html)


# ============================================================================
# Delete View (DELETE or POST) - Remove a variable
# ============================================================================


class EnvVarDeleteView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Delete a variable. Returns empty response (HTMX removes the row)."""

    def delete(self, request, *args, **kwargs):
        return self._handle_delete(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Support POST with _method=DELETE for browsers that don't support DELETE
        return self._handle_delete(request, *args, **kwargs)

    def _handle_delete(self, request, *args, **kwargs):
        key = request.GET.get("key", "") or request.POST.get("key", "")
        if not key:
            return HttpResponseBadRequest("Missing key parameter")

        # Reject PTF_* system vars
        if key.startswith("PTF_"):
            return HttpResponseBadRequest("Cannot delete system variables.")

        service_name = kwargs.get("service_name")
        env_name = kwargs.get("env_name")
        service, environment = _get_entity_and_context(self.project, service_name, env_name)
        current_level = _current_level_for(service_name, env_name)

        # Cannot delete upstream vars
        resolved = resolve_env_vars(self.project, service, environment)
        for var in resolved:
            if var["key"] == key and var["source"] != current_level:
                return HttpResponseBadRequest(f"Cannot delete variable '{key}' defined at {var['source']} level.")

        entity = _get_entity(self.project, current_level, service, environment)
        env_vars = [v for v in (entity.env_vars or []) if v["key"] != key]
        entity.env_vars = env_vars
        entity.save(update_fields=["env_vars", "updated_at"])

        return HttpResponse("")  # HTMX removes the row


# ============================================================================
# Toggle Lock View (POST) - Toggle lock state on a variable
# ============================================================================


class EnvVarToggleLockView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Toggle lock state on a variable. Returns display row partial."""

    def post(self, request, *args, **kwargs):
        key = request.GET.get("key", "") or request.POST.get("key", "")
        if not key:
            return HttpResponseBadRequest("Missing key parameter")

        service_name = kwargs.get("service_name")
        env_name = kwargs.get("env_name")
        current_level = _current_level_for(service_name, env_name)

        # Only project and service levels support locking
        if current_level == "environment":
            return HttpResponseBadRequest("Environment level does not support locking.")

        # Cannot toggle system var locks
        if key.startswith("PTF_"):
            return HttpResponseBadRequest("Cannot modify system variable locks.")

        service, environment = _get_entity_and_context(self.project, service_name, env_name)
        entity = _get_entity(self.project, current_level, service, environment)
        env_vars = list(entity.env_vars or [])

        for var in env_vars:
            if var["key"] == key:
                # Cannot lock empty values
                if not var.get("value", ""):
                    return HttpResponseBadRequest("Cannot lock a variable with an empty value.")
                var["lock"] = not var.get("lock", False)
                break
        else:
            return HttpResponse(status=404)

        entity.env_vars = env_vars
        entity.save(update_fields=["env_vars", "updated_at"])

        # Return updated display row
        resolved_var = _resolve_and_find_var(self.project, service, environment, key, current_level)
        urls = _get_env_var_urls(current_level, self.project.name, env_name=env_name, service_name=service_name)

        context = {
            "var": resolved_var,
            "is_editable": True,
            "current_level": current_level,
            "show_empty_warning": current_level in ("service", "environment"),
            **urls,
        }
        from django.template.loader import render_to_string

        html = render_to_string("core/env_vars/_env_var_row.html", context, request=request)
        return HttpResponse(html)
