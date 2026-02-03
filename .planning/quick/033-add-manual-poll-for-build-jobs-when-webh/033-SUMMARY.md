---
phase: quick
plan: 033
subsystem: builds
tags: [github-api, polling, htmx, builds]
dependency-graph:
  requires: [06-01, 06-02]
  provides: [manual-build-sync]
  affects: []
tech-stack:
  added: []
  patterns: [manual-polling-fallback]
file-tracking:
  key-files:
    created: []
    modified:
      - plugins/github/plugin.py
      - core/views/services.py
      - core/urls.py
      - core/templates/core/services/_builds_tab.html
decisions:
  - id: quick-033-01
    title: Viewer-level permission for sync
    choice: Allow viewers to trigger sync
    rationale: Read-only operation that doesn't modify data
metrics:
  duration: 3 min
  completed: 2026-02-03
---

# Quick Task 033: Add Manual Poll for Build Jobs

**One-liner:** Sync Builds button in builds tab to manually fetch workflow runs from GitHub when webhooks unavailable.

## What Was Built

Added manual polling capability for build jobs when webhooks cannot be registered (local dev, non-public installations).

### Components

1. **GitHubPlugin.list_workflow_runs()** - New method to fetch recent workflow runs from GitHub API
2. **ServiceSyncBuildsView** - View to handle POST requests and enqueue polling tasks
3. **Sync Builds button** - UI button in builds tab header that triggers manual polling

### User Flow

1. User navigates to service builds tab
2. Clicks "Sync Builds" button (always visible)
3. Backend fetches recent workflow runs from GitHub
4. Enqueues poll_build_details task for each run
5. Build records created/updated asynchronously
6. User sees success message and can refresh to see builds

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Permission level | Viewer can sync | Read-only operation, doesn't modify service |
| Runs per page | 10 | Reasonable limit for manual sync |
| CI workflow filter | Skip non-CI runs | Only process runs starting with "CI -" prefix |

## Files Changed

| File | Change |
|------|--------|
| `plugins/github/plugin.py` | Added list_workflow_runs method |
| `core/views/services.py` | Added ServiceSyncBuildsView class |
| `core/urls.py` | Added service_sync_builds URL pattern |
| `core/templates/core/services/_builds_tab.html` | Added Sync Builds button to header |

## Commits

| Hash | Description |
|------|-------------|
| c61c1e3 | feat(quick-033): add list_workflow_runs method to GitHubPlugin |
| 9fe8cd7 | feat(quick-033): add ServiceSyncBuildsView for manual build polling |
| 976e6d4 | feat(quick-033): add Sync Builds button to builds tab UI |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- [x] URL resolves: `/projects/{project}/services/{service}/sync-builds/`
- [x] View imports and loads correctly
- [x] Template compiles without errors
- [x] Sync Builds button appears in template
- [x] Button submits POST to correct endpoint
