---
phase: 02-core-domain
plan: 01
subsystem: core-models
tags: [django, models, htmx, project, environment, membership]
dependency-graph:
  requires:
    - 01-01 (User/Group models)
  provides:
    - Project model with env_vars JSONField
    - Environment model with project FK
    - ProjectMembership model linking Groups to Projects
    - HTMX infrastructure for partial updates
  affects:
    - 02-02 (Settings encryption)
    - 02-03 (Blueprint models)
    - 03-01 (Project CRUD UI)
tech-stack:
  added:
    - django-htmx>=1.21.0
  patterns:
    - JSONField for env_vars list storage
    - Denormalized username fields for audit trail
    - CDN-based HTMX with CSRF auto-injection
key-files:
  created:
    - core/migrations/0002_project_environment_projectmembership.py
  modified:
    - core/models.py
    - core/admin.py
    - devssp/settings.py
    - theme/templates/base.html
    - requirements.txt
decisions:
  - id: env-vars-jsonfield
    choice: JSONField with list of dicts [{key, value, lock}]
    rationale: Flexible schema, supports locked values, easy to merge project/env vars
  - id: project-role-on-membership
    choice: project_role on ProjectMembership vs Group
    rationale: Same group can have different roles in different projects
  - id: htmx-via-cdn
    choice: CDN (unpkg) vs npm install
    rationale: Simpler setup, no build step needed, version pinned in template
metrics:
  duration: 2 min
  completed: 2026-01-22
---

# Phase 02 Plan 01: Core Domain Models Summary

**One-liner:** Project/Environment/ProjectMembership models with HTMX infrastructure for dynamic UI.

## What Was Built

### Project Model
- `id`: BigAutoField primary key
- `uuid`: UUIDField for external references (unique, indexed)
- `name`: CharField(20) DNS-compatible, unique
- `description`: TextField
- `env_vars`: JSONField storing list of `{key, value, lock}` objects
- `status`: active/inactive/archived
- `created_by`: denormalized username for audit
- `created_at`/`updated_at`: timestamps

### Environment Model
- `id`: BigAutoField primary key
- `uuid`: UUIDField for external references
- `project`: ForeignKey to Project (CASCADE)
- `name`: CharField(20) unique within project
- `env_vars`: JSONField for override/extend project vars
- `is_production`: boolean flag for production environments
- `is_default`: boolean flag for default environment selection
- `status`: active/inactive
- `order`: IntegerField for sorting (dev=10, staging=20, prod=30)

### ProjectMembership Model
- Links Groups to Projects with project-level roles
- `project_role`: owner/contributor/viewer
- `added_by`: denormalized username
- Unique constraint on (project, group)

### HTMX Infrastructure
- HTMX 2.0.4 loaded via unpkg CDN
- CSRF token meta tag for automatic injection
- `htmx:configRequest` event handler adds X-CSRFToken header
- django-htmx middleware enables `request.htmx` detection

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| env_vars storage | JSONField with list | Flexible schema, supports locked values |
| Project role location | On ProjectMembership | Same group can have different roles per project |
| HTMX loading | CDN (unpkg) | No build step, version pinned in template |

## Files Changed

| File | Change |
|------|--------|
| core/models.py | Added Project, Environment, ProjectMembership models |
| core/admin.py | Admin configuration for all three models |
| core/migrations/0002_*.py | Database schema migration |
| devssp/settings.py | Added django_htmx app and middleware |
| requirements.txt | Added django-htmx>=1.21.0 |
| theme/templates/base.html | HTMX script and CSRF configuration |

## Commit History

| Hash | Message |
|------|---------|
| 4a95a7a | feat(02-01): add Project, Environment, ProjectMembership models |
| a609190 | feat(02-01): install django-htmx and configure middleware |
| dce5bc9 | feat(02-01): add HTMX to base template and run migrations |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- [x] `python manage.py check` passes with no errors
- [x] Models import correctly from core.models
- [x] Django admin shows all three models
- [x] Base template includes htmx.org script tag
- [x] django-htmx middleware imports correctly
- [x] Migration 0002 applied successfully
- [x] Tables core_project, core_environment, core_project_membership exist

## Next Phase Readiness

**Ready for 02-02 (Settings encryption):**
- Project model exists with env_vars JSONField ready for encryption
- Environment model inherits/overrides project env_vars
- All models registered with auditlog for security tracking

**Ready for 03-01 (Project CRUD UI):**
- HTMX infrastructure in place for partial updates
- Models have all fields needed for list/detail/edit views
- Admin interface available for data seeding during development
