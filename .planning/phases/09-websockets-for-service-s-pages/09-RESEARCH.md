# Phase 9: WebSockets for Service's Pages - Research

**Researched:** 2026-02-24
**Domain:** Django Channels WebSocket + HTMX WS Extension + Dashboard UX
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Architecture: Django Channels + HTMX WS Extension
- Use Django Channels 4.3.2 (compatible with Django 6.x) for server-side WebSocket consumers
- Use HTMX WebSocket extension (`htmx-ext-ws`) for client-side -- sends HTML partials via OOB swaps, no custom JS needed
- Single WebSocket connection per service detail page
- Server pushes rendered Django template partials wrapped in `hx-swap-oob="true"` divs
- Reuse existing template partials for both initial HTTP render and WebSocket pushes
- CSP-compatible: htmx-ext-ws does not use eval(), works with Alpine CSP build

#### Transport: Database Polling (No Redis)
- Consumer polls SQLite every 3 seconds, pushes only when state changes
- No channel layer needed -- avoids Redis dependency
- Acceptable latency: 0-3 seconds for dashboard updates
- If instant push becomes necessary later, Redis channel layer can be added without changing consumer interface

#### Connection Lifecycle
- Place `ws-connect` on `detail.html` content wrapper (outside `#tab-content`)
- Connection stays open across HTMX tab switches within the same service (tab content is swapped inside the WS wrapper)
- Connection closes when navigating away from the service (DOM element removed)
- Built-in HTMX exponential backoff reconnection on unexpected closure
- Authentication via `AuthMiddlewareStack` -- reads session cookie from WS handshake

#### Real-Time Update Scope (expanded from original)
- **Service dashboard**: build stats, scaffold progress (pending/done only -- no step-by-step), CI pipeline health
- **Builds list**: full list refresh when any build changes status (queued -> running -> success/failed) -- ensures sort order and new builds appear correctly
- **Build detail**: status update only when build completes -- logs fetched on demand, not streamed
- **CI workflow tab**: manifest sync status
- Service info section (repo, metadata) does NOT need real-time updates -- static after creation
- Each updatable section gets a stable `id` attribute for OOB targeting
- Multiple sections updated from a single WS message via OOB swaps by element ID

#### New Build Notification
- New builds get a subtle visual indicator -- brief highlight on new/changed rows so user notices new activity
- No toast or intrusive notification

#### Connection Status Indicator
- Small dot next to the service name in the left sidebar showing connected/disconnected state
- Green when WebSocket is connected, changes when disconnected

#### Fallback & Error Handling
- If WebSocket can't connect at all (Channels not running), show a subtle "Live updates unavailable" warning banner
- Page works fine without WS -- just no live updates, manual refresh still works
- Claude's Discretion: whether to auto-fallback to polling or rely on reconnect only

#### ASGI Setup
- Project already runs uvicorn with ASGI (`Dockerfile` line 62: `uvicorn pathfinder.asgi:application`)
- Only change needed: update `asgi.py` to use `ProtocolTypeRouter` routing HTTP and WebSocket
- No migration from Gunicorn needed -- already on ASGI
- Traefik supports WebSocket upgrade automatically, no proxy config changes

#### Dashboard Empty State (conditional)
- If no CI Workflow assigned: show card with link to assign a CI Workflow
- If CI Workflow assigned but no builds: show card with "Fetch Builds" button (manual poll -- webhook could fail)
- If builds exist: show stats row + recent builds normally
- Hide stats cards and recent builds section entirely when total_builds=0 -- no dashes for empty state

#### Dashboard Polish (from frontend design review)
- Make commit SHAs clickable links in recent builds (link to commit URL)
- Add left accent border to CI Pipeline card based on health (green = healthy, amber = needs attention)
- CI Pipeline empty state gets dashed-border card with icon instead of plain centered text
- No additional CI Pipeline info beyond what exists -- build stats row already covers it

### Claude's Discretion
- Exact polling comparison logic (hash-based vs field-based state diffing)
- Consumer class structure (single consumer vs separate per-section)
- Whether to extract dashboard sections into separate partial templates for reuse
- Onboarding card layout details
- Exact accent border color logic for CI Pipeline card
- Which stat cards should be clickable (link to relevant tabs)
- Number of recent builds to show on dashboard
- Whether to auto-fallback to HTMX polling on WS disconnect or rely on reconnect with backoff

