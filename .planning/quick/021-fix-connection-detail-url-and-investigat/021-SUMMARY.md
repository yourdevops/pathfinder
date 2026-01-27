---
quick: 021
subsystem: connections, worker
tags: [url-fix, slug-migration, background-tasks, docker-compose]
key-files:
  modified:
    - core/templates/core/connections/detail.html
    - docker-compose.yml
decisions:
  - Use wildcard queue-name for worker flexibility
metrics:
  duration: 1 min
  completed: 2026-01-27
---

# Quick Task 021: Fix Connection Detail URL and Worker Queue

**One-liner:** Fixed stale UUID URL references in connection detail template and configured worker to process all task queues.

## Changes Made

### Task 1: Fix connection detail template URL references
**Commit:** 1aec968

Updated the Usage section links in `/core/templates/core/connections/detail.html` to use slug-based URL parameters instead of UUIDs (migrated in Phase 4.1):

- Line 257: Changed `projects:detail` from `project_uuid=attachment.project.uuid` to `project_name=attachment.project.name`
- Line 276: Changed `projects:environment_detail` from `project_uuid` and `env_uuid` to `project_name` and `env_name`

### Task 2: Fix worker to process all task queues
**Commit:** c65a4b3

Updated the worker service command in `docker-compose.yml`:

- Changed: `python manage.py db_worker`
- To: `python manage.py db_worker --queue-name "*"`

This ensures the worker processes tasks from all queues:
- `default`
- `health_checks`
- `blueprint_sync`
- `repository_scaffolding`

## Deviations from Plan

None - plan executed exactly as written.

## Verification

1. Connection detail page (`/connections/<name>/`) renders without NoReverseMatch error
2. Project and environment links in Usage section navigate to correct slug-based URLs
3. Worker logs show `queues=*` on startup
4. Background tasks execute from all queue types

## Impact

- Fixes connection detail page crash after Phase 4.1 slug URL migration
- Enables background task processing for health checks, blueprint sync, and repository scaffolding
