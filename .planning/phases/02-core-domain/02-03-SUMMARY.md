---
phase: 02-core-domain
plan: 03
subsystem: project-detail
tags: [django, htmx, permissions, navigation, tabs]
dependency-graph:
  requires:
    - 02-01 (Project, Environment, ProjectMembership models)
    - 02-02 (Navigation context, project list view)
  provides:
    - Project detail page with HTMX tabs
    - Project permission helpers and mixins
    - Context-replacing project sidebar
    - Environment CRUD views
    - Project membership management
  affects:
    - 02-04 (Will use permission mixins)
    - All project-scoped views (navigation context)
tech-stack:
  added: []
  patterns:
    - HTMX tab navigation with hx-push-url
    - Context-replacing sidebar (AWS Console pattern)
    - Permission mixins with role hierarchy
    - Vary header for HTMX responses
key-files:
  created:
    - core/permissions.py
    - core/templates/core/projects/detail.html
    - core/templates/core/projects/_services_tab.html
    - core/templates/core/projects/_environments_tab.html
    - core/templates/core/projects/_members_tab.html
    - core/templates/core/projects/_settings_tab.html
    - core/templates/core/projects/add_member_modal.html
    - core/templates/core/projects/environment_create.html
    - core/templates/core/projects/environment_detail.html
    - core/templates/core/components/nav_project.html
  modified:
    - core/views/projects.py
    - core/forms.py
    - core/urls.py
    - core/views/__init__.py
    - core/context_processors.py
    - theme/templates/base.html
decisions:
  - id: permission-role-hierarchy
    choice: Role hierarchy viewer < contributor < owner with system role override
    rationale: Admin/Operator system roles get owner-level access to all projects
  - id: htmx-tab-pattern
    choice: Partial template swap with hx-push-url for browser history
    rationale: Seamless UX without full page reload, preserves back/forward navigation
  - id: context-replacing-sidebar
    choice: AWS Console pattern - project nav replaces main nav with back button
    rationale: Clearer context, more space for project-specific navigation
metrics:
  duration: 8 min
  completed: 2026-01-22
---

# Phase 02 Plan 03: Project Detail with HTMX Tabs Summary

**One-liner:** Project detail page with HTMX tab navigation, permission mixins, and context-replacing sidebar.

## What Was Built

### Project Permission System

Created `core/permissions.py` with:

- `has_system_role()` - Check if user has admin/operator/auditor role via groups
- `get_user_project_role()` - Get user's highest role on a project (owner/contributor/viewer)
- `can_access_project()` - Check if user has at least required role
- `ProjectPermissionMixin` - Base mixin that sets project and role in view
- `ProjectViewerMixin`, `ProjectContributorMixin`, `ProjectOwnerMixin` - Role-specific mixins

Role hierarchy enforced: `viewer < contributor < owner`
System override: Admin and Operator system roles get `owner` access to all projects.

### Project Detail View with HTMX Tabs

`ProjectDetailView` features:
- Four tabs: Services, Environments, Members, Settings
- HTMX partial swap without full page reload
- `hx-push-url` updates browser URL bar
- `Vary: HX-Request` header for proper caching
- Settings tab only visible to project owners

Tab templates:
- `_services_tab.html` - Empty state placeholder (Phase 5)
- `_environments_tab.html` - Environment list with badges, add button
- `_members_tab.html` - Groups organized by role section
- `_settings_tab.html` - Project info form, env vars placeholder, danger zone

### Context-Replacing Project Sidebar

Updated `navigation_context` processor to:
- Detect `project_uuid` in URL via resolver_match
- Provide `in_project_context`, `current_project`, `current_project_role`

Created `nav_project.html`:
- Back to Projects link with arrow
- Project name and description
- Navigation links: Services, Environments, Members, Settings
- Settings only visible to owners
- User section at bottom (same as main nav)

Updated `base.html` to conditionally include project nav.

### Supporting Views and Forms

Views added:
- `ProjectUpdateView` - Update project settings
- `ProjectArchiveView` - Archive project (soft delete)
- `EnvironmentCreateView` - Create environment with first-as-default logic
- `EnvironmentDetailView` - View environment details
- `AddMemberModalView` - HTMX modal for adding groups
- `RemoveMemberView` - Remove group from project

Forms added:
- `ProjectUpdateForm` - Edit description and status
- `EnvironmentForm` - Create/edit environment
- `AddProjectMemberForm` - Add group with role selection

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Permission hierarchy | viewer < contributor < owner | Clear role escalation path |
| System role override | Admin/Operator get owner access | Platform teams need full access |
| Tab navigation | HTMX partial swap with hx-push-url | No page reload, browser history works |
| Sidebar pattern | Context-replacing (AWS style) | Clearer context, dedicated project nav |

## Files Changed

| File | Change |
|------|--------|
| core/permissions.py | Created with permission helpers and mixins |
| core/views/projects.py | Added 7 new views for project/env/member management |
| core/forms.py | Added ProjectUpdateForm, EnvironmentForm, AddProjectMemberForm |
| core/urls.py | Added 8 new URL patterns for project operations |
| core/views/__init__.py | Export new views |
| core/context_processors.py | Enhanced navigation_context with project detection |
| theme/templates/base.html | Conditional project nav include |
| core/templates/core/projects/list.html | Link to detail view |
| core/templates/core/projects/detail.html | Main detail with tab nav |
| core/templates/core/projects/_*.html | Tab partials |
| core/templates/core/components/nav_project.html | Project sidebar |

## Commit History

| Hash | Message |
|------|---------|
| 060ee39 | feat(02-03): create project permission helpers and mixins |
| e0ec9c2 | feat(02-03): implement project detail view with HTMX tabs |
| 0bc129a | feat(02-03): implement context-replacing project sidebar |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- [x] Project detail shows name, description, and four tabs
- [x] Tabs load content dynamically via HTMX
- [x] URL updates when switching tabs (browser back/forward works)
- [x] Context-replacing sidebar shows when viewing project
- [x] Back button returns to main navigation and project list
- [x] Permission helpers correctly determine user's project role
- [x] Settings tab restricted to owners/admins
- [x] Django check passes with no issues
- [x] All templates load correctly

## Next Phase Readiness

**Ready for 02-04 (Remaining views and polish):**
- Permission system fully functional
- Project detail with tabs complete
- Context-replacing navigation working
- URL patterns established for all project operations