### Deferred Ideas (OUT OF SCOPE)
- WebSocket support for pages outside service context (CI workflows list, steps catalog, project dashboard) -- future phase
- Redis channel layer for instant push from background workers -- can be added without interface changes
- Bidirectional features (cancel build, trigger re-deploy from dashboard via WS) -- future phase
- Service detail header deduplication with sidebar -- minor UI cleanup, separate task
- Real-time log streaming for build detail -- status updates only for now, streaming deferred
</user_constraints>

## Summary

This phase adds real-time push updates to all service-context pages via Django Channels 4.3.2 WebSocket consumers paired with the htmx-ext-ws extension. The architecture avoids Redis entirely by having the server-side consumer poll SQLite every 3 seconds and push rendered HTML partials when state changes. The htmx WebSocket extension handles client-side swap logic via OOB (Out-of-Band) swaps, meaning the server sends `<div id="X" hx-swap-oob="true">...</div>` and HTMX replaces matching elements -- no custom JavaScript needed.

The project already runs on ASGI via uvicorn (Dockerfile line 62), so the primary infrastructure change is updating `asgi.py` to use Channels' `ProtocolTypeRouter` to route both HTTP and WebSocket protocols. A critical finding is that CSP `connect-src 'self'` does NOT reliably match `ws://` WebSocket connections across browsers -- we must explicitly add `ws:` and `wss:` to the CSP `connect-src` directive. Another important finding is that `manage.py runserver` does NOT support WebSocket -- development must use uvicorn (or add `daphne` to INSTALLED_APPS). Since the project already has `daphne` is not present, the development script (`run-dev.sh`) should switch from `manage.py runserver` to `uvicorn pathfinder.asgi:application --reload`.

The phase also includes dashboard UX improvements: conditional empty states based on service progress (no workflow -> assign workflow CTA, workflow but no builds -> fetch builds CTA), clickable commit SHAs, CI Pipeline health accent borders, and connection status indicator in the sidebar.

**Primary recommendation:** Use a single `AsyncWebsocketConsumer` with an `asyncio.create_task` polling loop, hash-based state diffing to detect changes, and `render_to_string()` to generate OOB-wrapped HTML partials for each updatable section.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| channels | 4.3.2 | WebSocket consumer framework for Django | Official Django project, confirmed Django 6.0 compatible (changelog 2025-11-20) |
| htmx-ext-ws | 2.0.3 | Client-side WebSocket connection + OOB swap handling | Official HTMX extension, peer dep htmx.org >=2.0.2, project uses htmx 2.0.4 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| daphne | latest | ASGI development server with WS support (optional) | Only if `manage.py runserver` WebSocket support is desired; NOT needed if dev script uses uvicorn directly |
| pytest-asyncio | latest | Async test support for WebSocket consumer tests | Testing phase -- decorator `@pytest.mark.asyncio` for consumer tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| daphne for dev | uvicorn --reload | uvicorn already in deps, no extra package; loses `manage.py runserver` static file serving (use whitenoise) |
| Database polling | Redis channel layer | Instant push but adds Redis dependency; not needed for 3s latency requirement |
| htmx-ext-ws | Custom JS WebSocket | More control but contradicts project's HTMX-first architecture, requires maintaining custom code |

### Installation

Python dependency:
```bash
uv add channels==4.3.2
```

NPM dependency (for vendor copy to static):
```bash
cd theme/static_src && npm install htmx-ext-ws@2.0.3
```

Update `copy-vendor.js` to include:
```javascript
['node_modules/htmx-ext-ws/dist/ws.min.js', 'htmx-ext-ws.min.js'],
```

## Architecture Patterns

### Recommended Project Structure
```
core/
  consumers.py              # WebSocket consumer(s)
  routing.py                # WebSocket URL routing
pathfinder/
  asgi.py                   # Updated: ProtocolTypeRouter
core/templates/core/services/
  detail.html               # Updated: ws-connect wrapper
  _details_tab.html         # Updated: OOB-targetable section IDs
  _builds_tab.html          # Updated: OOB-targetable section IDs
  _build_row.html           # Unchanged (included by builds tab)
  _ci_tab.html              # Updated: OOB-targetable section IDs
  _dashboard_empty.html     # NEW: conditional empty state partial
  _stats_row.html           # NEW: extractable stats partial for OOB
  _recent_builds.html       # NEW: extractable recent builds partial
  _ci_pipeline_card.html    # NEW: extractable CI pipeline card partial
theme/templates/
  base.html                 # Updated: load htmx-ext-ws, register Alpine WS component
theme/static/js/vendor/
  htmx-ext-ws.min.js        # NEW: vendored WS extension
```

