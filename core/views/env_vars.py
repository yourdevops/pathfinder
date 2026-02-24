"""Unified env var views: bulk save endpoint and utility functions."""

import json
import re

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views import View

from core.models import Environment, Service
from core.permissions import ProjectContributorMixin
from core.utils import resolve_env_vars


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


class EnvVarBulkSaveView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Bulk save all env vars for the current level. Replaces the entity's env_vars entirely."""

    def post(self, request, *args, **kwargs):
        service_name = kwargs.get("service_name")
        env_name = kwargs.get("env_name")
        service, environment = _get_entity_and_context(self.project, service_name, env_name)
        current_level = _current_level_for(service_name, env_name)
        entity = _get_entity(self.project, current_level, service, environment)

        # Project-level env var editing is owner-only
        if current_level == "project" and self.user_project_role != "owner":
            return HttpResponse("Only project owners can edit project-level variables.", status=403)

        try:
            new_vars = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

        if not isinstance(new_vars, list):
            return HttpResponseBadRequest("Expected JSON array")

        # Validate each var
        validated = []
        seen_keys = set()
        for var in new_vars:
            key = (var.get("key") or "").strip().upper()
            if not key or not re.match(r"^[A-Z][A-Z0-9_]*$", key):
                return HttpResponseBadRequest(f"Invalid key format: {key}")
            if key.startswith("PTF_"):
                return HttpResponseBadRequest("Cannot save system variables (PTF_* prefix)")
            if key in seen_keys:
                return HttpResponseBadRequest(f"Duplicate key: {key}")
            seen_keys.add(key)

            value = var.get("value", "")
            lock = bool(var.get("lock", False))
            description = (var.get("description") or "").strip()

            # Empty value cannot be locked
            if not value:
                lock = False
            # Environment level never locks
            if current_level == "environment":
                lock = False

            validated.append({"key": key, "value": value, "lock": lock, "description": description})

        # Check upstream lock conflicts
        resolved = resolve_env_vars(self.project, service, environment)
        upstream_locked_keys = {v["key"] for v in resolved if v["lock"] and v["source"] != current_level}
        for var in validated:
            if var["key"] in upstream_locked_keys:
                return HttpResponseBadRequest(
                    f"Variable '{var['key']}' is locked at an upstream level and cannot be overridden."
                )

        entity.env_vars = validated
        entity.save(update_fields=["env_vars", "updated_at"])

        return HttpResponse(status=200)
