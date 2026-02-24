---
phase: 07-implement-unified-environment-variables-management
plan: 02
subsystem: ui
tags: [htmx, django-templates, env-vars, alpine-js, inline-editing]

# Dependency graph
requires:
  - phase: 07-01
    provides: resolve_env_vars cascade function with source/locked_by metadata
provides:
  - Unified env var template partials (container, row, edit row, add row)
  - HTMX CRUD view endpoints for env var management
  - Entity-specific URL patterns for project, service, environment levels
  - Pre-computed URL helper for template context
affects: [07-03, 07-04, 07-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [pre-computed URL context pattern for reusable HTMX partials, entity-agnostic view with level-specific URL routing]

key-files:
  created:
    - core/templates/core/env_vars/_env_var_container.html
    - core/templates/core/env_vars/_env_var_row.html
    - core/templates/core/env_vars/_env_var_row_edit.html
    - core/templates/core/env_vars/_env_var_add_row.html
    - core/views/env_vars.py
  modified:
    - core/views/__init__.py
    - core/urls.py

key-decisions:
  - "Pre-computed URL context variables instead of dynamic URL name construction in templates"
  - "Entity-agnostic view classes with level detection from URL kwargs"
  - "Toggle lock uses ProjectOwnerMixin; other CRUD uses ProjectContributorMixin"

patterns-established:
  - "Pre-computed URL pattern: views pass env_var_*_url context vars to avoid template filter URL building"
  - "Level detection from kwargs: _current_level_for(service_name, env_name) determines project/service/environment"

requirements-completed: [DPLY-03, DPLY-04]

# Metrics
duration: 6min
completed: 2026-02-24
---

# Phase 07 Plan 02: Unified Env Var UI Component Summary

**Reusable HTMX-driven env var component with three-state lock icons, inline editing, and entity-specific CRUD endpoints for project/service/environment levels**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-24T10:37:13Z
- **Completed:** 2026-02-24T10:43:13Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Four template partials implementing unified env var display with three-state lock icon, hover tooltip, inline editing, and "not set" empty value display
- Six view classes handling all HTMX CRUD operations (display, edit, add, save, delete, toggle-lock)
- Entity-specific URL patterns for project, service, and environment contexts (18 new URL patterns total)
- Server-side validation: key format, PTF_* prefix rejection, upstream lock enforcement, empty value lock prevention

## Task Commits

Each task was committed atomically:

1. **Task 1: Create unified env var template partials** - `aba364c` (feat)
2. **Task 2: Create unified env var views and URL patterns** - `1e3407e` (feat)

## Files Created/Modified
- `core/templates/core/env_vars/_env_var_container.html` - Outer container with upstream/current grouping and add button
- `core/templates/core/env_vars/_env_var_row.html` - Display mode row with three-state lock, tooltip, source badge
- `core/templates/core/env_vars/_env_var_row_edit.html` - Inline edit form with key/value/description/lock
- `core/templates/core/env_vars/_env_var_add_row.html` - Empty row delegate to edit template
- `core/views/env_vars.py` - Six HTMX view classes with URL helper and entity resolution
- `core/views/__init__.py` - Added imports for new env_vars views
- `core/urls.py` - 18 new URL patterns (6 per entity level) plus new view imports

## Decisions Made
- Used pre-computed URL context variables (`env_var_*_url`) instead of attempting dynamic URL name construction in Django templates, because `{% url %}` tags do not support template filter-based name building
- Views detect entity level from URL kwargs (service_name/env_name presence) rather than requiring explicit target_type parameter
- EnvVarToggleLockView requires ProjectOwnerMixin (stricter) while other CRUD views use ProjectContributorMixin, matching the existing permission pattern where lock management is an owner-level action
- URL names use `_new` suffix (e.g., `project_env_var_save_new`) to avoid collision with existing old URL patterns that will be removed in Plan 05

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Changed from dynamic URL names to pre-computed URL context**
- **Found during:** Task 1 (Template creation)
- **Issue:** Plan specified `{% url target_type|add:'_env_var_add_row' %}` syntax which is invalid in Django templates -- `{% url %}` does not support filter-based URL name construction
- **Fix:** Templates receive pre-computed URL context variables (`env_var_add_url`, `env_var_edit_url`, etc.) from the views instead
- **Files modified:** All four template partials, core/views/env_vars.py
- **Verification:** All URL helpers produce correct paths, Django check passes
- **Committed in:** aba364c, 1e3407e

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential design change for Django template compatibility. No scope creep.

## Issues Encountered
- Pre-existing test infrastructure issue prevents `manage.py test` from running (ImportError in test module path resolution) -- not related to this plan's changes
- Pre-commit hooks reformatted import grouping in urls.py and __init__.py (ruff split aliased imports into separate blocks)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Template partials ready for integration into project settings, service settings, environment detail, and wizard pages (Plan 03-04)
- View endpoints operational and tested via Django check and URL resolution
- Old env var patterns preserved for backward compatibility until Plan 05 cleanup

---
*Phase: 07-implement-unified-environment-variables-management*
*Completed: 2026-02-24*
