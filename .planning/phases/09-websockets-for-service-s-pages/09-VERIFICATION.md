---
phase: 09-websockets-for-service-s-pages
verified: 2026-02-24T20:45:25Z
status: passed
score: 9/9 success criteria verified
re_verification: false
gaps: []
resolved_gaps:
  - truth: "Dashboard sections update in real-time when build status changes (for services transitioning from 0 to >0 builds)"
    status: resolved
    reason: "Fixed by adding id='dashboard-stats-row' with OOB conditional to _dashboard_empty.html (commit 7c3259f)"
    artifacts:
      - path: "core/templates/core/services/_dashboard_empty.html"
        issue: "Template has no id attribute and no {% if oob %}hx-swap-oob=\"true\"{% endif %} pattern on its root elements, unlike all other OOB-targetable partials. Consumer sets oob=True in context but the template ignores it."
    missing:
      - "Either wrap _dashboard_empty.html content in a div with id='dashboard-stats-row' and the OOB conditional pattern, OR wrap it in a stable outer div with id='dashboard-section' and route the consumer to send that ID. This would make the empty->has-builds transition happen in real-time without a refresh."
human_verification:
  - test: "Navigate to a service detail page with no builds. Trigger a build (via Fetch Builds or webhook). Observe whether the page auto-updates within 3 seconds to show stats row, or requires a manual refresh."
    expected: "Page auto-updates within 3 seconds when first build data arrives (currently requires manual refresh due to _dashboard_empty.html missing OOB swap target)."
    why_human: "Real-time DOM behavior cannot be verified statically. The gap analysis is based on code inspection of the OOB swap mechanism; actual browser behavior confirms whether HTMX silently drops the swap or finds an alternative target."
  - test: "Navigate to a service detail page with existing builds. Trigger a build status change. Observe the dashboard stats row and recent builds section."
    expected: "Both sections update within 3 seconds without page refresh."
    why_human: "Core real-time path needs functional confirmation."
  - test: "Switch between all service tabs (Details, CI Workflow, Builds, Environments, Settings) while watching the green dot in sidebar."
    expected: "Green dot remains green throughout all tab switches — WebSocket connection persists across HTMX tab swaps."
    why_human: "Connection lifecycle behavior is dynamic and cannot be verified statically."
---

# Phase 9: WebSockets for Service's Pages — Verification Report

**Phase Goal:** Real-time push updates to all service-context pages via a single WebSocket connection per service detail view, replacing HTMX polling with Django Channels + htmx-ext-ws OOB swaps; includes dashboard empty state improvements and UI polish
**Verified:** 2026-02-24T20:45:25Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from Success Criteria)

| #  | Truth                                                                                  | Status      | Evidence                                                                 |
|----|----------------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------|
| 1  | WebSocket connection opens on service detail page and persists across tab switches     | VERIFIED    | `ws-connect="/ws/services/{{ service.id }}/"` on outer div outside `#tab-content` in `detail.html:8` |
| 2  | Dashboard stats, recent builds, and CI pipeline card update within 3s when data changes | PARTIAL     | OOB works for services with existing builds; empty->has-builds transition has no DOM target (see Gaps) |
| 3  | Builds list tab refreshes automatically when any build changes status                  | VERIFIED    | `_builds_tab.html` has `id="builds-tab-content" {% if oob %}hx-swap-oob="true"{% endif %}`; consumer renders it every poll cycle |
| 4  | CI workflow tab shows manifest sync status updates in real-time                        | VERIFIED    | `_ci_manifest_status.html` has `id="ci-manifest-status"` with OOB conditional; consumer renders it when `ci_workflow` is set |
| 5  | Sidebar shows green dot when WebSocket is connected, gray when disconnected            | VERIFIED    | `wsStatus` Alpine component in `base.html:370`; used via `x-data="wsStatus()"` in `nav_service.html:15` |
| 6  | Dashboard shows contextual empty states (no workflow -> assign CTA, no builds -> fetch CTA) | VERIFIED | `_dashboard_empty.html` has both states (`Set Up CI Pipeline`, `No Builds Yet` + `Fetch Builds`); used conditionally in `_details_tab.html:56` |
| 7  | Commit SHAs in recent builds are clickable links                                       | VERIFIED    | `_recent_builds.html:30-36`: links to `ci_run_url` first, then repo commit URL, then plain text |
| 8  | CI Pipeline card has accent border based on health status                              | VERIFIED    | `_ci_pipeline_card.html:6-8`: `border-l-4 border-l-green-500` (healthy) and `border-l-4 border-l-amber-500` (needs attention) |
| 9  | Page works without WebSocket (manual refresh fallback)                                 | VERIFIED    | `ws-fallback-warning` div is `class="hidden"` by default; vanilla JS only shows it after initial connect + disconnect; page renders via Django HTTP as before |

