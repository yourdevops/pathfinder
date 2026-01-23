---
phase: 03-integrations
plan: 05
subsystem: health-checks
tags: [background-tasks, django-tasks, health-checks, scheduling]

# Dependency graph
requires:
  - phase: 03-01
    provides: IntegrationConnection model with health fields
  - phase: 03-04
    provides: Connections UI with test button
provides:
  - Background health check tasks
  - Spread scheduling to avoid load spikes
  - Manual health check trigger
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [django-tasks, spread-scheduling, background-worker]

key-files:
  created:
    - core/tasks.py
  modified:
    - core/admin.py
    - devssp/settings.py

key-decisions:
  - "Spread scheduling divides interval by connection count"
  - "Synchronous health check for manual Test Connection"
  - "Background worker runs via 'python manage.py db_worker'"

patterns-established:
  - "@task decorator for background tasks"
  - "Spread scheduling pattern for periodic jobs"
  - "IntegrationConnectionAdmin with read-only health fields"

# Metrics
duration: 4min
completed: 2026-01-23
---

# Phase 3 Plan 5: Background Health Checks Summary

**Background health check system with spread scheduling and manual trigger**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-23T14:00:00Z
- **Completed:** 2026-01-23T14:04:00Z
- **Tasks:** 3
- **Files created:** 1
- **Files modified:** 2

## Accomplishments
- Created check_connection_health task for individual connection checks
- Implemented schedule_health_checks with spread scheduling
- Added check_all_connections_now for batch manual checks
- Registered IntegrationConnection in Django admin
- HEALTH_CHECK_INTERVAL setting configured (900 seconds)

## Task Commits

1. **Task 1: Create health check tasks** - `4e135f3` (feat)
2. **Task 2: Add health check settings and admin** - included in 4e135f3
3. **Task 3: Wire up manual health check trigger** - existing from 03-04

## Files Created
- `core/tasks.py` - Health check background tasks

## Files Modified
- `core/admin.py` - IntegrationConnectionAdmin registration
- `devssp/settings.py` - HEALTH_CHECK_INTERVAL setting

## Decisions Made
- Spread scheduling: checks spread evenly across HEALTH_CHECK_INTERVAL
- run_after parameter used for delayed task execution
- Admin provides read-only access to connection health info

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

To enable background health checks:
1. Run `python manage.py db_worker` as a separate process
2. Set up cron/systemd to call schedule_health_checks periodically

Manual health checks work without worker setup.

## Next Phase Readiness
- Health check infrastructure ready for all connection types
- Connection detail page shows health status with "Test Connection" button

---
*Phase: 03-integrations*
*Completed: 2026-01-23*
