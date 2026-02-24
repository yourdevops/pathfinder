# Phase 9: WebSockets for Service's pages - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add real-time push updates to all service-context pages via a single WebSocket connection per service detail view, replacing HTMX polling patterns. Covers: service dashboard, builds list, build detail, CI workflow tab. Includes dashboard empty state improvements and UI polish. Does NOT include WebSocket support for pages outside the service context (CI workflows list, steps catalog, etc.).

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
- If instant push becomes necessary later, Redis channel layer can be added without changing consumer interface

### Connection Lifecycle
- Place `ws-connect` on `detail.html` content wrapper (outside `#tab-content`)
- Connection stays open across HTMX tab switches within the same service (tab content is swapped inside the WS wrapper)
- Connection closes when navigating away from the service (DOM element removed)
- Built-in HTMX exponential backoff reconnection on unexpected closure
- Authentication via `AuthMiddlewareStack` — reads session cookie from WS handshake

### Real-Time Update Scope (expanded from original)
- **Service dashboard**: build stats, scaffold progress (pending/done only — no step-by-step), CI pipeline health
- **Builds list**: full list refresh when any build changes status (queued → running → success/failed) — ensures sort order and new builds appear correctly
- **Build detail**: status update only when build completes — logs fetched on demand, not streamed
- **CI workflow tab**: manifest sync status
- Service info section (repo, metadata) does NOT need real-time updates — static after creation
- Each updatable section gets a stable `id` attribute for OOB targeting
- Multiple sections updated from a single WS message via OOB swaps by element ID

### New Build Notification
- New builds get a subtle visual indicator — brief highlight on new/changed rows so user notices new activity
- No toast or intrusive notification

### Connection Status Indicator
- Small dot next to the service name in the left sidebar showing connected/disconnected state
- Green when WebSocket is connected, changes when disconnected

### Fallback & Error Handling
- If WebSocket can't connect at all (Channels not running), show a subtle "Live updates unavailable" warning banner
- Page works fine without WS — just no live updates, manual refresh still works
- Claude's Discretion: whether to auto-fallback to polling or rely on reconnect only

### ASGI Setup
- Project already runs uvicorn with ASGI (`Dockerfile` line 62: `uvicorn pathfinder.asgi:application`)
- Only change needed: update `asgi.py` to use `ProtocolTypeRouter` routing HTTP and WebSocket
- No migration from Gunicorn needed — already on ASGI
- Traefik supports WebSocket upgrade automatically, no proxy config changes

### Dashboard Empty State (conditional)
- If no CI Workflow assigned: show card with link to assign a CI Workflow
- If CI Workflow assigned but no builds: show card with "Fetch Builds" button (manual poll — webhook could fail)
- If builds exist: show stats row + recent builds normally
- Hide stats cards and recent builds section entirely when total_builds=0 — no dashes for empty state

### Dashboard Polish (from frontend design review)
- Make commit SHAs clickable links in recent builds (link to commit URL)
- Add left accent border to CI Pipeline card based on health (green = healthy, amber = needs attention)
- CI Pipeline empty state gets dashed-border card with icon instead of plain centered text
- No additional CI Pipeline info beyond what exists — build stats row already covers it

### Claude's Discretion
- Exact polling comparison logic (hash-based vs field-based state diffing)
- Consumer class structure (single consumer vs separate per-section)
- Whether to extract dashboard sections into separate partial templates for reuse
- Onboarding card layout details
- Exact accent border color logic for CI Pipeline card
- Which stat cards should be clickable (link to relevant tabs)
- Number of recent builds to show on dashboard
- Whether to auto-fallback to HTMX polling on WS disconnect or rely on reconnect with backoff

</decisions>

<specifics>
## Specific Ideas

- "The first thing developers see when opening a service should answer: Is it healthy? What happened recently? What needs my attention?"
- HTMX WS extension's OOB swap pattern is the key mechanism — server sends `<div id="X" hx-swap-oob="true">...</div>` and HTMX replaces the matching element
- Current HTMX polling patterns to replace: scaffold status (`hx-trigger="every 3s"`), builds tab (`hx-trigger="every 5s"`)
- Four stat cards showing dashes for a fresh service is visual noise — replace with contextual setup guidance
- Reference: Vercel, Railway, Render all collapse operational sections until there's data
- Empty state is conditional on service progress: no workflow → assign workflow CTA, workflow but no builds → fetch builds CTA
- All service-context pages (dashboard, builds, build detail, CI tab) share the single WS connection

</specifics>

<deferred>
## Deferred Ideas

- WebSocket support for pages outside service context (CI workflows list, steps catalog, project dashboard) — future phase
- Redis channel layer for instant push from background workers — can be added without interface changes
- Bidirectional features (cancel build, trigger re-deploy from dashboard via WS) — future phase
- Service detail header deduplication with sidebar — minor UI cleanup, separate task
- Real-time log streaming for build detail — status updates only for now, streaming deferred

</deferred>

---

*Phase: 09-websockets-for-service-s-pages*
*Context gathered: 2026-02-24*