**Score:** 8/9 — SC2 is partial (active services update fine; empty-to-first-build transition requires manual refresh)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `core/consumers.py` | ServiceConsumer with polling loop and OOB rendering (min 80 lines) | VERIFIED | 275 lines; `AsyncWebsocketConsumer` with `poll_loop()`, `get_current_state()`, SHA-256 `compute_hash()`, `build_template_context()`, full `render_updates()` |
| `core/routing.py` | WebSocket URL routing with `websocket_urlpatterns` | VERIFIED | 7 lines; `path("ws/services/<int:service_id>/", ServiceConsumer.as_asgi())` |
| `pathfinder/asgi.py` | `ProtocolTypeRouter` for HTTP + WebSocket | VERIFIED | `ProtocolTypeRouter`, `AllowedHostsOriginValidator`, `AuthMiddlewareStack`, `URLRouter` |
| `theme/static/js/vendor/htmx-ext-ws.min.js` | Client-side WebSocket extension | VERIFIED | File exists at expected path |
| `core/templates/core/services/_stats_row.html` | Stats row partial with OOB id (min 20 lines) | VERIFIED | 71 lines; `id="dashboard-stats-row"` with `{% if oob %}hx-swap-oob="true"{% endif %}` |
| `core/templates/core/services/_recent_builds.html` | Recent builds partial with OOB id (min 15 lines) | VERIFIED | 66 lines; `id="dashboard-recent-builds"` with OOB conditional |
| `core/templates/core/services/_ci_pipeline_card.html` | CI pipeline card partial with OOB id (min 15 lines) | VERIFIED | 82 lines; `id="dashboard-ci-pipeline"` with OOB conditional |
| `core/templates/core/services/_dashboard_empty.html` | Conditional empty state partial (min 15 lines) | PARTIAL | 39 lines; content is substantive but has **no stable id or OOB conditional** — cannot be OOB-targeted by consumer |
| `core/templates/core/services/_details_tab.html` | Refactored dashboard using `{% include %}` | VERIFIED | Uses `{% include %}` for all 3 partials; HTMX polling removed |
| `core/templates/core/services/detail.html` | WebSocket wrapper with `ws-connect` | VERIFIED | `hx-ext="ws" ws-connect="/ws/services/{{ service.id }}/"` at line 8 |
| `core/templates/core/components/nav_service.html` | Connection status indicator dot | VERIFIED | `x-data="wsStatus()"` wrapper; green/gray dot at lines 15-23 |
| `core/templates/core/services/_ci_manifest_status.html` | CI manifest status partial with OOB id | VERIFIED | `id="ci-manifest-status"` with OOB conditional; included in `_ci_tab.html:155` |

---

## Key Link Verification

### Plan 09-01 Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pathfinder/asgi.py` | `core/routing.py` | `from core.routing import websocket_urlpatterns` | WIRED | `asgi.py:22`: `from core.routing import websocket_urlpatterns  # noqa: E402` |
| `core/routing.py` | `core/consumers.py` | `ServiceConsumer.as_asgi()` | WIRED | `routing.py:6`: `path("ws/services/<int:service_id>/", ServiceConsumer.as_asgi())` |
| `theme/templates/base.html` | `theme/static/js/vendor/htmx-ext-ws.min.js` | `<script>` tag | WIRED | `base.html:392`: `<script src="{% static 'js/vendor/htmx-ext-ws.min.js' %}" nonce="{{ csp_nonce }}">` |

### Plan 09-02 Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_details_tab.html` | `_stats_row.html` | `{% include %}` | WIRED | `_details_tab.html:59`: `{% include "core/services/_stats_row.html" %}` |
| `_details_tab.html` | `_recent_builds.html` | `{% include %}` | WIRED | `_details_tab.html:69`: `{% include "core/services/_recent_builds.html" %}` |
| `_details_tab.html` | `_ci_pipeline_card.html` | `{% include %}` | WIRED | `_details_tab.html:64`: `{% include "core/services/_ci_pipeline_card.html" %}` |
| `core/views/services.py` | `_dashboard_empty.html` | context `show_empty_state` | WIRED | `services.py:613`: `context["show_empty_state"] = context["total_builds"] == 0` |

