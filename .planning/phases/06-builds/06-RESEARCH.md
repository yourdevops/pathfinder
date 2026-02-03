# Phase 6: Builds - Research

**Researched:** 2026-02-03
**Domain:** Webhook ingestion, CI build tracking, GitHub Actions integration
**Confidence:** HIGH

## Summary

This research covers implementing GitHub Actions build tracking via webhooks for the Pathfinder developer self-service portal. The phase involves receiving webhook notifications from GitHub when builds start/complete, polling the GitHub API for full build details, storing build records, and transitioning services from draft to active on first successful build.

The standard approach leverages Django's existing infrastructure (django-tasks for background processing, CSRF exempt views for webhooks) combined with PyGithub's WorkflowRun API for fetching build details. The webhook acts as a lightweight trigger; GitHub's REST API is the source of truth for build data.

Key findings: HMAC-SHA256 signature verification is the standard for GitHub webhooks; PyGithub provides comprehensive WorkflowRun properties (id, head_sha, status, conclusion, html_url); Django 6.x's native tasks framework handles async polling cleanly; the existing plugin architecture (CICapableMixin) provides the extension point for CI-specific functionality.

**Primary recommendation:** Implement a single `/webhooks/build/` endpoint with HMAC verification, trigger background task to poll GitHub API for details, store Build model records, and transition Service status on first success.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 6.0.1 | Web framework with native tasks | Already in project, provides CSRF exempt, tasks framework |
| PyGithub | 2.5.0+ | GitHub API client | Already in project, provides WorkflowRun class with all needed properties |
| django-tasks | 0.4.0+ | Background task processing | Already configured with database backend, queues defined |
| hmac (stdlib) | N/A | Webhook signature verification | Python standard library, recommended by GitHub |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib (stdlib) | N/A | SHA256 hashing | For HMAC digest computation |
| secrets (stdlib) | N/A | Timing-safe comparison | For `compare_digest()` in signature verification |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polling after webhook | Direct webhook data | Webhook payload may not contain all needed fields; API is source of truth |
| HMAC-SHA256 | JWT tokens | HMAC is GitHub's standard; simpler, no key rotation |
| Database backend | Redis/Celery | Database is sufficient for this use case, already configured |

**Installation:**
No new dependencies required. All libraries already in pyproject.toml.

## Architecture Patterns

### Recommended Project Structure
```
core/
|-- models.py           # Add Build model
|-- views/
|   |-- webhooks.py     # New webhook views (CSRF exempt)
|-- tasks.py            # Add poll_build_details task
|-- urls.py             # Add webhook_patterns

plugins/github/
|-- plugin.py           # Add get_workflow_run method
```

### Pattern 1: Webhook as Notification Trigger
**What:** Webhook receives minimal notification, enqueues background task to fetch full details from API
**When to use:** When webhook payload is insufficient or untrusted; API is authoritative source
**Example:**
```python
# Source: Project context decision from 06-CONTEXT.md
@csrf_exempt
def build_webhook(request):
    """
    Single endpoint receiving build status notifications.
    Always returns 200 OK to prevent enumeration attacks.
    Enqueues background task for actual processing.
    """
    if request.method != 'POST':
        return HttpResponse(status=200)

    # Verify HMAC signature
    if not verify_github_signature(request):
        logger.warning("Invalid webhook signature")
        return HttpResponse(status=200)  # Still 200 to prevent enumeration

    payload = json.loads(request.body)
    run_id = payload.get('workflow_run', {}).get('id')

    if run_id:
        poll_build_details.enqueue(run_id=run_id)

    return HttpResponse(status=200)
```

### Pattern 2: HMAC Signature Verification
**What:** Verify webhook authenticity using shared secret and HMAC-SHA256
**When to use:** Always for external webhooks
**Example:**
```python
# Source: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
import hmac
import hashlib

def verify_github_signature(request, secret: bytes) -> bool:
    """Verify GitHub webhook signature using HMAC-SHA256."""
    signature_header = request.headers.get('X-Hub-Signature-256', '')
    if not signature_header:
        return False

    expected = 'sha256=' + hmac.new(
        secret,
        msg=request.body,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)
```

### Pattern 3: Build State Machine
**What:** Track build lifecycle with clear state transitions
**When to use:** For status tracking with defined transitions
**Example:**
```python
# Source: Project context - Claude's discretion area
class Build(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),      # Webhook received, polling not complete
        ('running', 'Running'),       # Build in progress
        ('success', 'Success'),       # Build completed successfully
        ('failed', 'Failed'),         # Build failed
        ('cancelled', 'Cancelled'),   # Build was cancelled
    ]

    # Allowed transitions
    VALID_TRANSITIONS = {
        'pending': ['running', 'success', 'failed', 'cancelled'],
        'running': ['success', 'failed', 'cancelled'],
        # Terminal states - no transitions out
    }
```