### Pattern 1: AsyncWebsocketConsumer with Polling Loop

**What:** A single async consumer that accepts the connection, spawns a polling task, and pushes OOB HTML when state changes.

**When to use:** Always -- this is the core pattern for this phase.

**Example:**
```python
# Source: Channels 4.3.2 docs + pythontutorials.net pattern
import asyncio
import hashlib
import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string


class ServiceConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.poll_task = None
        self.last_state_hash = None

    async def connect(self):
        # Auth check -- scope["user"] populated by AuthMiddlewareStack
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        self.service_id = self.scope["url_route"]["kwargs"]["service_id"]
        await self.accept()
        self.poll_task = asyncio.create_task(self.poll_loop())

    async def disconnect(self, close_code):
        if self.poll_task:
            self.poll_task.cancel()
            try:
                await self.poll_task
            except asyncio.CancelledError:
                pass

    async def poll_loop(self):
        while True:
            try:
                state = await self.get_current_state()
                state_hash = self.compute_hash(state)
                if state_hash != self.last_state_hash:
                    self.last_state_hash = state_hash
                    html = await self.render_updates(state)
                    if html:
                        await self.send(text_data=html)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass  # Log but don't crash the loop
            await asyncio.sleep(3)

    @sync_to_async
    def get_current_state(self):
        """Fetch all relevant data from DB in a single sync block."""
        from core.models import Build, Service
        service = Service.objects.select_related(
            "ci_workflow", "ci_workflow_version"
        ).get(id=self.service_id)
        builds = list(
            Build.objects.filter(service=service)
            .order_by("-created_at")[:20]
            .values("id", "status", "commit_sha", "created_at")
        )
        return {
            "service_status": service.status,
            "scaffold_status": service.scaffold_status,
            "ci_manifest_status": service.ci_manifest_status,
            "build_data": builds,
        }

    def compute_hash(self, state):
        """Hash state dict to detect changes."""
        return hashlib.md5(
            json.dumps(state, default=str, sort_keys=True).encode()
        ).hexdigest()

    @sync_to_async
    def render_updates(self, state):
        """Render OOB partials for changed sections."""
        # render_to_string with context, wrap in OOB div
        # Return concatenated HTML for all changed sections
        ...
```

### Pattern 2: OOB Swap Message Format

**What:** Server sends HTML with `hx-swap-oob="true"` attributes; HTMX replaces elements by ID.

**When to use:** Every WebSocket push message.

**Example:**
```html
<!-- Multiple sections in one WS message -->
<div id="stats-row" hx-swap-oob="true">
  <!-- Re-rendered stats cards HTML -->
</div>
<div id="recent-builds" hx-swap-oob="true">
  <!-- Re-rendered recent builds HTML -->
</div>
<div id="ci-pipeline-card" hx-swap-oob="true">
  <!-- Re-rendered CI pipeline card HTML -->
</div>
```

### Pattern 3: WebSocket Connection in detail.html

**What:** Place `ws-connect` on a wrapper div outside `#tab-content` so the connection persists across tab switches.

**When to use:** Service detail page template.

**Example:**
```html
<!-- detail.html -->
{% block content %}
<div class="p-8" hx-ext="ws" ws-connect="/ws/services/{{ service.id }}/">
    <div id="tab-content">
        {% include tab_template %}
    </div>
</div>
{% endblock %}
```

### Pattern 4: ASGI Routing Configuration

**What:** Update `asgi.py` to route both HTTP and WebSocket protocols.

**When to use:** One-time setup.

**Example:**
```python
# pathfinder/asgi.py
# Source: Channels 4.3.2 official docs
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pathfinder.settings")

# Must call get_asgi_application() before importing consumers
django_asgi_app = get_asgi_application()

from core.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

```python
# core/routing.py
from django.urls import path
from core.consumers import ServiceConsumer

