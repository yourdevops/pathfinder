"""API views for external integrations."""

import json
import logging

import yaml
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import ApiToken, CIStep
from plugins.base import get_ci_plugin_for_engine

logger = logging.getLogger(__name__)


@csrf_exempt
def step_validate_api(request):
    """POST /api/ci-workflows/steps/validate

    Validates a CI step definition file and returns parsed metadata,
    computed slug, conflict detection, and warnings.

    Authentication: Authorization: Token <api-token>

    Request body (JSON):
        ci_engine: str -- engine identifier (e.g., "github_actions")
        content: str -- raw YAML content of the step definition file

    Response (JSON):
        valid: bool
        step: {name, slug, phase, runtimes, produces, inputs}
        conflicts: [str]
        warnings: [str]
        errors: [str]
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # Token authentication
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Token "):
        return JsonResponse(
            {"error": "Authentication required. Use: Authorization: Token <your-token>"},
            status=401,
        )

    token_key = auth_header[6:].strip()
    try:
        token = ApiToken.objects.get(key=token_key, is_active=True)
        token.last_used_at = timezone.now()
        token.save(update_fields=["last_used_at"])
    except ApiToken.DoesNotExist:
        return JsonResponse({"error": "Invalid or revoked token"}, status=401)

    # Parse request body
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    engine = body.get("ci_engine", "")
    content_str = body.get("content", "")

    if not engine:
        return JsonResponse({"error": "ci_engine field is required"}, status=400)
    if not content_str:
        return JsonResponse({"error": "content field is required"}, status=400)

    # Parse YAML
    try:
        file_content = yaml.safe_load(content_str)
    except yaml.YAMLError as e:
        return JsonResponse({"valid": False, "step": None, "conflicts": [], "warnings": [], "errors": [str(e)]})

    if not isinstance(file_content, dict):
        return JsonResponse(
            {
                "valid": False,
                "step": None,
                "conflicts": [],
                "warnings": [],
                "errors": ["Content must be a YAML mapping"],
            }
        )

    # Get CI plugin for the engine
    ci_plugin = get_ci_plugin_for_engine(engine)
    if not ci_plugin:
        return JsonResponse(
            {
                "valid": False,
                "step": None,
                "conflicts": [],
                "warnings": [],
                "errors": [f"Unknown CI engine: {engine}"],
            }
        )

    # Parse step file using plugin logic
    step_info = ci_plugin.parse_step_file(file_content)
    slug = ci_plugin.derive_step_slug(file_content, "")

    # Check for slug conflicts
    conflicts = []
    if slug:
        existing = CIStep.objects.filter(engine=engine, slug=slug, status="active").first()
        if existing:
            conflicts.append(f"Slug '{slug}' already exists in repository '{existing.repository.name}'")

    # Build warnings
    warnings = []
    if not step_info.get("phase"):
        warnings.append("No x-pathfinder.phase specified -- step will appear in 'Other' category")
    if not slug:
        warnings.append("Could not derive slug from step definition -- check x-pathfinder.name or action name field")
    if not step_info.get("name"):
        warnings.append("No name field found in step definition")

    valid = bool(slug) and len(conflicts) == 0

    return JsonResponse(
        {
            "valid": valid,
            "step": {
                "name": step_info.get("name", ""),
                "slug": slug,
                "phase": step_info.get("phase", ""),
                "runtimes": step_info.get("runtime_constraints", {}),
                "produces": step_info.get("produces"),
                "inputs": list((step_info.get("inputs") or {}).keys()),
            },
            "conflicts": conflicts,
            "warnings": warnings,
            "errors": [],
        }
    )