### Pattern 4: Service Status Activation
**What:** Transition service from draft to active on first successful build
**When to use:** When build success should activate service
**Example:**
```python
# Source: Project requirement BILD-05
def activate_service_on_first_success(build):
    """Transition service from draft to active on first successful build."""
    service = build.service
    if service.status == 'draft' and build.status == 'success':
        # Check this is first successful build
        has_prior_success = Build.objects.filter(
            service=service,
            status='success'
        ).exclude(id=build.id).exists()

        if not has_prior_success:
            service.status = 'active'
            service.save(update_fields=['status', 'updated_at'])
            logger.info(f"Service {service.name} activated on first successful build")
```

### Anti-Patterns to Avoid
- **Processing in webhook handler:** Don't do heavy work synchronously; webhook handler must return quickly
- **Trusting webhook payload:** Always fetch authoritative data from API; payload may be spoofed
- **Returning errors on invalid webhooks:** Always return 200 OK; errors reveal information to attackers
- **Plain string comparison for signatures:** Always use `hmac.compare_digest()` to prevent timing attacks

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Signature verification | Custom HMAC code | `hmac.new()` + `compare_digest()` | Timing-safe, battle-tested |
| GitHub API calls | Raw requests | PyGithub WorkflowRun | Handles auth, pagination, rate limits |
| Background tasks | Threading/multiprocessing | django-tasks | Already configured, database-backed, reliable |
| Pagination | Custom offset/limit | Django Paginator | Built-in, handles edge cases |

**Key insight:** The existing django-tasks infrastructure and PyGithub library eliminate the need for custom async code or API wrappers.

## Common Pitfalls

### Pitfall 1: Timing Attack on Signature Verification
**What goes wrong:** Using `==` to compare signatures allows timing-based attacks
**Why it happens:** Regular string comparison exits early on first mismatch
**How to avoid:** Always use `hmac.compare_digest()` for constant-time comparison
**Warning signs:** Using `if signature == expected:` instead of `compare_digest()`

### Pitfall 2: Processing Long-Running Tasks in Webhook Handler
**What goes wrong:** Webhook times out, GitHub retries, duplicate processing
**Why it happens:** Trying to do everything synchronously
**How to avoid:** Webhook handler only validates and enqueues; processing happens in background task
**Warning signs:** Webhook response time > 1 second; duplicate build records

### Pitfall 3: Revealing Webhook Endpoint via Error Responses
**What goes wrong:** Different error codes for invalid signature vs missing service expose endpoint
**Why it happens:** Natural instinct to return meaningful errors
**How to avoid:** Always return 200 OK regardless of outcome; log errors internally
**Warning signs:** Different HTTP status codes for different error conditions

### Pitfall 4: Race Condition on Service Activation
**What goes wrong:** Multiple successful builds arrive simultaneously, causing duplicate activation attempts
**Why it happens:** Checking and updating status not atomic
**How to avoid:** Use `select_for_update()` or check with `F()` expressions; idempotent activation logic
**Warning signs:** Database integrity errors or duplicate log messages

### Pitfall 5: Missing run_id Lookup
**What goes wrong:** Can't find service for webhook because no mapping exists
**Why it happens:** GitHub's run_id is transient; need service identifier in webhook
**How to avoid:** Use workflow name pattern (`{project-name}-{service-name}.yml`) to identify service
**Warning signs:** "Service not found" errors in webhook processing

## Code Examples

Verified patterns from official sources and project context:

### CSRF Exempt Webhook View
```python
# Source: Django docs - https://docs.djangoproject.com/en/6.0/ref/csrf/
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

@csrf_exempt
def build_webhook(request):
    """Receive build notifications from GitHub Actions."""
    if request.method != 'POST':
        return HttpResponse(status=200)

    # Process webhook...
    return HttpResponse(status=200)
```

### PyGithub WorkflowRun Properties
```python
# Source: https://github.com/PyGithub/PyGithub/blob/main/github/WorkflowRun.py
from github import Github

def fetch_workflow_run(connection, repo_name: str, run_id: int) -> dict:
    """Fetch workflow run details from GitHub API."""
    g = plugin._get_github_client(connection.get_config())
    repo = g.get_repo(repo_name)
    run = repo.get_workflow_run(run_id)

    return {
        'id': run.id,
        'run_number': run.run_number,
        'head_sha': run.head_sha,
        'head_branch': run.head_branch,
        'status': run.status,           # queued, in_progress, completed
        'conclusion': run.conclusion,   # success, failure, cancelled, etc.
        'created_at': run.created_at,
        'updated_at': run.updated_at,
        'html_url': run.html_url,
        'name': run.name,
        'event': run.event,
        'actor': run.actor.login if run.actor else None,
    }
```

