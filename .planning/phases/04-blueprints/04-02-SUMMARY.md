---
phase: 04-blueprints
plan: 02
subsystem: blueprints
tags: [django, htmx, alpine, gitpython, views, templates]

# Dependency graph
requires:
  - phase: 04-01
    provides: Blueprint and BlueprintVersion models, GitPython helpers, sync_blueprint task
provides:
  - Blueprint list view with table layout and filtering
  - Blueprint registration with live manifest preview
  - Blueprint detail view with version display
  - HTMX-powered preview and sync endpoints
affects: [05 (service wizard uses blueprint selection)]

# Tech tracking
tech-stack:
  added: []
  patterns: [HTMX live preview, Alpine.js form state management]

key-files:
  created:
    - core/views/blueprints.py
    - core/templates/core/blueprints/list.html
    - core/templates/core/blueprints/register.html
    - core/templates/core/blueprints/_preview.html
    - core/templates/core/blueprints/detail.html
    - core/templates/core/blueprints/_sync_status.html
  modified:
    - core/views/__init__.py
    - core/urls.py
    - core/views/placeholders.py

key-decisions:
  - "SCM connection dropdown for private repos, 'None' option for public"
  - "HTMX live preview validates manifest before registration"
  - "Registration blocked until valid manifest previewed"
  - "Redirect to detail page after registration (not list)"
  - "Prerelease toggle hidden by default on detail page"

patterns-established:
  - "HTMX preview pattern: blur/change triggers preview fetch, x-init updates Alpine state"
  - "Blueprint availability: is_available_globally checks for active deploy connections"
  - "Table-style list with Alpine filtering (search + dropdown filters)"

# Metrics
duration: 4min
completed: 2026-01-26
---

# Phase 04 Plan 02: Blueprint Views Summary

**Blueprint UI with table list, live HTMX manifest preview on registration, and version detail display**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-26T12:11:39Z
- **Completed:** 2026-01-26T12:15:48Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Blueprint list page with table layout, tag/plugin filtering, and availability indicators
- Registration form with SCM connection selection and live manifest preview via HTMX
- Blueprint detail page with metadata display, version list, and prerelease toggle
- HTMX-powered sync status updates and preview validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create blueprint views module with preview endpoint** - `35f2c9e` (feat)
2. **Task 2: Update URL patterns with preview endpoint** - `ed5da4d` (feat)
3. **Task 3: Create blueprint templates with live preview** - `0ae30b5` (feat)

## Files Created/Modified

- `core/views/blueprints.py` - BlueprintListView, BlueprintPreviewView, BlueprintRegisterView, BlueprintDetailView, BlueprintSyncView
- `core/views/__init__.py` - Updated imports to export new blueprint views
- `core/views/placeholders.py` - Removed placeholder BlueprintsListView
- `core/urls.py` - Added blueprint URL patterns (list, register, preview, detail, sync)
- `core/templates/core/blueprints/list.html` - Table-style blueprint list with filtering
- `core/templates/core/blueprints/register.html` - Registration form with HTMX preview
- `core/templates/core/blueprints/_preview.html` - HTMX partial for manifest preview
- `core/templates/core/blueprints/detail.html` - Blueprint detail with versions
- `core/templates/core/blueprints/_sync_status.html` - HTMX partial for sync status

## Decisions Made

- **SCM connection dropdown:** Shows "None (public repository)" plus active GitHub connections
- **HTMX preview pattern:** Preview triggers on blur (delay 500ms) and Enter key, updates Alpine state via x-init
- **Registration validation:** Manifest is re-fetched during POST to ensure preview was successful
- **Redirect after registration:** Goes to detail page per CONTEXT.md decision (not list)
- **Version display:** Prereleases hidden by default with toggle checkbox

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed as specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Blueprint views complete and functional
- Ready for testing with real Git repositories containing ssp-template.yaml
- Service wizard (Phase 5) can use blueprint selection from this UI
- Note: Requires GitPython to clone repos during preview/registration

---
*Phase: 04-blueprints*
*Completed: 2026-01-26*