websocket_urlpatterns = [
    path("ws/services/<int:service_id>/", ServiceConsumer.as_asgi()),
]
```

### Pattern 5: Connection Status via Alpine.js

**What:** Track WebSocket connection state using htmx events and Alpine.js reactive data.

**When to use:** Sidebar connection indicator.

**Example:**
```html
<!-- In base.html Alpine.data registrations -->
Alpine.data('wsStatus', function() {
    return {
        connected: false,
        init: function() {
            var self = this;
            document.addEventListener('htmx:wsOpen', function() {
                self.connected = true;
            });
            document.addEventListener('htmx:wsClose', function() {
                self.connected = false;
            });
            document.addEventListener('htmx:wsError', function() {
                self.connected = false;
            });
        }
    };
});
```

```html
<!-- In nav_service.html sidebar -->
<div x-data="wsStatus()">
    <span class="w-2 h-2 rounded-full inline-block"
          :class="connected ? 'bg-green-400' : 'bg-gray-500'"></span>
</div>
```

### Anti-Patterns to Avoid

- **Sending JSON over WebSocket then parsing in JS:** Contradicts the HTMX-first architecture. Always send rendered HTML.
- **Using channel layers for single-consumer scenarios:** No need for group broadcast when each consumer polls independently. Channel layers add complexity and Redis dependency.
- **Rendering full page HTML over WebSocket:** Only send OOB-wrapped partials for sections that changed, not the entire tab content.
- **Polling inside synchronous consumer:** Must use `AsyncWebsocketConsumer` with `asyncio.sleep()`. A `SyncConsumer` would block the event loop.
- **Forgetting to cancel the poll task on disconnect:** Causes memory leaks and orphaned asyncio tasks.

## Discretion Recommendations

### State Diffing: Use Hash-Based Comparison
**Recommendation:** Hash the entire state dict (JSON serialized) with MD5. Simpler than tracking individual field changes, and the state payload is small (a few KB). Compare the hash to `last_state_hash`; if different, render and push all sections. This avoids tracking which specific fields changed and handles edge cases like new builds appearing.

### Consumer Structure: Single Consumer, Single Class
**Recommendation:** One `ServiceConsumer` class that handles all sections. The consumer fetches all relevant data in one `get_current_state()` call, renders all OOB partials, and sends them in a single message. Separate consumers per section would mean separate WebSocket connections, contradicting the "single connection per service" decision.

### Template Extraction: Extract Dashboard Sections Into Partials
**Recommendation:** Extract these from `_details_tab.html` into reusable partials:
- `_stats_row.html` -- the 4 stat cards grid
- `_recent_builds.html` -- the recent builds table
- `_ci_pipeline_card.html` -- the CI pipeline status card

Both the initial HTTP render (`{% include %}`) and the WebSocket consumer (`render_to_string()`) use the same partials. This ensures visual consistency between page load and real-time updates.

### CI Pipeline Accent Border Colors
**Recommendation:**
- Green (`border-l-green-500`): All synced + webhook active + builds passing
- Amber (`border-l-amber-500`): Out of sync, or recent builds failing, or no webhook
- No accent (default border): No workflow assigned or never pushed

### Stat Cards Clickability
**Recommendation:** Make "Total Builds" and "Last Build" clickable (link to builds tab). "Success Rate" and "Avg Build Time" are purely informational -- no meaningful drill-down target.

### Recent Builds Count
**Recommendation:** Show 5 recent builds (current behavior). This fits well in the dashboard layout and matches the existing `recent_builds = list(builds_qs[:5])` query.

### WS Disconnect Fallback: Reconnect with Backoff Only (No Polling Fallback)
**Recommendation:** Rely on htmx-ext-ws built-in exponential backoff reconnection. Auto-fallback to HTMX polling would require tracking connection state and dynamically adding/removing `hx-trigger="every Ns"` attributes, which adds significant complexity. The page works fine without real-time updates (manual refresh). The reconnection typically succeeds within seconds.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket server protocol | Custom asyncio WebSocket handler | `channels.generic.websocket.AsyncWebsocketConsumer` | Handles protocol frames, handshake, close codes, binary/text frames |
| WebSocket reconnection | Custom JS reconnection logic | htmx-ext-ws built-in exponential backoff | Handles jitter, message queuing, configurable delay function |
| WebSocket authentication | Custom cookie/token parsing | `channels.auth.AuthMiddlewareStack` | Reads Django session cookie from WS handshake headers, populates scope["user"] |
| OOB swap processing | Custom JS DOM manipulation for incoming WS messages | htmx-ext-ws OOB swap | Parses HTML, finds elements by ID, replaces content -- same logic as HTMX OOB |
| WebSocket URL routing | Manual URL parsing in consumer | `channels.routing.URLRouter` with `path()` | Familiar Django URL patterns, captures kwargs into scope |
| ASGI protocol routing | Custom protocol detection | `channels.routing.ProtocolTypeRouter` | Routes HTTP vs WebSocket based on ASGI scope type |
| Origin validation | Custom origin header checking | `channels.security.websocket.AllowedHostsOriginValidator` | Uses Django's ALLOWED_HOSTS, prevents cross-origin WS connections |

**Key insight:** Django Channels + htmx-ext-ws together provide the complete server-to-browser pipeline. The server renders HTML, sends it over WebSocket, and HTMX swaps it into the DOM -- all without custom JavaScript beyond a small Alpine.js connection status component.

## Common Pitfalls

### Pitfall 1: CSP connect-src Does Not Match WebSocket with 'self'
**What goes wrong:** WebSocket connections blocked by CSP policy. Browser console shows `Refused to connect to 'ws://localhost:8000/ws/...' because it violates the Content Security Policy directive: "default-src 'self'"`.
**Why it happens:** CSP `'self'` does NOT reliably match `ws://` or `wss://` schemes across browsers. This is a known spec issue (w3c/webappsec-csp#7).
**How to avoid:** Explicitly add `ws:` and `wss:` to `connect-src` in `SECURE_CSP`:
```python
SECURE_CSP = {
    ...
    "connect-src": [CSP.SELF, "ws:", "wss:"],
}
```
**Warning signs:** WebSocket connection fails silently in browser; no server-side error logs.