### Background Task Pattern
```python
# Source: Existing core/tasks.py patterns in codebase
from django_tasks import task
import logging

logger = logging.getLogger(__name__)

@task(queue_name="build_updates")
def poll_build_details(run_id: int, repo_name: str, connection_id: int) -> dict:
    """
    Poll GitHub API for workflow run details and update Build record.

    Args:
        run_id: GitHub workflow run ID
        repo_name: Full repository name (owner/repo)
        connection_id: IntegrationConnection ID for GitHub
    """
    from core.models import Build, IntegrationConnection, Service

    try:
        connection = IntegrationConnection.objects.get(id=connection_id)
    except IntegrationConnection.DoesNotExist:
        logger.error(f"Connection {connection_id} not found")
        return {"error": "Connection not found"}

    # Fetch from GitHub API
    run_data = fetch_workflow_run(connection, repo_name, run_id)

    # Update or create Build record
    build, created = Build.objects.update_or_create(
        github_run_id=run_id,
        defaults={
            'status': map_github_status(run_data['status'], run_data['conclusion']),
            'commit_sha': run_data['head_sha'],
            'branch': run_data['head_branch'],
            'ci_job_url': run_data['html_url'],
            # ... other fields
        }
    )

    # Activate service if first success
    if build.status == 'success':
        activate_service_on_first_success(build)

    return {"build_id": build.id, "status": build.status}
```

### Django Paginator for Build History
```python
# Source: Existing core/views/audit.py pattern
from django.core.paginator import Paginator

class BuildHistoryView(LoginRequiredMixin, TemplateView):
    template_name = "core/services/_builds_tab.html"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get builds for service
        builds = Build.objects.filter(
            service=self.service
        ).order_by('-created_at')

        # Apply status filter
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter != 'all':
            builds = builds.filter(status=status_filter)

        # Paginate
        paginator = Paginator(builds, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        context['page_obj'] = paginator.get_page(page_number)
        context['builds'] = context['page_obj']

        return context
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| X-Hub-Signature (SHA1) | X-Hub-Signature-256 (SHA256) | 2020 | Must use SHA256 header |
| Celery for tasks | Django 6.0 native tasks | Django 6.0 (2024) | No separate broker needed |
| Custom webhook parsing | GitHub sends structured JSON | Stable | Standard payload format |

**Deprecated/outdated:**
- `X-Hub-Signature` header: Use `X-Hub-Signature-256` instead (SHA256 vs SHA1)
- Threading for background work: Use django-tasks database backend

## Open Questions

Things that need resolution during implementation:

1. **Webhook secret storage**
   - What we know: HMAC needs shared secret; GitHub plugin has `webhook_secret` config field
   - What's unclear: Per-service secrets or single per-connection?
   - Recommendation: Use per-connection webhook_secret from IntegrationConnection config

2. **Service identification from webhook**
   - What we know: Webhook contains workflow name and repository
   - What's unclear: Exact mapping from workflow name to Service
   - Recommendation: Parse workflow name pattern `{project}-{service}.yml` or match by repo URL

3. **Artifact reference format**
   - What we know: Need to store artifact reference for deployments
   - What's unclear: Where artifact ref comes from (outputs? naming convention?)
   - Recommendation: Check if CIStep "produces" metadata defines artifact pattern; may need GitHub packages URL

4. **Real-time updates (WebSocket consideration)**
   - What we know: Context mentions considering WebSocket for in-progress builds
   - What's unclear: Implementation complexity vs benefit
   - Recommendation: Start with polling (HTMX `hx-trigger="every 3s"`); WebSocket is future enhancement

## Sources

### Primary (HIGH confidence)
- [GitHub Webhook Signature Verification](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) - HMAC verification pattern
- [GitHub Workflow Run API](https://docs.github.com/en/rest/actions/workflow-runs) - API response fields
- [PyGithub WorkflowRun](https://github.com/PyGithub/PyGithub/blob/main/github/WorkflowRun.py) - Available properties and methods
- [Django Tasks Framework](https://docs.djangoproject.com/en/6.0/topics/tasks/) - Native background task API

### Secondary (MEDIUM confidence)
- Existing `core/tasks.py` - Pattern for django-tasks usage in this codebase
- Existing `plugins/github/plugin.py` - PyGithub client patterns in this codebase
- Existing `core/views/services.py` - View patterns and HTMX usage

### Tertiary (LOW confidence)
- WebSearch results on Django webhook patterns - General best practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, documented
- Architecture: HIGH - Patterns from official docs and existing codebase
- Pitfalls: HIGH - Well-documented security concerns with official guidance

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - stable domain)
