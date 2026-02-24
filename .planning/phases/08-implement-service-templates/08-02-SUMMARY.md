---
phase: 08-implement-service-templates
plan: 02
subsystem: ui
tags: [django-views, django-forms, htmx, templates, crud, sidebar-navigation]

# Dependency graph
requires:
  - phase: 08-01
    provides: "Template, TemplateVersion models; read_pathfinder_manifest; git_utils helpers"
  - phase: 03.1-unified-sidebar
    provides: "Expandable sidebar navigation pattern with $persist"
provides:
  - "TemplateRegisterForm for template registration"
  - "Template CRUD views (list, detail, register, deregister, sync status)"
  - "Template list/detail/register HTML templates"
  - "Templates sidebar navigation section"
  - "templates URL namespace at /templates/"
affects: [08-03, 08-04, 08-05]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Template CRUD mirrors StepsRepository registration pattern", "Sync status HTMX partial mirrors _scan_status.html"]

key-files:
  created:
    - core/forms/templates.py
    - core/views/templates.py
    - core/templates/core/templates/list.html
    - core/templates/core/templates/detail.html
    - core/templates/core/templates/register.html
    - core/templates/core/templates/_sync_status.html
  modified:
    - core/views/__init__.py
    - core/urls.py
    - pathfinder/urls.py
    - core/templates/core/components/nav.html

key-decisions:
  - "Registration flow: shallow clone for manifest, full clone for tags, creates Template + TemplateVersion records"
  - "Deregister guard uses template.services.exists() to block deletion when services reference template"
  - "Sync Now button disabled placeholder for Plan 03 sync task implementation"
  - "Templates sidebar section placed between CI Workflows and Integrations"

patterns-established:
  - "Template registration: clone -> read manifest -> validate uniqueness -> create record -> list tags -> create versions"
  - "Template sync status partial with HTMX polling every 3s (same as StepsRepository scan status)"

requirements-completed: [BPRT-01, BPRT-03, BPRT-04]

# Metrics
duration: 5min
completed: 2026-02-24
---

# Phase 08 Plan 02: Template CRUD UI Summary

**Template list table, detail page with metadata/versions/sync sections, registration form with manifest validation, and sidebar navigation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-24T14:42:42Z
- **Completed:** 2026-02-24T14:47:17Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Template list page with table columns: name, description, runtimes badges, version count, sync status, last synced
- Template detail page with three sections: metadata (git URL, connection, runtimes, required vars), versions (sorted newest-first), sync status
- Registration form validates pathfinder.yaml manifest, checks name uniqueness, creates Template + TemplateVersion records
- Deregister with confirmation modal and service-reference guard
- Templates expandable section in sidebar navigation between CI Workflows and Integrations
- Sync status HTMX partial with auto-polling during syncing/pending states

## Task Commits

Each task was committed atomically:

1. **Task 1: Registration form, views, URLs, and sidebar navigation** - `707fcbe` (feat)
2. **Task 2: Template list, detail, and registration HTML templates** - `ba9a3df` (feat)

## Files Created/Modified
- `core/forms/templates.py` - TemplateRegisterForm with connection dropdown and git URL
- `core/views/templates.py` - TemplateListView, TemplateDetailView, TemplateRegisterView, TemplateDeregisterView, TemplateSyncStatusView
- `core/views/__init__.py` - Added template view imports and __all__ entries
- `core/urls.py` - templates_patterns with list, register, detail, deregister, sync_status URLs
- `pathfinder/urls.py` - Wired templates namespace at /templates/
- `core/templates/core/components/nav.html` - Added Templates expandable section with $persist state
- `core/templates/core/templates/list.html` - Table layout with sync status badges and empty state
- `core/templates/core/templates/detail.html` - Scrollable page with metadata, versions, sync sections
- `core/templates/core/templates/register.html` - Two-field form with error display
- `core/templates/core/templates/_sync_status.html` - HTMX polling partial for sync status badge

## Decisions Made
- Registration does shallow clone first for manifest validation, then full clone for tag listing (optimizes for the common failure case)
- Sync Now button is a disabled placeholder; actual sync task wiring deferred to Plan 03
- Deregister uses existing _confirm_modal.html component for consistency
- Templates sidebar section uses $persist(false).as('nav_templates') for toggle state

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-commit ruff check auto-reordered imports in core/urls.py on first commit attempt; re-staged and committed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Template CRUD UI complete, ready for sync task implementation (08-03)
- Registration flow creates Template + TemplateVersion records, ready for wizard integration (08-04/08-05)
- Sync status partial ready for HTMX wiring to sync trigger endpoint (08-03)

---
*Phase: 08-implement-service-templates*
*Completed: 2026-02-24*
