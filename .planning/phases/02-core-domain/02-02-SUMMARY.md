---
phase: 02-core-domain
plan: 02
subsystem: navigation-projects
tags: [django, templates, htmx, navigation, projects]
dependency-graph:
  requires:
    - 02-01 (Project model)
  provides:
    - Restructured sidebar navigation
    - Project list page with environment counts
    - Create project modal via HTMX
    - navigation_context processor for project context
  affects:
    - 02-03 (Project detail views will use nav context)
    - All pages (navigation restructure)
tech-stack:
  added: []
  patterns:
    - HTMX modal pattern with HX-Redirect
    - Context processor for navigation state
    - Admin-only UI sections via is_admin
key-files:
  created:
    - core/templates/core/projects/list.html
    - core/templates/core/projects/create_modal.html
    - core/views/projects.py
  modified:
    - core/templates/core/components/nav.html
    - core/context_processors.py
    - core/forms.py
    - core/urls.py
    - core/views/__init__.py
    - pathfinder/urls.py
    - pathfinder/settings.py
decisions:
  - id: nav-settings-grouping
    choice: Settings section groups User Management under admin-only
    rationale: Per CONTEXT.md, cleaner organization for admin features
  - id: projects-link-all-users
    choice: Projects link visible to all authenticated users
    rationale: All users need project access, permissions handled at view level
  - id: login-redirect-projects
    choice: LOGIN_REDIRECT_URL to projects:list instead of users:list
    rationale: Projects is the primary workflow entry point
metrics:
  duration: 4 min
  completed: 2026-01-22
---

# Phase 02 Plan 02: Navigation and Project List Summary

**One-liner:** Sidebar restructured with Projects/Settings grouping; project list with HTMX create modal.

## What Was Built

### Navigation Restructure

Completely rewrote sidebar navigation per CONTEXT.md:

- **Pathfinder logo** links to projects:list (home)
- **Projects** link visible to all authenticated users
- **Blueprints** and **Integrations** (renamed from Connections)
- **Settings section** (admin-only) containing:
  - General (placeholder)
  - User Management subsection with Users and Groups
  - Audit & Logs
  - API & Tokens (placeholder)
  - Notifications (placeholder)
- **Documentation** link with external link icon
- **User profile** at bottom with logout

### Project List View

- `ProjectListView` with `Count('environments')` annotation
- Table view showing name, description, env count, last activity
- Empty state with "No projects yet" message and Create button
- `naturaltime` filter for last activity display

### Create Project Modal

- `ProjectCreateModalView` returns modal form
- `ProjectCreateForm` with DNS-compatible name validation:
  - Lowercase alphanumeric with hyphens
  - Max 20 characters
  - Unique name check
- HTMX form submission with inline error display
- `HX-Redirect` to projects:list on success

### Navigation Context Processor

- `navigation_context` provides `in_project_context` and `current_project`
- Prepared for Plan 03 project detail views

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Settings grouping | Admin-only section with User Management subsection | Cleaner organization per CONTEXT.md |
| Projects visibility | All authenticated users | Permissions handled at view/project level |
| Login redirect | projects:list | Projects is the primary workflow entry point |

## Files Changed

| File | Change |
|------|--------|
| core/templates/core/components/nav.html | Complete restructure with Settings section |
| core/context_processors.py | Added navigation_context processor |
| core/views/projects.py | Created with List/CreateModal/Create views |
| core/templates/core/projects/list.html | Project list with table and empty state |
| core/templates/core/projects/create_modal.html | HTMX modal form |
| core/forms.py | Added ProjectCreateForm |
| core/urls.py | Added projects_patterns |
| pathfinder/urls.py | Added projects namespace |
| pathfinder/settings.py | Updated LOGIN_REDIRECT_URL and context_processors |

## Commit History

| Hash | Message |
|------|---------|
| 1458005 | feat(02-02): restructure sidebar navigation |
| 8d03df1 | feat(02-02): add project list view and URL routing |
| 7a8acc6 | feat(02-02): implement create project modal with HTMX |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- [x] Navigation shows Projects, Blueprints, Integrations for all users
- [x] Admin sees Settings section with Users/Groups/Audit
- [x] Clicking Projects goes to /projects/ showing list
- [x] Create Project button opens modal overlay (admin only)
- [x] ProjectCreateForm validates DNS-compatible names
- [x] LOGIN_REDIRECT_URL updated to projects:list
- [x] Django check passes with no issues

## Next Phase Readiness

**Ready for 02-03 (Project detail views):**
- Project list functional with navigation to create
- navigation_context processor ready for project context detection
- URL patterns established for extending with detail views

**Note:** Project list rows link to `#` placeholder - Plan 03 will add `projects:detail` URL.
