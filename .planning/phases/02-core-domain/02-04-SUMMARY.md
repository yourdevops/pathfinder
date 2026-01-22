---
phase: 02
plan: 04
subsystem: core-domain
tags: [membership, environments, env-vars, htmx, permissions]
dependency-graph:
  requires: [02-03]
  provides: [project-membership-crud, environment-crud, env-var-management, env-var-inheritance]
  affects: [03-01, 05-01]
tech-stack:
  added: []
  patterns: [env-var-inheritance, lock-pattern, htmx-modals]
key-files:
  created:
    - core/templates/core/projects/env_var_modal.html
  modified:
    - core/views/projects.py
    - core/forms.py
    - core/urls.py
    - core/views/__init__.py
    - core/templates/core/projects/_settings_tab.html
    - core/templates/core/projects/_environments_tab.html
    - core/templates/core/projects/environment_detail.html
decisions:
  - title: "Env var lock prevents override"
    context: "How to handle locked env vars at environment level"
    choice: "Locked project vars cannot be overridden - error shown"
    rationale: "Clear governance, prevents accidental override of critical values"
  - title: "Amber styling for production"
    context: "How to visually distinguish production environments"
    choice: "bg-amber-500/20 text-amber-400 for production badge and row"
    rationale: "Consistent warning color, distinct from default/active states"
  - title: "Inheritance shown via badge"
    context: "How to display inherited vs local env vars"
    choice: "Blue 'Inherited' badge for project-level, green 'Environment' for local"
    rationale: "Clear visual indication of source, helps users understand override behavior"
metrics:
  duration: 6 min
  completed: 2026-01-22
---

# Phase 2 Plan 4: Project Governance and Environment Management Summary

**One-liner:** Complete project membership management and environment CRUD with environment variables supporting inheritance and lock capability.

## What Was Built

### Project Membership Management (Task 1)
Verified existing implementation from 02-03:
- AddMemberModalView handles both GET and POST for HTMX modal
- RemoveMemberView removes group from project membership
- Form excludes groups already assigned to project
- Members tab shows groups organized by role (owner/contributor/viewer)

### Environment CRUD (Task 2)
Enhanced environment management:
- **EnvironmentUpdateView**: Edit environment settings (description, order, is_production, is_default)
- **EnvironmentDeleteView**: Delete environment with default reassignment
- **EnvironmentForm**: Extended to include is_default field, name disabled on edit
- Environment detail page now shows edit form for contributors/owners

### Environment Variables Management (Task 3)
Full env var implementation with inheritance:
- **Project-level env vars**: Stored in Project.env_vars JSONField
  - Add via HTMX modal
  - Lock capability to prevent override
  - Delete via HTMX
- **Environment-level env vars**: Stored in Environment.env_vars JSONField
  - Inherit from project automatically
  - Cannot override locked project vars
  - "Inherited" badge for project-level vars
  - "Environment" badge for local vars
- **get_merged_env_vars()**: Merges project and environment vars with inheritance tracking

## Key Implementation Details

### Env Var Structure
```python
# JSONField format
[
    {"key": "DB_HOST", "value": "localhost", "lock": True},
    {"key": "APP_NAME", "value": "myapp", "lock": False}
]
```

### Inheritance Logic
1. Project vars are added first (all marked as inherited)
2. Environment vars are added/override project vars
3. If project var is locked, environment cannot override (error shown)

### URL Patterns Added
```python
# Environment CRUD
path('<uuid:project_uuid>/environments/<uuid:env_uuid>/update/', ...)
path('<uuid:project_uuid>/environments/<uuid:env_uuid>/delete/', ...)

# Project env vars
path('<uuid:project_uuid>/env-vars/', ProjectEnvVarModalView)
path('<uuid:project_uuid>/env-vars/save/', ProjectEnvVarSaveView)
path('<uuid:project_uuid>/env-vars/<str:key>/delete/', ProjectEnvVarDeleteView)

# Environment env vars
path('<uuid:project_uuid>/environments/<uuid:env_uuid>/env-vars/', EnvVarModalView)
path('<uuid:project_uuid>/environments/<uuid:env_uuid>/env-vars/save/', EnvVarSaveView)
path('<uuid:project_uuid>/environments/<uuid:env_uuid>/env-vars/<str:key>/delete/', EnvVarDeleteView)
```

## Verification Results

All success criteria met:
- [x] Admin can add groups to projects with owner/contributor/viewer roles
- [x] Project owner can remove groups from project
- [x] First environment becomes default automatically
- [x] is_production flag shown with distinct amber styling
- [x] Project-level env vars can be locked to prevent override
- [x] Environment inherits project env vars with "inherited" badge
- [x] Locked vars cannot be overridden at environment level
- [x] All CRUD operations work for membership, environments, and env vars

## Deviations from Plan

None - plan executed as written. Task 1 was verified as already working from 02-03.

## Files Changed

| File | Changes |
|------|---------|
| core/views/projects.py | Added EnvironmentUpdateView, EnvironmentDeleteView, ProjectEnvVarModalView, ProjectEnvVarSaveView, ProjectEnvVarDeleteView, EnvVarModalView, EnvVarSaveView, EnvVarDeleteView, get_merged_env_vars() |
| core/forms.py | Extended EnvironmentForm with is_default, disabled name on edit |
| core/urls.py | Added 9 new URL patterns for env and env var management |
| core/views/__init__.py | Exported new views |
| core/templates/core/projects/env_var_modal.html | New HTMX modal for env var add/edit |
| core/templates/core/projects/_settings_tab.html | Full env vars table with lock indicator |
| core/templates/core/projects/_environments_tab.html | Amber styling for production |
| core/templates/core/projects/environment_detail.html | Edit form and merged env vars display |

## Commit

- 1fc0a54: feat(02-04): complete project governance and env management

## Next Phase Readiness

Phase 2 is now complete. All core domain features implemented:
- User and group management
- Project CRUD with HTMX tabs
- Environment management
- Project membership with roles
- Environment variables with inheritance

Ready for Phase 3 (External Integrations) which will add:
- Container runtime connections
- Image registry connections
- Secret storage connections