### Pitfall 2: manage.py runserver Does Not Support WebSocket
**What goes wrong:** WebSocket connections return 404 or fail to upgrade when using `manage.py runserver`.
**Why it happens:** Django's built-in development server is HTTP-only. WebSocket requires an ASGI server (uvicorn or daphne).
**How to avoid:** Two options:
1. Add `daphne` to INSTALLED_APPS (replaces runserver with ASGI-capable version)
2. Change dev script to use `uvicorn pathfinder.asgi:application --reload --host 127.0.0.1 --port 8000`
**Warning signs:** WS connections fail in development but work in Docker (which uses uvicorn).

### Pitfall 3: Django ORM Calls in Async Consumer Without sync_to_async
**What goes wrong:** `SynchronousOnlyOperation` exception or silent data corruption.
**Why it happens:** Django's ORM is synchronous. Calling it directly from an async context violates Django's safety checks.
**How to avoid:** Wrap ALL ORM calls in `@sync_to_async` decorated methods, or use Django's async ORM methods (`.aget()`, `.acount()`, etc. -- prefixed with `a`).
**Warning signs:** `SynchronousOnlyOperation: You cannot call this from an async context` error at runtime.

### Pitfall 4: Forgetting to Cancel asyncio Task on Disconnect
**What goes wrong:** Memory leak; poll loop continues running after client disconnects, querying the database for a phantom connection.
**Why it happens:** `asyncio.create_task()` creates a fire-and-forget task. Without explicit cancellation, it runs until the event loop shuts down.
**How to avoid:** Store task reference in `self.poll_task`, cancel and await it in `disconnect()`:
```python
async def disconnect(self, close_code):
    if self.poll_task:
        self.poll_task.cancel()
        try:
            await self.poll_task
        except asyncio.CancelledError:
            pass
```
**Warning signs:** Rising memory usage; database query count keeps growing with no active clients.

### Pitfall 5: OOB Swap Target IDs Not Present in DOM
**What goes wrong:** WebSocket sends OOB HTML with `id="stats-row"`, but the current tab doesn't have that element (e.g., user is on CI tab, not dashboard). The HTML is silently discarded.
**Why it happens:** OOB swaps only work when the target element exists in the current DOM.
**How to avoid:** This is actually fine -- HTMX silently ignores OOB swaps for missing IDs. The consumer can always send all sections; only those currently visible get updated. No special handling needed.
**Warning signs:** None -- this is expected behavior, not a bug.

### Pitfall 6: get_asgi_application() Must Be Called Before Importing Consumers
**What goes wrong:** `AppRegistryNotReady` exception when importing consumer modules.
**Why it happens:** Django apps must be initialized before model imports. `get_asgi_application()` calls `django.setup()`.
**How to avoid:** In `asgi.py`, call `get_asgi_application()` BEFORE importing `core.routing`:
```python
django_asgi_app = get_asgi_application()
from core.routing import websocket_urlpatterns  # noqa: E402
```
**Warning signs:** Import errors at startup mentioning `AppRegistryNotReady`.

