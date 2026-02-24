---
phase: 07-implement-unified-environment-variables-management
plan: 05
subsystem: ui, env-vars
tags: [env-vars, htmx, cleanup, modal-removal]

# Dependency graph
requires:
  - phase: 07-03
    provides: unified stacked-row UI component
  - phase: 07-04
    provides: service settings and wizard integration
provides:
  - removal of all deprecated modal-based env var code
  - clean codebase with only unified env var views/templates/URLs
affects: [env-vars-redesign, deployment-gate]

# Tech tracking
tech-stack:
  added: []
  patterns: [unified env var imports without aliases]

key-files:
  created: []
  modified:
    - core/views/projects.py
    - core/urls.py
    - core/views/__init__.py
    - core/models.py

key-decisions:
  - "Simplified env_vars import aliases after removing name conflicts with old views"

patterns-established:
  - "env_vars views imported directly (no aliases) now that old modal views are removed"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-02-24
---

# Phase 07 Plan 05: Cleanup and Verification Summary

**Removed all deprecated modal-based env var code; human verification FAILED with 4 issues requiring redesign**

## Performance

- **Duration:** 5 min (Task 1 only; checkpoint stopped execution)
- **Started:** 2026-02-24T10:57:38Z
- **Completed:** 2026-02-24T11:02:00Z
- **Tasks:** 1/2 (Task 2 checkpoint FAILED)
- **Files modified:** 5 (4 modified, 1 deleted)

## Accomplishments
- Removed 6 deprecated modal-based view classes from core/views/projects.py
- Deleted env_var_modal.html template
- Removed 7 old URL patterns from core/urls.py
- Removed Service.get_merged_env_vars() deprecated method
- Simplified import aliases (no more name conflicts between old and new views)
- Django check passes, all 12 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove deprecated modal-based env var code and old URL patterns** - `42f11d5` (feat)
2. **Task 2: Human verification of unified env var system** - FAILED (no commit)

## Files Created/Modified
- `core/views/projects.py` - Removed ProjectEnvVarModalView, ProjectEnvVarSaveView, ProjectEnvVarDeleteView, EnvVarModalView, EnvVarSaveView, EnvVarDeleteView
- `core/templates/core/projects/env_var_modal.html` - DELETED
- `core/urls.py` - Removed 7 old modal URL patterns, simplified env_vars imports
- `core/views/__init__.py` - Removed old view imports/exports, simplified aliases
- `core/models.py` - Removed Service.get_merged_env_vars() deprecated method

## Decisions Made
- Simplified env_vars import aliases after removing name conflicts with old views

## Deviations from Plan

None - Task 1 executed exactly as written.

## Human Verification Results: FAILED

Task 2 checkpoint was presented for human verification. The user reviewed all 5 test scenarios and reported 4 issues:

### Issue 1: Sort order wrong
Variables are not sorted consistently in System > Project > Service > Environment order across all contexts.

### Issue 2: Source badges unwanted
Color-coded "source" labels (badges) are visible in the UI. User wants source information available only on hover/tooltip, not as visible badges.

### Issue 3: Wizard save button broken
Cannot save an added variable in the wizard -- the save/check button does not appear when adding a new variable.

### Issue 4: Bulk save required (ARCHITECTURAL)
The current HTMX per-row immediate save pattern is architecturally wrong. User requires:
- ALL edits happen client-side in the browser session (no server round-trips per row)
- Changes submitted in bulk with the page-level "Save" button
- Env var edits must be part of the broader page save (project settings Save, environment settings Save, service settings Save, wizard submit)
- This is a significant architectural change from the current per-row HTMX save approach

## Issues Encountered
- `uv run python manage.py test` (without label) has a pre-existing import path issue unrelated to this plan; `uv run python manage.py test core.tests` passes all 12 tests

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Old modal code is fully cleaned up (Task 1 complete)
- 4 issues from human verification need to be addressed in a follow-up plan
- Issue 4 (bulk save) is architectural and will require significant rework of the env var component

## Self-Check: FAILED

Task 1 completed successfully. Task 2 (human verification) FAILED with 4 issues.

Commit verification:
- 42f11d5: VERIFIED (Task 1)

Gaps requiring follow-up:
1. Sort order: System > Project > Service > Environment
2. Remove visible source badges, keep info in tooltips only
3. Fix wizard save button for new variables
4. ARCHITECTURAL: Replace per-row HTMX save with client-side bulk save pattern

---
*Phase: 07-implement-unified-environment-variables-management*
*Completed: 2026-02-24 (partial - Task 1 only)*
