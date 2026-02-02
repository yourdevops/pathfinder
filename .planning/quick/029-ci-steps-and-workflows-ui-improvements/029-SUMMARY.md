---
phase: quick-029
plan: 01
status: complete
completed: 2026-02-02
duration: 4 min
tasks_completed: 3
tasks_total: 3
subsystem: ci-workflows-ui
tags: [ci-steps, workflows, htmx, alpine, sorting, ui]
tech-stack:
  patterns: [alpine-client-sort, htmx-cascade-selects, data-attribute-sorting]
key-files:
  modified:
    - core/views/ci_workflows.py
    - core/forms/ci_workflows.py
    - core/urls.py
    - core/templates/core/ci_workflows/steps_catalog.html
    - core/templates/core/ci_workflows/_steps_table.html
    - core/templates/core/ci_workflows/step_detail.html
    - core/templates/core/ci_workflows/workflow_create.html
    - core/templates/core/ci_workflows/_compatible_steps.html
---

# Quick Task 029: CI Steps and Workflows UI Improvements

**One-liner:** 7 targeted UX enhancements across steps catalog, step detail, workflow creation, and workflow composer.

## Changes Made

### Task 1: Steps Catalog Improvements (5a04265)
- Renamed "Engine" column header to "CI Engine" with human-friendly display names (e.g., "GitHub Actions" instead of "github_actions")
- Added `Case/When` phase ordering: Setup > Test > Build > Package (was alphabetical: build, package, setup, test)
- Added Alpine.js client-side sortable table headers with sort direction indicators (arrows)
- Added `data-sort-*` attributes to table rows for name, phase (numeric), engine, repository
- Wired runtime version filter to dynamically populate via fetch when runtime selection changes
- Updated `RuntimeVersionsView` to accept `runtime` param as fallback for `runtime_family`

### Task 2: Step Detail Source Link (c9e7595)
- Computed source URL from `repository.git_url`, `commit_sha`, `directory_name`, and engine file name
- Added clickable "Source" link in format `directory/file@sha` that opens repository file at correct version in new tab
- Added "CI Engine" display name to step detail General info card

### Task 3: Workflow Creation & Composer Enhancements (38657f1)
- Added `engine` field to `WorkflowCreateForm` as first selection after description
- Created `EngineRuntimesView` HTMX endpoint returning runtime family options filtered by engine
- Wired CI Engine > Runtime Family > Runtime Version HTMX cascade in workflow creation form
- Engine value passed through to composer via URL query params
- Added (i) info button on each compatible step in composer, opening step detail in new tab with `@click.stop`
- Fixed phase ordering to Setup > Test > Build > Package across all views (was Setup > Build > Test > Package in 3 places)

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Client-side sorting via Alpine + data attributes | Avoids server round-trips; works with HTMX-loaded table body |
| Fetch API for dynamic version loading | HTMX runtime select already triggers table filter; version loading done via JS fetch to avoid dual hx-get |
| `@click.stop` on info button | Prevents parent `@click="addStepFromEl($el)"` from firing when clicking info |

## Verification

- `uv run python manage.py check` -- passes with no issues
- `uv run python manage.py tailwind build` -- completes successfully
- `uv run python manage.py collectstatic --noinput` -- completes successfully
