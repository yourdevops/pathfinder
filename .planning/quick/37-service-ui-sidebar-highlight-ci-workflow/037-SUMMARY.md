---
phase: quick-037
plan: 1
subsystem: ui
tags: [htmx, sidebar, ci-workflow, manifest, pr-only, card-selector]

# Dependency graph
requires:
  - phase: 06.1-ci-workflows-gap
    provides: "CI workflow assignment, version pinning, manifest push views"
provides:
  - "Dynamic sidebar highlight on HTMX tab navigation"
  - "Consolidated CI Workflow tab with rich card selectors"
  - "PR-only manifest push enforcement (direct push removed)"
affects: [services, ci-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JS-based sidebar highlight with data-service-nav attributes and htmx:pushedIntoHistory listener"
    - "Mini-card radio selector pattern for workflow/version picking"
    - "Save-on-change pattern: hidden button revealed when selection differs from initial value"

key-files:
  created: []
  modified:
    - core/templates/core/components/nav_service.html
    - core/templates/core/services/_ci_tab.html
    - core/templates/core/services/_settings_tab.html
    - core/views/services.py
    - core/urls.py
    - core/models.py
    - core/tasks.py

key-decisions:
  - "Pure JS + HTMX events for sidebar highlight instead of Alpine.js (CSP-compatible build limitation)"
  - "PR-only manifest push: removed direct push option entirely from model, views, URLs, tasks"
  - "Mini-card workflow selector with runtime/artifact badges instead of plain dropdown"
  - "Version status shown as colored badges: green=authorized, amber=draft, red=revoked"
  - "Workflow and version selectors side-by-side in 2/3 + 1/3 grid layout"

patterns-established:
  - "data-service-nav attribute pattern for sidebar highlight across HTMX tab switches"
  - "Card-based radio selector with hidden input for rich form selection"

# Metrics
duration: 10min
completed: 2026-02-16
---

# Quick Task 037: Service UI Sidebar Highlight & CI Workflow Tab Summary

**Dynamic sidebar highlight via JS/HTMX events, consolidated CI tab with rich mini-card workflow/version selectors, and PR-only manifest push enforcement**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-16T11:29:58Z
- **Completed:** 2026-02-16T11:40:49Z
- **Tasks:** 3 (2 auto + 1 checkpoint with refinements)
- **Files modified:** 7

## Accomplishments
- Sidebar nav highlight dynamically follows active tab on HTMX tab switches without full page reload
- CI Workflow tab consolidated from 4 separate cards into one unified card with workflow/version selectors side-by-side
- Workflow selector redesigned as rich mini-cards showing name, runtime badge, artifact type, and description
- Version selector shows colored status badges (green authorized, amber draft, red revoked)
- Save buttons appear only when user changes selection from current value
- Push Manifest button context-aware: "Update Pull Request" when PR exists, hidden when synced
- PR-only manifest push enforced across model, views, URLs, tasks, and settings UI

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix sidebar highlight and enforce PR-only manifest flow** - `ed39414` (feat)
2. **Task 2: Consolidate CI Workflow tab into single card** - `608dceb` (feat)
3. **Task 2 refinement: Rich card selectors with inline layout** - `cd65785` (feat)

## Files Created/Modified
- `core/templates/core/components/nav_service.html` - Replaced Django template conditionals with JS-based sidebar highlight using data-service-nav attributes
- `core/templates/core/services/_ci_tab.html` - Consolidated 4 cards into 1, mini-card workflow selector, version cards with status badges, side-by-side layout
- `core/templates/core/services/_settings_tab.html` - Removed CI Manifest Push Method section
- `core/views/services.py` - Removed ServiceUpdatePushMethodView class
- `core/urls.py` - Removed service_update_push_method URL pattern and import
- `core/models.py` - Hardcoded PR-only choice on ci_manifest_push_method field
- `core/tasks.py` - Removed direct push branch from push_ci_manifest, updated docstring

## Decisions Made
- Used pure JS + HTMX `pushedIntoHistory` event for sidebar highlight instead of Alpine.js due to CSP-compatible build not supporting inline expressions
- Removed direct push option entirely (not just hidden) -- PR is the only manifest delivery method
- Workflow selector uses mini-cards with radio-style indicators instead of native `<select>` dropdown for richer display
- Version and workflow selectors placed side-by-side (2/3 + 1/3 grid) to show version as emerging property of workflow
- Status badges use consistent color scheme: green=authorized/synced, amber=draft/out-of-date, red=revoked, gray=never-pushed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unnecessary humanize template tag load**
- **Found during:** Task 2
- **Issue:** `{% load humanize %}` was added but `timesince` is a built-in Django filter, not from humanize
- **Fix:** Removed the unnecessary tag load
- **Files modified:** core/templates/core/services/_ci_tab.html
- **Committed in:** 608dceb

**2. [Rule 1 - Bug] Updated push_ci_manifest docstring**
- **Found during:** Task 1
- **Issue:** Docstring still referenced "both PR and direct push modes" after removing direct push
- **Fix:** Updated docstring to reflect PR-only behavior
- **Files modified:** core/tasks.py
- **Committed in:** ed39414

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Minor correctness fixes. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Service UI navigation is now robust with dynamic sidebar highlighting
- CI Workflow management consolidated into a clean, rich interface
- PR-only manifest push simplifies the delivery model

---
*Quick Task: 037*
*Completed: 2026-02-16*