### Pitfall 7: Template Context Missing in render_to_string
**What goes wrong:** Template renders with empty data or `TemplateSyntaxError` because context variables are missing.
**Why it happens:** When rendering partials via `render_to_string()` in the consumer, you must provide the exact same context that the Django view provides. Missing a context variable causes template errors.
**How to avoid:** Ensure `get_current_state()` returns all data needed by the partials. Create a helper function that builds the template context dict from the state.
**Warning signs:** Blank sections after WS update; template syntax errors in server logs.

### Pitfall 8: SQLite Locking Under Concurrent Access
**What goes wrong:** `database is locked` errors when multiple WebSocket consumers poll SQLite simultaneously.
**Why it happens:** SQLite has limited concurrent write support. Multiple consumers polling every 3 seconds create read contention.
**How to avoid:** Consumer queries are read-only, so contention is minimal with WAL mode (SQLite default in Django). Ensure no writes happen in the consumer. If issues arise, increase poll interval or add `PRAGMA busy_timeout`.
**Warning signs:** Intermittent `OperationalError: database is locked` in consumer logs.

## Code Examples

### Complete asgi.py Setup
```python
# Source: Channels 4.3.2 official docs (routing.html, introduction.html)
"""ASGI config for pathfinder project."""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pathfinder.settings")

# Initialize Django BEFORE importing anything that uses models
django_asgi_app = get_asgi_application()

from core.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

### WebSocket URL Routing
```python
# core/routing.py
from django.urls import path
from core.consumers import ServiceConsumer

websocket_urlpatterns = [
    path("ws/services/<int:service_id>/", ServiceConsumer.as_asgi()),
]
```

### OOB HTML Message Construction
```python
# Source: SaaS Pegasus Django Channels + HTMX guide
from django.template.loader import render_to_string

def build_oob_message(sections):
    """Build multi-section OOB swap message.

    sections: list of (template_name, context_dict, target_id) tuples
    """
    parts = []
    for template, context, target_id in sections:
        html = render_to_string(template, context)
        parts.append(
            f'<div id="{target_id}" hx-swap-oob="true">{html}</div>'
        )
    return "\n".join(parts)
```

### CSP Configuration Update
```python
# In settings.py -- add connect-src for WebSocket
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.NONCE],
    "img-src": [CSP.SELF, "data:", "https://avatars.githubusercontent.com"],
    "connect-src": [CSP.SELF, "ws:", "wss:"],  # NEW: WebSocket support
    "frame-src": [CSP.NONE],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}
```

### detail.html WebSocket Wrapper
```html
{% extends "base.html" %}

{% block sidebar %}
{% include "core/components/nav_service.html" %}
{% endblock %}

{% block content %}
<div class="p-8" hx-ext="ws" ws-connect="/ws/services/{{ service.id }}/">
    <div id="tab-content">
        {% include tab_template %}
    </div>
</div>
{% endblock %}
```

### base.html Script Updates
```html
<!-- Add htmx-ext-ws after htmx.min.js -->
<script src="{% static 'js/vendor/htmx.min.js' %}" nonce="{{ csp_nonce }}"></script>
<script src="{% static 'js/vendor/htmx-ext-ws.min.js' %}" nonce="{{ csp_nonce }}"></script>
```

### Testing WebSocket Consumer
```python
# Source: Channels 4.3.2 testing docs
import pytest
from channels.testing import WebsocketCommunicator
from core.consumers import ServiceConsumer

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_service_consumer_connects():
    communicator = WebsocketCommunicator(
        ServiceConsumer.as_asgi(),
        "/ws/services/1/"
    )
    # Note: Middleware not applied in direct testing
    # For auth testing, use the full ASGI application
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()
```

### Development Script Update (run-dev.sh)
```bash
# Replace: $PYTHON manage.py runserver
# With:    $PYTHON -m uvicorn pathfinder.asgi:application --reload --host 127.0.0.1 --port 8000
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Daphne as only ASGI server for Channels | Uvicorn/Hypercorn fully supported | Channels 4.0 (2023) | No need for daphne in production |
| `hx-ws` built-in attribute (htmx 1.x) | `htmx-ext-ws` external extension | htmx 2.0 (2024-06) | Must install separate extension package |
| Channel layers required for all use cases | Channel layers optional | Channels 4.x docs | Can skip Redis for simple polling patterns |
| `database_sync_to_async` only option | Django async ORM (`aget`, `acount`, etc.) | Django 4.1+ | Can use native async ORM for simple queries |
| Custom reconnection JS | htmx-ext-ws exponential backoff | htmx-ext-ws 2.0 | Built-in reconnection with jitter, message queuing |

