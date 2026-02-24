# Phase 9: WebSockets for Service's pages - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add real-time push updates to service detail pages via a single WebSocket connection per page, replacing HTMX polling patterns. Includes refinements to the new service detail dashboard (empty state strategy, UI polish from frontend design review). Does NOT include WebSocket support for other pages (builds list, CI workflows, etc.) — only the service detail context.

</domain>

<decisions>
## Implementation Decisions

### Architecture: Django Channels + HTMX WS Extension
- Use Django Channels 4.3.2 (compatible with Django 6.x) for server-side WebSocket consumers
- Use HTMX WebSocket extension (`htmx-ext-ws`) for client-side — sends HTML partials via OOB swaps, no custom JS needed
- Single WebSocket connection per service detail page
- Server pushes rendered Django template partials wrapped in `hx-swap-oob="true"` divs
- Reuse existing template partials for both initial HTTP render and WebSocket pushes
- CSP-compatible: htmx-ext-ws does not use eval(), works with Alpine CSP build

### Transport: Database Polling (No Redis)
- Consumer polls SQLite every 3 seconds, pushes only when state changes
- No channel layer needed — avoids Redis dependency
- Acceptable latency: 0-3 seconds for dashboard updates
- If instant push becomes necessary later, Redis channel layer can be added as Phase 2 without changing consumer interface

### Connection Lifecycle
- Place `ws-connect` on `detail.html` content wrapper (outside `#tab-content`)
- Connection stays open across HTMX tab switches within the same service (tab content is swapped inside the WS wrapper)
- Connection closes when navigating away from the service (DOM element removed)
- Built-in HTMX exponential backoff reconnection on unexpected closure
- Authentication via `AuthMiddlewareStack` — reads session cookie from WS handshake

### Update Scope
- Multiple dashboard sections updated from a single WS message via OOB swaps by element ID
- Sections that get real-time updates: build stats, CI pipeline status, recent builds, scaffold progress
- Service info section (repo, metadata) does NOT need real-time updates — static after creation
- Each updatable section gets a stable `id` attribute for OOB targeting

### ASGI Setup
- Project already runs uvicorn with ASGI (`Dockerfile` line 62: `uvicorn pathfinder.asgi:application`)
- Only change needed: update `asgi.py` to use `ProtocolTypeRouter` routing HTTP and WebSocket
- No migration from Gunicorn needed — already on ASGI
- Traefik supports WebSocket upgrade automatically, no proxy config changes

### Dashboard Polish (from frontend design review)
- Wrap stats row + recent builds in `{% if total_builds > 0 %}` — hide when no builds, show "Getting Started" onboarding card instead
- Make commit SHAs clickable links in recent builds (link to commit URL like `_build_row.html` does)
- Add left accent border to CI Pipeline card based on health (green = all healthy, amber = needs attention)
- Make environment/variable counts clickable — switch to respective tabs via HTMX
- CI Pipeline empty state gets dashed-border card with icon instead of plain centered text

### Claude's Discretion
- Exact polling comparison logic (hash-based vs field-based state diffing)
- Consumer class structure (single consumer vs separate per-section)
- Whether to extract dashboard sections into separate partial templates for reuse
- Onboarding card content and layout details
- Exact accent border color logic for CI Pipeline card

</decisions>

<specifics>
## Specific Ideas

- "The first thing developers see when opening a service should answer: Is it healthy? What happened recently? What needs my attention?"
- HTMX WS extension's OOB swap pattern is the key mechanism — server sends `<div id="X" hx-swap-oob="true">...</div>` and HTMX replaces the matching element
- Current HTMX polling patterns to replace: scaffold status (`hx-trigger="every 3s"`), builds tab (`hx-trigger="every 5s"`)
- Four stat cards showing dashes for a fresh service is visual noise — replace with setup guidance
- Reference: Vercel, Railway, Render all collapse operational sections until there's data

</specifics>

<deferred>
## Deferred Ideas

- WebSocket support for other pages (builds list with live status, CI workflow sync progress) — future phase
- Redis channel layer for instant push from background workers — can be added without interface changes
- Bidirectional features (cancel build, trigger re-deploy from dashboard via WS) — future phase
- Service detail header deduplication with sidebar — minor UI cleanup, separate task

</deferred>

---

*Phase: 09-websockets-for-service-s-pages*
*Context gathered: 2026-02-24*
