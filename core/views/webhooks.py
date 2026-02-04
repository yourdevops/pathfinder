"""
Webhook endpoints for receiving external events.

Handles GitHub webhooks for build status updates.
"""

import hashlib
import hmac
import json
import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


def verify_github_signature(request: HttpRequest, secret: str) -> bool:
    """
    Verify GitHub webhook signature.

    Uses HMAC-SHA256 to verify the signature header matches
    the computed signature of the request body.

    Args:
        request: The HTTP request object
        secret: The webhook secret from connection config

    Returns:
        True if signature is valid, False otherwise
    """
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header:
        return False

    expected = (
        "sha256="
        + hmac.new(
            secret.encode(),
            request.body,
            hashlib.sha256,
        ).hexdigest()
    )

    # Use compare_digest for timing-safe comparison
    return hmac.compare_digest(expected, signature_header)


def identify_service_from_webhook(payload: dict):
    """
    Identify the Service associated with a webhook payload.

    Matches by repository URL, which is unique per service.
    CI workflows can be shared across multiple services, so workflow name
    is not a reliable identifier.

    Args:
        payload: The parsed webhook JSON payload

    Returns:
        Service instance or None if no match found
    """
    from core.models import Service

    repo_url = payload.get("repository", {}).get("html_url", "")
    if repo_url:
        service = Service.objects.filter(repo_url=repo_url).first()
        if service:
            return service

    logger.warning(f"No service found for webhook: repo={repo_url}")
    return None


def extract_artifact_ref(payload: dict) -> str:
    """
    Extract artifact reference from webhook payload.

    Primarily looks for the artifacts_url from the workflow_run.
    Used for Phase 7 deployment integration.

    Args:
        payload: The parsed webhook JSON payload

    Returns:
        Artifact reference string, or empty string if not available
    """
    workflow_run = payload.get("workflow_run", {})

    # Primary: artifacts_url from workflow run
    artifacts_url = workflow_run.get("artifacts_url", "")
    if artifacts_url:
        return artifacts_url

    # Fallback: construct from repository and run_id
    repo = payload.get("repository", {})
    run_id = workflow_run.get("id")
    if repo.get("full_name") and run_id:
        return f"https://api.github.com/repos/{repo['full_name']}/actions/runs/{run_id}/artifacts"

    return ""


@csrf_exempt
def build_webhook(request: HttpRequest) -> HttpResponse:
    """
    Handle GitHub Actions workflow_run webhook.

    Receives webhook events when GitHub Actions workflows start or complete.
    Validates HMAC signature and enqueues background task to poll GitHub API
    for full build details.

    Security: Always returns 200 OK to prevent information leakage.

    Args:
        request: The HTTP request object

    Returns:
        HttpResponse with 200 status (always)
    """
    from core.models import ProjectConnection
    from core.tasks import poll_build_details

    # Only accept POST
    if request.method != "POST":
        return HttpResponse(status=200)

    # Parse JSON body
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in webhook payload")
        return HttpResponse(status=200)

    # Only process 'requested' (start) and 'completed' actions
    action = payload.get("action", "")
    if action not in ("requested", "completed"):
        return HttpResponse(status=200)

    # Identify service
    service = identify_service_from_webhook(payload)
    if not service:
        return HttpResponse(status=200)

    # Get project's default SCM connection
    project_connection = (
        ProjectConnection.objects.filter(project=service.project, is_default=True).select_related("connection").first()
    )

    if not project_connection:
        logger.warning(f"No default SCM connection for project {service.project.name}")
        return HttpResponse(status=200)

    connection = project_connection.connection
    config = connection.get_config()

    # Verify signature
    webhook_secret = config.get("webhook_secret", "")
    if webhook_secret:
        if not verify_github_signature(request, webhook_secret):
            logger.warning(f"Invalid webhook signature for service {service.name}")
            return HttpResponse(status=200)
    else:
        logger.warning(f"No webhook secret configured for connection {connection.name}")

    # Extract run details
    workflow_run = payload.get("workflow_run", {})
    run_id = workflow_run.get("id")
    if not run_id:
        logger.warning("No run_id in webhook payload")
        return HttpResponse(status=200)

    repo_full_name = payload.get("repository", {}).get("full_name", "")
    if not repo_full_name:
        logger.warning("No repository full_name in webhook payload")
        return HttpResponse(status=200)

    # Extract artifact reference
    artifact_ref = extract_artifact_ref(payload)

    # Enqueue background task
    poll_build_details.enqueue(
        run_id=run_id,
        repo_name=repo_full_name,
        connection_id=connection.id,
        service_id=service.id,
        artifact_ref=artifact_ref,
    )

    logger.info(f"Enqueued build polling for service {service.name}, run_id={run_id}")
    return HttpResponse(status=200)
