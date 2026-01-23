---
phase: 010-fix-integrations-page-permissions-and-ac
plan: 010
subsystem: auth
tags: [permissions, access-control, django-mixins, css]

# Dependency graph
requires:
  - phase: 03-integrations
    provides: OperatorRequiredMixin, connection views
provides:
  - Tiered permission model for connections (all users view list, admin/operator/auditor view details, admin/operator manage)
  - IntegrationsReadMixin for read-only integrations access
  - Error message styling with message-error CSS class
affects: [04-blueprints, any future integrations features]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Tiered access control (list/view/manage permissions)
    - Permission context variables for template conditionals

key-files:
  created: []
  modified:
    - core/permissions.py
    - core/views/connections.py
    - core/templates/core/connections/list.html
    - core/templates/core/connections/_connection_card.html
    - theme/static_src/src/styles.css
    - theme/templates/base.html

key-decisions:
  - "OperatorRequiredMixin allows both admin and operator roles (admin beats operator)"
  - "IntegrationsReadMixin for admin/operator/auditor read-only access"
  - "can_manage and can_view_details context variables for template conditionals"

patterns-established:
  - "Tiered permission model: list (all authenticated) / view details (privileged) / manage (admin/operator)"

# Metrics
duration: 3min
completed: 2026-01-23
---

# Quick Task 010: Fix Integrations Page Permissions and Access Control

**Tiered permission model for connections with proper admin role fallback and red error message styling**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-23T12:00:00Z
- **Completed:** 2026-01-23T12:03:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Fixed OperatorRequiredMixin to allow both admin and operator roles
- Implemented tiered access control: all authenticated users see list, admin/operator/auditor see details, admin/operator manage
- Added IntegrationsReadMixin for read-only integrations access
- Added message-error CSS class for red background/border error display
- Templates conditionally show/hide add buttons and action links based on user permissions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add error message styling and fix OperatorRequiredMixin** - `3f62c64` (fix)
2. **Task 2: Update connection views with tiered permission model** - `427a175` (feat)
3. **Task 3: Build CSS and update base template** - `342e6c6` (style)

## Files Created/Modified
- `core/permissions.py` - Fixed OperatorRequiredMixin to include admin role, added IntegrationsReadMixin
- `core/views/connections.py` - Updated imports, removed OperatorRequiredMixin from list view, added permission context variables
- `core/templates/core/connections/list.html` - Wrapped add buttons with can_manage conditional
- `core/templates/core/connections/_connection_card.html` - Conditional name links and action buttons based on permissions
- `theme/static_src/src/styles.css` - Added message-error CSS class
- `theme/templates/base.html` - Updated message rendering to use message-error class for errors

## Decisions Made
- OperatorRequiredMixin now checks for admin OR operator role (matches existing pattern in get_user_project_role)
- IntegrationsReadMixin allows admin, operator, or auditor for read-only access
- can_manage and can_view_details context variables computed in view for template use

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- CSS dist folder is gitignored, so built CSS not committed (expected behavior)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Connection pages now have proper tiered access control
- Error messages display with visible red styling
- Ready for Phase 4 (Blueprints) development

---
*Quick Task: 010-fix-integrations-page-permissions-and-ac*
*Completed: 2026-01-23*
