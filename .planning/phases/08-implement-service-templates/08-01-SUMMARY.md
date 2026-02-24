---
phase: 08-implement-service-templates
plan: 01
subsystem: database
tags: [django-models, migrations, manifest-parser, service-templates]

# Dependency graph
requires:
  - phase: 04-blueprints
    provides: "git_utils.py with clone, parse_version_tag, build_authenticated_git_url"
  - phase: 06.11-templates-documentation-folder
    provides: "Template design docs (design.md, template-registration.md)"
provides:
  - "Template, TemplateVersion, ProjectTemplateConfig models"
  - "Service.template FK and Service.template_version text field"
  - "read_pathfinder_manifest() function for pathfinder.yaml validation"
  - "get_available_templates_for_project() helper"
affects: [08-02, 08-03, 08-04, 08-05]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Template model mirrors StepsRepository pattern", "ProjectTemplateConfig parallels ProjectCIConfig"]

key-files:
  created:
    - core/migrations/0033_service_templates.py
  modified:
    - core/models.py
    - core/git_utils.py

key-decisions:
  - "read_pathfinder_manifest replaces read_manifest_from_repo entirely (old ssp-template.yaml/pathfinder-template.yaml removed)"
  - "Template.name sourced from manifest, validated as DNS label"
  - "TemplateVersion uses sort_key for semver ordering (same pattern as parse_version_tag)"
  - "Service.template_version is CharField not FK for historical reference stability"

patterns-established:
  - "Template sync pattern: pending > syncing > synced > error (mirrors StepsRepository scan_status)"
  - "pathfinder.yaml manifest: kind: ServiceTemplate with DNS-compatible name"

requirements-completed: [BPRT-01, BPRT-02]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 08 Plan 01: Data Models and Manifest Parser Summary

**Template, TemplateVersion, ProjectTemplateConfig models with pathfinder.yaml manifest validation and Service template FK**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T14:37:21Z
- **Completed:** 2026-02-24T14:39:50Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Template model with sync_status lifecycle, connection FK, runtimes, required_vars
- TemplateVersion model with semver sort_key ordering and availability tracking
- ProjectTemplateConfig with default_template and allowed_templates M2M (parallels ProjectCIConfig)
- Service model gains template FK (SET_NULL) and template_version text field
- read_pathfinder_manifest validates kind: ServiceTemplate and DNS-compatible name
- get_available_templates_for_project helper with project-scoped filtering

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Template, TemplateVersion, ProjectTemplateConfig models and Service FK** - `90d3337` (feat)
2. **Task 2: Manifest parser and migration** - `f027963` (feat)

## Files Created/Modified
- `core/models.py` - Template, TemplateVersion, ProjectTemplateConfig models; Service template FK; auditlog registrations; get_available_templates_for_project helper
- `core/git_utils.py` - read_pathfinder_manifest replaces read_manifest_from_repo; updated apply_template_to_directory exclude list
- `core/migrations/0033_service_templates.py` - Migration for all new models and Service field additions

## Decisions Made
- Replaced read_manifest_from_repo entirely with read_pathfinder_manifest (old manifest filenames removed)
- Template.name validated as DNS label, sourced from pathfinder.yaml manifest
- Service.template_version is CharField (not FK) for historical stability
- apply_template_to_directory exclude list updated from old filenames to pathfinder.yaml

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-commit hooks (ruff check/format) auto-fixed unused import in git_utils.py on first commit attempt; re-staged and committed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Models and migration applied, ready for template registration UI (08-02)
- Manifest parser ready for sync operations (08-03)
- Service template FK ready for template selection in service creation wizard (08-04/08-05)

---
*Phase: 08-implement-service-templates*
*Completed: 2026-02-24*
