---
phase: quick
plan: 017
subsystem: ui
tags: [navigation, project-detail, htmx, django-templates]

# Dependency graph
requires:
  - phase: 02-core-domain
    provides: Project detail page structure, HTMX tabs, ProjectMembership model
provides:
  - Simplified 3-item project navigation (Services, Environments, Settings)
  - Members section integrated into Settings tab
  - Services as default project landing page
affects: [05-services]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Settings tab as consolidated project configuration hub

key-files:
  created: []
  modified:
    - core/templates/core/components/nav_project.html
    - core/templates/core/projects/_settings_tab.html
    - core/views/projects.py
  deleted:
    - core/templates/core/projects/_members_tab.html

key-decisions:
  - "Services is default landing page (no ?tab= parameter required)"
  - "Members section consolidated into Settings tab"
  - "Navigation reduced from 4 items to 3 items"

patterns-established:
  - "Project Settings tab contains all configuration including Members"

# Metrics
duration: 3min
completed: 2026-01-26
---

# Quick Task 017: Consolidate Project Pages and Update Nav Summary

**Simplified project navigation to 3 items (Services, Environments, Settings) with Members integrated into Settings tab**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-26
- **Completed:** 2026-01-26
- **Tasks:** 4
- **Files modified:** 3 (1 deleted)

## Accomplishments
- Reduced project navigation from 4 items to 3 items for cleaner UX
- Made Services the default landing page when navigating to a project
- Consolidated Members management into Settings tab
- Removed obsolete _members_tab.html template

## Task Commits

Each task was committed atomically:

1. **Task 1: Update project sidebar navigation** - `e9418d1` (feat)
2. **Task 2: Merge Members content into Settings tab** - `31fe4a0` (feat)
3. **Task 3: Update view logic for tabs and context** - `d82417b` (feat)
4. **Task 4: Delete obsolete members tab template** - `69ced86` (chore)

## Files Created/Modified
- `core/templates/core/components/nav_project.html` - Updated nav with 3 items: Services, Environments, Settings
- `core/templates/core/projects/_settings_tab.html` - Added Members section between SCM Connections and Danger Zone
- `core/views/projects.py` - Updated valid_tabs, moved members context to settings, fixed redirects
- `core/templates/core/projects/_members_tab.html` - DELETED (obsolete)

## Decisions Made
- Services is the default tab (no ?tab= parameter in URL)
- Members section placed between SCM Connections and Danger Zone in Settings
- Cog/gear icon used for Settings nav item

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Project navigation simplified and ready for Phase 5 (Services)
- Services tab will be populated in Phase 5
- No blockers or concerns

---
*Quick Task: 017-consolidate-project-pages-and-update-nav*
*Completed: 2026-01-26*
