---
phase: quick
plan: 015
subsystem: blueprints
tags: [django, jsonfield, model-migration, multi-plugin]

# Dependency graph
requires:
  - phase: 04-blueprints
    provides: Blueprint model with deploy_plugin CharField
provides:
  - Blueprint.deploy_plugins JSONField storing list of plugin names
  - Any-match availability logic for multiple plugins
  - Comma-separated display in all blueprint templates
affects: [05-services, blueprint-selection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSONField for multi-value plugin requirements"
    - "Any-match availability logic (OR semantics)"

key-files:
  created:
    - core/migrations/0007_blueprint_deploy_plugins.py
  modified:
    - core/models.py
    - core/tasks.py
    - core/views/blueprints.py
    - core/templates/core/blueprints/detail.html
    - core/templates/core/blueprints/_preview.html
    - core/templates/core/blueprints/list.html

key-decisions:
  - "JSONField for deploy_plugins - supports variable-length lists"
  - "Any-match (OR) availability logic - blueprint available if ANY plugin has connection"
  - "Data migration preserves existing single values as single-element lists"

patterns-established:
  - "Multi-plugin blueprints: deploy_plugins is always a list, even if single plugin"

# Metrics
duration: 3min
completed: 2026-01-26
---

# Quick Task 015: Support Multiple Deploy Plugins in Blueprints Summary

**Blueprint.deploy_plugins JSONField with any-match availability logic and comma-separated UI display**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-26T14:10:07Z
- **Completed:** 2026-01-26T14:13:03Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Changed Blueprint.deploy_plugin CharField to deploy_plugins JSONField (list)
- Updated availability methods to use any-match (OR) logic for multiple plugins
- Data migration converts existing string values to single-element lists
- All templates display comma-separated plugin lists
- List page filter matches blueprints with any matching plugin

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Blueprint model and create migration** - `aa2b21e` (feat)
2. **Task 2: Update sync task and views** - `28b0bf0` (feat)
3. **Task 3: Update templates to display plugin lists** - `9c0fe11` (feat)

## Files Created/Modified
- `core/models.py` - Blueprint.deploy_plugins JSONField, updated availability methods
- `core/migrations/0007_blueprint_deploy_plugins.py` - Field migration with data conversion
- `core/tasks.py` - Sync stores full required_plugins list
- `core/views/blueprints.py` - Views pass lists to templates
- `core/templates/core/blueprints/detail.html` - Join deploy_plugins with comma
- `core/templates/core/blueprints/_preview.html` - Join deploy_plugins in preview
- `core/templates/core/blueprints/list.html` - Filter uses split().includes() for any-match

## Decisions Made
- JSONField stores list of strings (not CharFields or M2M) - simplest for variable-length plugin lists
- Any-match logic (OR) - blueprint available if ANY required plugin has active connection
- Empty list = no requirement (always available)

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Blueprint model fully supports multiple deploy plugins
- Ready for Phase 5 (Services) which will use blueprints for service creation

---
*Quick Task: 015*
*Completed: 2026-01-26*