**Deprecated/outdated:**
- `hx-ws` attribute: Removed in htmx 2.0, replaced by `htmx-ext-ws` extension
- `channels.layers.InMemoryChannelLayer`: Only for testing, never production
- `daphne` as mandatory: Optional since Channels 4.0; uvicorn is the standard ASGI server for this project

## Open Questions

1. **How many concurrent WebSocket connections can uvicorn handle with SQLite polling?**
   - What we know: Each connection spawns an asyncio task polling every 3s. SQLite reads are fast (<1ms). Uvicorn async event loop can handle thousands of connections.
   - What's unclear: Practical limit with SQLite WAL mode + 2 uvicorn workers (from Dockerfile).
   - Recommendation: Not a concern for this project's scale (single team, <50 concurrent users). Monitor in production; Redis channel layer is the upgrade path.

2. **Will `render_to_string` work correctly inside `sync_to_async`?**
   - What we know: `render_to_string` is synchronous and relies on Django's template engine. It should work inside `@sync_to_async`.
   - What's unclear: Whether template loaders have any async-incompatible caching behavior.
   - Recommendation: Place `render_to_string` inside the same `@sync_to_async` block as ORM calls. Test early.

3. **How does HTMX handle WS messages when no matching OOB target IDs exist?**
   - What we know: HTMX OOB swaps silently ignore elements with IDs not in the DOM.
   - What's unclear: Whether error events fire for unmatched IDs.
   - Recommendation: Verified via htmx docs -- unmatched OOB swaps are silently ignored. Safe to always send all sections.

## Sources

### Primary (HIGH confidence)
- Channels 4.3.2 official docs -- consumers, routing, introduction, testing, authentication
  - https://channels.readthedocs.io/en/stable/topics/consumers.html
  - https://channels.readthedocs.io/en/stable/topics/routing.html
  - https://channels.readthedocs.io/en/stable/introduction.html
  - https://channels.readthedocs.io/en/stable/topics/testing.html
- Channels 4.3.2 CHANGELOG -- confirmed Django 6.0 support, Python 3.9-3.14
  - https://github.com/django/channels/blob/main/CHANGELOG.txt
- htmx-ext-ws official docs -- ws-connect, OOB swaps, events, reconnection
  - https://htmx.org/extensions/ws/
- htmx-ext-ws jsDelivr -- version 2.0.3, dist files: ws.min.js (5KB)
  - https://www.jsdelivr.com/package/npm/htmx-ext-ws
- MDN CSP connect-src -- 'self' does NOT match ws:// reliably
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/connect-src
- Django 6.0 CSP docs -- SECURE_CSP dict format, connect-src directive
  - https://docs.djangoproject.com/en/6.0/ref/csp/

### Secondary (MEDIUM confidence)
- SaaS Pegasus Django Channels + HTMX guide -- render_to_string + OOB pattern
  - https://www.saaspegasus.com/guides/django-websockets-chatgpt-channels-htmx/
- pythontutorials.net -- AsyncWebsocketConsumer periodic task pattern
  - https://www.pythontutorials.net/blog/django-channels-for-asynchronous-periodic-tasks/
- Django Forum -- channels with uvicorn, daphne vs uvicorn for development
  - https://forum.djangoproject.com/t/understanding-a-dev-production-channels-async-setup-with-daphne-and-uvicorn/24259

### Tertiary (LOW confidence)
- None -- all key claims verified via official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Channels 4.3.2 confirmed Django 6 compatible via official changelog; htmx-ext-ws version verified via jsDelivr
- Architecture: HIGH - ProtocolTypeRouter + AsyncWebsocketConsumer + OOB swap pattern documented in official sources and verified via multiple guides
- Pitfalls: HIGH - CSP connect-src limitation verified via MDN; runserver limitation verified via Django docs and community forums; sync_to_async requirement documented in Channels official docs
- Discretion recommendations: MEDIUM - Based on engineering judgment from examining codebase structure; hash-based diffing is straightforward but not verified at this project's scale

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (30 days -- stable ecosystem, no fast-moving dependencies)
