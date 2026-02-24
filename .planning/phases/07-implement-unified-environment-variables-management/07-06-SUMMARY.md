---
phase: 07-implement-unified-environment-variables-management
plan: 06
subsystem: ui
tags: [env-vars, sorting, cascade, templates]

requires:
  - phase: 07-01
    provides: resolve_env_vars() cascade logic
  - phase: 07-02
    provides: env var HTMX partials and views
provides:
  - Source-priority sort in resolve_env_vars() (system > project > service > environment)
  - Badge-free env var row template (source info in tooltip only)
affects: [07-07]

tech-stack:
  added: []
  patterns: [source-priority tuple sort for cascade display ordering]

key-files:
  created: []
  modified:
    - core/utils.py
    - core/tests/test_env_vars.py
    - core/templates/core/env_vars/_env_var_row.html
    - core/templates/core/services/wizard/step_configuration.html

key-decisions:
  - "Source priority sort: system=0, project=1, service=2, environment=3 as tuple key"
  - "Source badges removed entirely; tooltip on key hover is the only source indicator"

patterns-established:
  - "Tuple sort with source_priority dict for cascade ordering"

requirements-completed: [DPLY-04]

duration: 1min
completed: 2026-02-24
---

# Phase 07 Plan 06: Fix Sort Order and Source Badges Summary

**Source-priority sort (System > Project > Service > Environment) and removal of visible source badges from env var rows**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-24T11:55:54Z
- **Completed:** 2026-02-24T11:57:10Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- resolve_env_vars() now sorts by (source_priority, key) ensuring system vars always appear first
- Removed colored source badges from _env_var_row.html and wizard step_configuration.html
- Added two new tests verifying source-priority sort order

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix resolve_env_vars sort order and update tests** - `545c78b` (fix)
2. **Task 2: Remove visible source badges from env var rows** - `a27a64e` (fix)

## Files Created/Modified
- `core/utils.py` - Changed sort key from `key` to `(source_priority, key)` tuple
- `core/tests/test_env_vars.py` - Replaced alphabetical sort test with source-priority tests, added system-vars-first test
- `core/templates/core/env_vars/_env_var_row.html` - Removed 8-line source badge block
- `core/templates/core/services/wizard/step_configuration.html` - Removed System badge from PTF_* vars section

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Sort order and badge issues from human verification are resolved
- Remaining issues (wizard save button, bulk save architecture) to be addressed in plan 07-07

---
*Phase: 07-implement-unified-environment-variables-management*
*Completed: 2026-02-24*
