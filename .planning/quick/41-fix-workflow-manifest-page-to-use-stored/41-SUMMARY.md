---
phase: quick-41
plan: 01
subsystem: ui
tags: [django, ci-workflows, manifest, versions]

requires:
  - phase: 06.1
    provides: CIWorkflowVersion model with manifest_content and WorkflowManifestView pattern
provides:
  - Version-prioritized manifest display in WorkflowDetailView (draft > authorized > fresh generate)
affects: [ci-workflows, workflow-detail]

tech-stack:
  added: []
  patterns: [version-prioritized manifest resolution]

key-files:
  created: []
  modified:
    - core/views/ci_workflows.py
    - core/templates/core/ci_workflows/workflow_detail.html

key-decisions:
  - "Manifest tab uses stored version content matching WorkflowManifestView priority pattern"

patterns-established:
  - "Version-prioritized manifest resolution: draft > authorized > fresh generate fallback"

requirements-completed: [quick-41]

duration: 1min
completed: 2026-02-17
---

# Quick Task 41: Fix Workflow Manifest Page Summary

**WorkflowDetailView manifest tab now shows stored version content (draft > authorized > fresh generate) instead of always regenerating**

## Performance

- **Duration:** 33s
- **Started:** 2026-02-17T20:20:06Z
- **Completed:** 2026-02-17T20:20:39Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- WorkflowDetailView.get() now resolves manifest from stored version content before falling back to on-the-fly generation
- Manifest tab heading changed from "Generated Manifest" to "Manifest"
- Logic matches existing WorkflowManifestView pattern (lines 991-998) for consistency

## Task Commits

Each task was committed atomically:

1. **Task 1: Use stored version content for manifest in WorkflowDetailView** - `d451894` (fix)

## Files Created/Modified
- `core/views/ci_workflows.py` - Moved version queries before manifest resolution, added draft > authorized > generate fallback
- `core/templates/core/ci_workflows/workflow_detail.html` - Changed heading from "Generated Manifest" to "Manifest"

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Manifest tab now consistently shows the same content as WorkflowManifestView
- No blockers

## Self-Check: PASSED

- FOUND: core/views/ci_workflows.py
- FOUND: core/templates/core/ci_workflows/workflow_detail.html
- FOUND: commit d451894

---
*Quick Task: 41*
*Completed: 2026-02-17*
