---
phase: 05-services
plan: 03
subsystem: backend
tags: [git, jinja2, templating, background-tasks, scaffolding]

# Dependency graph
requires:
  - phase: 05-01
    provides: Service model with scaffold_status, scaffold_error, repo_is_new fields
  - phase: 04-01
    provides: git_utils module with clone_repo_shallow, build_authenticated_git_url, cleanup_repo
  - phase: 03-04
    provides: GitHub plugin with create_repository method
provides:
  - scaffold_repository background task for async repository scaffolding
  - scaffold_new_repository function for creating new repos from blueprints
  - scaffold_existing_repository function for feature branch + PR workflow
  - apply_template_to_directory function for Jinja2 variable substitution
  - create_pull_request method in GitHub plugin
affects: [05-02, 06-builds]

# Tech tracking
tech-stack:
  added: [Jinja2]
  patterns:
    - "Template variable substitution via Jinja2 {{ var }} syntax"
    - "Background task status tracking (pending/running/success/failed)"
    - "Cleanup of temporary directories in finally blocks"

key-files:
  created: []
  modified:
    - core/git_utils.py
    - core/tasks.py
    - plugins/github/plugin.py
    - requirements.txt
    - pathfinder/settings.py

key-decisions:
  - "Jinja2 for template substitution instead of string.Template"
  - "StrictUndefined mode to catch missing variables early"
  - "Feature branch naming: feature/{service-name}"

patterns-established:
  - "Background task status flow: pending -> running -> success/failed"
  - "Error capture in scaffold_error field for user visibility"
  - "Repository scaffolding cleanup with finally blocks"

# Metrics
duration: 4min
completed: 2026-01-26
---

# Phase 5 Plan 3: Repository Scaffolding Summary

**Background task and git utilities for scaffold_repository with Jinja2 template variable substitution**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-26T10:00:00Z
- **Completed:** 2026-01-26T10:04:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- scaffold_repository background task runs asynchronously to avoid HTTP timeout
- New repos: create via SCM plugin, push blueprint template to main branch
- Existing repos: create feature branch, apply template, open PR
- Template variables (service_name, project_name, service_handler) substituted via Jinja2

## Task Commits

Each task was committed atomically:

1. **Task 1: Add scaffolding functions to git_utils.py** - `26e6ded` (feat)
2. **Task 2: Create scaffold_repository background task** - `0c8a5d8` (feat)

## Files Created/Modified
- `core/git_utils.py` - Added get_template_variables, apply_template_to_directory, scaffold_new_repository, scaffold_existing_repository
- `core/tasks.py` - Replaced placeholder with full scaffold_repository implementation
- `plugins/github/plugin.py` - Added create_pull_request method for PR creation
- `requirements.txt` - Added Jinja2 dependency
- `pathfinder/settings.py` - Added repository_scaffolding queue to TASKS

## Decisions Made
- **Jinja2 for templating:** Chose Jinja2 with StrictUndefined mode to catch missing variables early rather than silent substitution failures
- **Feature branch naming:** feature/{service-name} convention for scaffolding into existing repos
- **Text file extensions:** Defined explicit list of text extensions for template substitution to avoid corrupting binary files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added create_pull_request method to GitHub plugin**
- **Found during:** Task 1 (scaffold_existing_repository implementation)
- **Issue:** scaffold_existing_repository calls plugin.create_pull_request() but GitHub plugin lacked this method
- **Fix:** Added create_pull_request method that parses repo URL and creates PR via PyGithub
- **Files modified:** plugins/github/plugin.py
- **Verification:** Method added and importable
- **Committed in:** 26e6ded (Task 1 commit)

**2. [Rule 3 - Blocking] Added repository_scaffolding queue to TASKS settings**
- **Found during:** Task 2 (scaffold_repository task import)
- **Issue:** Task used queue_name='repository_scaffolding' but this queue wasn't in TASKS settings
- **Fix:** Added 'repository_scaffolding' to QUEUES list in pathfinder/settings.py
- **Files modified:** pathfinder/settings.py
- **Verification:** Task import succeeds, Django check passes
- **Committed in:** 0c8a5d8 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking issues)
**Impact on plan:** Both auto-fixes necessary for task completion. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- scaffold_repository task ready for use by service creation wizard (05-02)
- Task can be enqueued with service_id and scm_connection_id
- Service scaffold_status will track progress (pending/running/success/failed)
- Error messages captured in scaffold_error field for user visibility

---
*Phase: 05-services*
*Completed: 2026-01-26*
