---
phase: 04-blueprints
plan: 01
subsystem: blueprints
tags: [git, gitpython, semver, yaml, models, tasks]

# Dependency graph
requires:
  - phase: 03-integrations
    provides: IntegrationConnection model for SCM authentication
provides:
  - Blueprint and BlueprintVersion models for template registration
  - GitPython helper functions for SCM-agnostic operations
  - sync_blueprint task for fetching manifest and tags
affects: [04-02 (blueprint views), 05 (service wizard)]

# Tech tracking
tech-stack:
  added: [GitPython, semver, PyYAML]
  patterns: [SCM-agnostic Git operations, semver parsing, background sync tasks]

key-files:
  created:
    - core/git_utils.py
    - core/migrations/0006_blueprint_blueprintversion.py
  modified:
    - core/models.py
    - core/tasks.py
    - requirements.txt
    - pathfinder/settings.py

key-decisions:
  - "GitPython for SCM abstraction (not GitHub API) - supports any Git server"
  - "Sort key format: {major:05d}.{minor:05d}.{patch:05d}.{prerelease or 'zzzz'}"
  - "Manifest files: ssp-template.yaml (primary), pathfinder-template.yaml (fallback)"

patterns-established:
  - "Git URL parsing: Support HTTPS and SSH formats from any host"
  - "Version sorting: Pre-releases sort before releases via sort_key"
  - "Shallow clone pattern: depth=1, single_branch for blueprint sync"

# Metrics
duration: 3min
completed: 2026-01-26
---

# Phase 04 Plan 01: Blueprint Models Summary

**Blueprint and BlueprintVersion models with GitPython-based sync task for SCM-agnostic template registration**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-26T12:04:39Z
- **Completed:** 2026-01-26T12:08:05Z
- **Tasks:** 4
- **Files modified:** 6

## Accomplishments

- Blueprint model with git_url, sync_status, manifest storage, and availability checking
- BlueprintVersion model with semver parsing (major/minor/patch/prerelease) and sort_key for ordering
- GitPython helper functions for any Git-compatible SCM (GitHub, GitLab, Bitbucket, self-hosted)
- sync_blueprint background task that fetches manifest and version tags from repositories

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Blueprint and BlueprintVersion models** - `f876c1b` (feat)
2. **Task 2: Create GitPython helper functions** - `d2b1eb1` (feat)
3. **Task 3: Add sync_blueprint task** - `a47c40a` (feat)
4. **Task 4: Create and run migration** - `17d7298` (chore)

## Files Created/Modified

- `core/models.py` - Blueprint and BlueprintVersion models with auditlog registration
- `core/git_utils.py` - GitPython helper functions (parse_git_url, build_authenticated_git_url, clone_repo_shallow, etc.)
- `core/tasks.py` - sync_blueprint task for background repository sync
- `requirements.txt` - Added GitPython, semver, PyYAML dependencies
- `pathfinder/settings.py` - Added QUEUES configuration for django_tasks
- `core/migrations/0006_blueprint_blueprintversion.py` - Database schema migration

## Decisions Made

- **GitPython for SCM abstraction:** Uses Git protocol directly instead of GitHub API, enabling support for any Git-compatible server (GitHub, GitLab, Bitbucket, self-hosted)
- **Manifest file names:** Primary: ssp-template.yaml, fallback: pathfinder-template.yaml
- **Sort key format:** `{major:05d}.{minor:05d}.{patch:05d}.{prerelease or 'zzzz'}` ensures releases sort after pre-releases
- **Authentication pattern:** build_authenticated_git_url embeds credentials in URL for private repo access

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added QUEUES configuration for django_tasks**
- **Found during:** Task 3 (sync_blueprint task)
- **Issue:** Task decorator with queue_name='blueprint_sync' failed because queue not configured in TASKS settings
- **Fix:** Added QUEUES configuration with ["default", "health_checks", "blueprint_sync"]
- **Files modified:** pathfinder/settings.py
- **Verification:** Task import succeeds, no InvalidTaskError
- **Committed in:** a47c40a (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for task queue functionality. No scope creep.

## Issues Encountered

None - plan executed as specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Blueprint models ready for views and UI development (Plan 02)
- sync_blueprint task can be triggered from registration views
- Version parsing and sorting verified with tests
- Blocking issue: django_tasks QUEUES config was missing (fixed)

---
*Phase: 04-blueprints*
*Completed: 2026-01-26*