### Plan 09-03 Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `detail.html` | `core/consumers.py` | `ws-connect` URL | WIRED | `detail.html:8`: `ws-connect="/ws/services/{{ service.id }}/"` matches `routing.py` pattern |
| `core/consumers.py` | `_stats_row.html` | `render_to_string` with `oob=True` | WIRED | `consumers.py:249`: `render_to_string("core/services/_stats_row.html", ctx)` |
| `core/consumers.py` | `_recent_builds.html` | `render_to_string` with `oob=True` | WIRED | `consumers.py:251`: `render_to_string("core/services/_recent_builds.html", ctx)` |
| `core/consumers.py` | `_ci_pipeline_card.html` | `render_to_string` with `oob=True` | WIRED | `consumers.py:252`: `render_to_string("core/services/_ci_pipeline_card.html", ctx)` |
| `core/consumers.py` | `_builds_tab.html` | `render_to_string` | WIRED | `consumers.py:255`: `render_to_string("core/services/_builds_tab.html", ctx)` |
| `core/consumers.py` | `_dashboard_empty.html` | `render_to_string` with `oob=True` | BROKEN | Consumer sends rendered empty state HTML but template has no OOB target id. HTMX silently discards it. Empty->has-builds transition does not update the DOM. |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SRVC-09 | 09-01, 09-02, 09-03, 09-04 | Contributor can view service details (overview, builds, deployments) | SATISFIED | REQUIREMENTS.md marks SRVC-09 Complete (Phase 5). Phase 9 extends this with real-time WebSocket updates. All planned features implemented. REQUIREMENTS.md phase-to-req mapping table does not have a Phase 9 row — no new requirement IDs were added for this phase, which matches ROADMAP.md declaring SRVC-09 as the inherited requirement. |

**Orphaned requirements:** None — REQUIREMENTS.md has no requirement IDs mapped to Phase 9. ROADMAP.md Phase 9 uses SRVC-09 (already completed in Phase 5) as its requirement, indicating this phase enhances the existing capability rather than introducing a new one.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `core/templates/core/services/_dashboard_empty.html` | 1-39 | Missing OOB id/swap-oob conditional despite being rendered by consumer with `oob=True` | Warning | Consumer call at `consumers.py:247` sets `oob=True` in context but template doesn't reference `oob` variable. `render_to_string` succeeds but returns plain HTML with no `hx-swap-oob` attribute — HTMX drops it silently when received over WebSocket. |

No TODO/FIXME/PLACEHOLDER comments found in any phase files.
No empty `return null`, `return {}`, `return []` stubs found.

---

## Human Verification Required

### 1. Empty-State to Has-Builds Transition

**Test:** Navigate to a service with no builds. Trigger build fetching (Fetch Builds button or wait for webhook). Observe whether the dashboard auto-updates within 3 seconds or requires manual refresh.
**Expected (design intent):** Dashboard should update automatically. **Actual (code analysis):** Requires manual refresh because `_dashboard_empty.html` has no stable OOB swap target id.
**Why human:** Dynamic DOM behavior after WebSocket message cannot be verified statically.

### 2. WebSocket Persistence Across Tab Switches

**Test:** Navigate to service detail page. Confirm green dot appears. Click CI Workflow tab, then Builds tab, then back to Details. Monitor the green dot throughout.
**Expected:** Green dot remains green — the `ws-connect` is outside `#tab-content` so tab switches (which replace `#tab-content`) do not close the WebSocket.
**Why human:** HTMX + htmx-ext-ws interaction lifecycle cannot be verified statically.

### 3. Real-Time Dashboard Update (Active Service)

**Test:** Navigate to a service with existing builds. Trigger a build status change (e.g., manually update a build via admin or API). Observe stats row and recent builds.
**Expected:** Both sections update within 3 seconds. The SHA-256 hash of state changes → consumer detects → renders OOB partials → HTMX swaps into `dashboard-stats-row` and `dashboard-recent-builds`.
**Why human:** Requires a running server with actual build state changes.

---

## Gaps Summary

**One gap blocks full goal achievement:**

The `_dashboard_empty.html` template is rendered by the consumer when `total_builds == 0`, but unlike all other OOB partials (`_stats_row.html`, `_recent_builds.html`, `_ci_pipeline_card.html`, `_builds_tab.html`, `_ci_manifest_status.html`), it has no stable `id` attribute and no `{% if oob %}hx-swap-oob="true"{% endif %}` conditional on its root elements.

**Root cause:** When the page first loads with 0 builds, `_details_tab.html` renders `_dashboard_empty.html` inline via `{% include %}`. This produces raw HTML content — no wrapper div with an id. Later when the consumer detects state changes (even while still at 0 builds), it sends the empty state HTML over WebSocket, but HTMX has no element to target for the swap.

**Most critical scenario:** When a service goes from 0 builds to its first build, the consumer switches from sending `_dashboard_empty.html` to sending `_stats_row.html` (with `id="dashboard-stats-row"`). But `#dashboard-stats-row` doesn't exist in the DOM — the page rendered the empty state instead. HTMX silently ignores the OOB swap. The page shows the empty state until manually refreshed.

**Affected scope:** Only the "first build ever" transition. Once a service has builds and the page is refreshed (or first loaded with builds), all real-time updates work correctly via the established OOB swap mechanism.

**Fix required:** Add a stable wrapper div with a consistent id to `_dashboard_empty.html` content, or restructure `_details_tab.html` to have a stable container div (e.g., `<div id="dashboard-section">`) that wraps both the empty state and the stats row, then route the consumer OOB swap to target `#dashboard-section`.

---

_Verified: 2026-02-24T20:45:25Z_
_Verifier: Claude (gsd-verifier)_
