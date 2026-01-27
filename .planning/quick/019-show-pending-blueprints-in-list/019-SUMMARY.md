---
type: quick
task: 019
title: Show pending blueprints in list view
subsystem: ui
tags: [blueprints, htmx, templates]

key-files:
  modified:
    - core/views/blueprints.py
    - core/views/__init__.py
    - core/urls.py
    - core/templates/core/blueprints/list.html

key-decisions:
  - "Use pk (int) for delete URL since pending blueprints have empty names"
  - "Mark pending blueprints as unavailable (filtered by showUnavailable toggle)"
  - "Allow delete for both pending and error status blueprints"

duration: 3min
completed: 2026-01-27
---

# Quick Task 019: Show Pending Blueprints in List View

**Pending blueprints now visible and deletable in list view, enabling cleanup of stuck registrations**

## Performance

- **Duration:** 3 min
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Pending blueprints now visible in list (filtered by "Show unavailable" toggle)
- Pending entries display "Registering..." label with git URL for identification
- Operators can delete pending/error blueprints via delete button
- Visual distinction with yellow background for pending rows

## Task Commits

1. **Task 1: Update view and add delete endpoint** - `4d1793f` (feat)
2. **Task 2: Update list template for pending blueprints** - `679ec3f` (feat)

## Files Modified

- `core/views/blueprints.py` - Removed pending exclusion filter, added BlueprintDeleteView
- `core/views/__init__.py` - Exported BlueprintDeleteView
- `core/urls.py` - Added delete URL pattern using pk (int)
- `core/templates/core/blueprints/list.html` - Template updates for pending state handling

## Decisions Made

- Use pk (int) for delete URL since pending blueprints have empty names (cannot use dns:blueprint_name)
- Pending blueprints treated as "unavailable" so they only show when "Show unavailable" toggle is enabled
- Delete button shown for both pending and error status (operators can clean up failed syncs too)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added BlueprintDeleteView to __init__.py exports**
- **Found during:** Task 1 (Django check failed)
- **Issue:** BlueprintDeleteView not exported from core.views module
- **Fix:** Added to imports and __all__ in core/views/__init__.py
- **Files modified:** core/views/__init__.py
- **Verification:** python manage.py check passes
- **Committed in:** 4d1793f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Standard missing export - plan didn't explicitly mention __init__.py update

## Issues Encountered

None

## Next Steps

- Users can now clean up stuck blueprint registrations via the UI
- Normal blueprint workflow unchanged

---
*Quick Task: 019*
*Completed: 2026-01-27*
