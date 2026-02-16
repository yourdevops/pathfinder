---
phase: quick-038
plan: 1
subsystem: ui
tags: [alpine-js, htmx, ci-workflows, dynamic-dropdown, csp-compatible]

# Dependency graph
requires:
  - phase: quick-037
    provides: CI workflow tab consolidation with workflow + version selectors
provides:
  - Client-side workflow-to-versions map for instant version swapping
  - Alpine ciSelector component with pickWf/pickVer methods
  - Dynamic x-for version dropdown driven by Alpine data
affects: [ci-workflows, service-detail]

# Tech tracking
tech-stack:
  added: []
  patterns: [Alpine.data ciSelector component for multi-dropdown coordination]

key-files:
  created: []
  modified:
    - core/views/services.py
    - core/templates/core/services/_ci_tab.html
    - theme/templates/base.html

key-decisions:
  - "Workflow dropdown items remain server-rendered (Django for loop) since workflow list is static; only version items use Alpine x-for for reactivity"
  - "Version map keyed by string workflow ID for JSON/Alpine compatibility"
  - "pickWf auto-selects first (latest) version from map when switching workflows"

patterns-established:
  - "ciSelector pattern: single Alpine.data scope wrapping multiple coordinated dropdowns with shared state"

# Metrics
duration: 2min
completed: 2026-02-16
---

# Quick Task 038: Dynamic CI Workflow Version Swapping Summary

**Client-side workflow-versions map with Alpine ciSelector component for instant version dropdown swapping without page reload**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-16T12:50:53Z
- **Completed:** 2026-02-16T12:53:16Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Built workflow_versions_json context variable mapping all available workflows to their versions
- Registered Alpine.data ciSelector component with pickWf/pickVer for coordinated dropdown behavior
- Rewrote CI tab version dropdown to use Alpine x-for for dynamic, reactive rendering
- Latest version auto-selected when switching workflows; version section hidden when no workflow selected

## Task Commits

Each task was committed atomically:

1. **Task 1: Build workflow-versions map in view and register Alpine ciSelector component** - `c569e90` (feat)
2. **Task 2: Rewrite CI tab template to use ciSelector component with dynamic version swapping** - `f90f2ee` (feat)

## Files Created/Modified
- `core/views/services.py` - Added workflow_versions_json context with versions map for all available workflows
- `core/templates/core/services/_ci_tab.html` - Rewrote edit mode to use ciSelector with Alpine x-for version dropdown
- `theme/templates/base.html` - Registered ciSelector Alpine.data component with pickWf/pickVer methods

## Decisions Made
- Workflow dropdown items remain server-rendered via Django for loop (static data, no reactivity needed)
- Only version dropdown items use Alpine x-for (need to reactively update when workflow changes)
- Version map keyed by string workflow ID for JSON/Alpine string comparison compatibility
- pickWf auto-selects first version (latest by published_at ordering) when switching workflows

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Dynamic version swapping functional
- Both workflow and version Save buttons still submit via HTMX POST as before
- Read-only view unchanged for viewer role users

---
*Quick Task: 038*
*Completed: 2026-02-16*
