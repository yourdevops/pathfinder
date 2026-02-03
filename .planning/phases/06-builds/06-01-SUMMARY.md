---
phase: 06-builds
plan: 01
subsystem: builds
tags: [webhooks, github-actions, hmac, background-tasks, state-machine]

# Dependency graph
requires:
  - phase: 05-services
    provides: Service model with ci_workflow field
  - phase: 05.1-ci-workflows-builder
    provides: CIWorkflow model with workflow naming convention
provides:
  - Build model for tracking CI/CD builds
  - Webhook endpoint for GitHub Actions notifications
  - Background task for polling GitHub API
  - Service activation logic on first successful build
affects: [06-02-builds-ui, 07-deploys]

# Tech tracking
tech-stack:
  added: []
  patterns: [webhook-hmac-verification, background-polling, state-machine]

key-files:
  created:
    - core/views/webhooks.py
    - core/migrations/0017_build.py
  modified:
    - core/models.py
    - core/tasks.py
    - core/urls.py
    - pathfinder/urls.py
    - pathfinder/settings.py
    - plugins/github/plugin.py

key-decisions:
  - "Always return 200 OK from webhook (security - prevents enumeration)"
  - "Webhook secret stored in connection config, not separate field"
  - "Service identification by workflow name (CI - {name}) or repo URL fallback"
  - "artifact_ref stored for Phase 7 deployment integration"
  - "commit_message stores first line only for display brevity"

patterns-established:
  - "Webhook HMAC verification pattern with timing-safe comparison"
  - "Background task polling pattern for external API data"
  - "Service activation on first successful build"

# Metrics
duration: 3min
completed: 2026-02-03
---

# Phase 06 Plan 01: Webhook Infrastructure Summary

**GitHub Actions webhook endpoint with HMAC authentication, Build model with state machine, and background polling task for build details**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-03T13:41:53Z
- **Completed:** 2026-02-03T13:45:08Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Build model with all fields for tracking GitHub Actions workflow runs
- Webhook endpoint at `/webhooks/build/` with HMAC-SHA256 signature verification
- Background task to poll GitHub API for workflow run and commit details
- Service activation logic that transitions services from draft to active on first success

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Build model with state machine** - `adc69f2` (feat)
2. **Task 2: Create webhook endpoint with HMAC verification** - `b8f2d09` (feat)
3. **Task 3: Add poll_build_details task and GitHub API methods** - `128a2c9` (feat)

## Files Created/Modified

- `core/models.py` - Added Build model with status state machine and map_github_status method
- `core/views/webhooks.py` - New file with webhook endpoint and HMAC verification
- `core/tasks.py` - Added poll_build_details task and activate_service_on_first_success helper
- `core/urls.py` - Added webhooks_patterns for webhook URLs
- `pathfinder/urls.py` - Registered webhooks namespace
- `pathfinder/settings.py` - Added build_updates queue to TASKS
- `plugins/github/plugin.py` - Added get_workflow_run and get_commit methods
- `core/migrations/0017_build.py` - Migration for Build model

## Decisions Made

- **Webhook returns 200 OK always:** Security best practice - prevents attackers from enumerating valid vs invalid payloads
- **Service identification strategy:** Primary lookup by workflow name (matching "CI - {workflow_name}" convention), fallback to repo_url matching
- **artifact_ref extraction:** Extracts artifacts_url from webhook payload for Phase 7 deployment integration
- **commit_message handling:** Stores only first line of commit message for cleaner display in UI
- **Duration calculation:** Computed as seconds between created_at and updated_at when run completes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-commit hook caught ruff style violation (SIM116) in map_github_status - refactored consecutive if statements to dictionary lookup
- Type error with dict.get() when conclusion could be None - added explicit None check before dictionary lookup

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Build model ready for Phase 06-02 (Build UI)
- Webhook endpoint ready for GitHub configuration
- Service activation logic ready for production use
- artifact_ref field ready for Phase 7 deployment integration

---
*Phase: 06-builds*
*Completed: 2026-02-03*
