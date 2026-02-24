---
phase: 09-websockets-for-service-s-pages
plan: 02
subsystem: ui
tags: [htmx, oob-swap, websocket-prep, dashboard, template-partials]

# Dependency graph
requires:
  - phase: 09-01
    provides: WebSocket infrastructure (ASGI routing, consumer base)
provides:
  - Reusable template partials with stable OOB target IDs for dashboard stats, recent builds, CI pipeline
  - Conditional empty state partial for services without builds
  - Dashboard sections extractable for WebSocket OOB push rendering
affects: [09-03, 09-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [conditional hx-swap-oob via template variable, dashboard empty state pattern]

key-files:
  created:
    - core/templates/core/services/_stats_row.html
    - core/templates/core/services/_recent_builds.html
    - core/templates/core/services/_ci_pipeline_card.html
    - core/templates/core/services/_dashboard_empty.html
  modified:
    - core/templates/core/services/_details_tab.html
    - core/views/services.py

key-decisions:
  - "OOB pattern uses {% if oob %}hx-swap-oob=true{% endif %} on root div of each partial"
  - "Commit SHAs link to ci_run_url first, then repo commit URL, then plain text fallback"
  - "CI pipeline accent border: green for fully healthy, amber for needs attention, none for unconfigured"
  - "Stats row hidden when total_builds == 0, replaced by contextual empty state"

patterns-established:
  - "OOB partial pattern: root div with stable id and conditional hx-swap-oob for dual HTTP/WS rendering"
  - "Dashboard empty state: conditional guidance based on service setup progress"

requirements-completed: [SRVC-09]

# Metrics
duration: 3min
completed: 2026-02-24
---

# Phase 09 Plan 02: Dashboard Partials Summary

**Service dashboard refactored into OOB-targetable partials with conditional empty states, clickable commit SHAs, and CI pipeline health accent borders**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-24T19:54:43Z
- **Completed:** 2026-02-24T19:57:36Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Extracted dashboard stats row, recent builds, and CI pipeline into reusable partials with stable OOB target IDs
- Implemented conditional empty state: no-workflow CTA, no-builds fetch CTA, normal dashboard with stats
- Made commit SHAs clickable (links to CI run URL or repo commit URL with fallback)
- Added health-based left accent border to CI pipeline card (green/amber/none)
- Removed HTMX polling from scaffold badge (will be replaced by WebSocket push in Plan 03)
- CI pipeline empty state uses dashed-border card with pipeline icon

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract dashboard sections into reusable partials with OOB IDs** - `18704ac` (feat)
2. **Task 2: Implement conditional empty states and update view context** - `b922fd4` (feat)

## Files Created/Modified
- `core/templates/core/services/_stats_row.html` - Stats row partial with clickable Last Build and Total Builds cards
- `core/templates/core/services/_recent_builds.html` - Recent builds partial with clickable commit SHA links
- `core/templates/core/services/_ci_pipeline_card.html` - CI pipeline card partial with health accent border and dashed empty state
- `core/templates/core/services/_dashboard_empty.html` - Conditional empty state with setup guidance CTAs
- `core/templates/core/services/_details_tab.html` - Refactored to use include for partials, removed polling
- `core/views/services.py` - Added show_empty_state context variable

## Decisions Made
- OOB pattern: each partial has root `<div id="..." {% if oob %}hx-swap-oob="true"{% endif %}>` for dual HTTP/WS rendering
- Commit SHA link priority: ci_run_url > repo commit URL > plain text
- CI pipeline accent: green when synced + webhook + last build success; amber when out of sync, failed build, or no webhook
- Last Build and Total Builds cards made clickable (link to builds tab); Success Rate and Avg Build Time kept non-clickable

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All dashboard partials have stable OOB target IDs ready for WebSocket consumer in Plan 03
- Plan 03 can render these partials with `oob=True` context to push real-time updates
- Scaffold badge polling removed; Plan 03 will add WebSocket push for scaffold status

## Self-Check: PASSED

All 5 created files verified on disk. Both task commits (18704ac, b922fd4) verified in git history.

---
*Phase: 09-websockets-for-service-s-pages*
*Completed: 2026-02-24*
