---
phase: quick
plan: 030
subsystem: ci-workflows
tags: [modal, deletion, usage-tracking, csp]
dependency-graph:
  requires: [05.3]
  provides: [reusable-confirm-modal, repo-deletion, workflow-deletion-guard]
  affects: []
tech-stack:
  added: []
  patterns: [include-with-modal-partial, data-attribute-delegation, server-side-deletion-guard]
key-files:
  created:
    - core/templates/core/components/_confirm_modal.html
  modified:
    - theme/templates/base.html
    - core/views/ci_workflows.py
    - core/urls.py
    - core/templates/core/ci_workflows/repo_detail.html
    - core/templates/core/ci_workflows/workflow_detail.html
decisions:
  - Pure CSS hidden-class toggling instead of Alpine for modal (CSP-safe, zero dependencies)
  - data-confirm-modal attribute pattern coexists with existing data-confirm handler
  - Server-side guards on both delete views prevent circumvention via direct POST
metrics:
  duration: 3 min
  completed: 2026-02-02
---

# Quick Task 030: Usage Tracking & Deletion Modal Summary

**One-liner:** Reusable CSP-safe confirmation modal, repo usage tracking with workflow links, and guarded deletion for repos and workflows.

## What Was Done

### Task 1: Modal infrastructure -- reusable partial + global handlers
- Created `_confirm_modal.html` partial using `{% include ... with %}` template variables (confirm_id, confirm_title, confirm_message, confirm_action, confirm_button_text)
- Added global click delegation in base.html for `data-confirm-modal` (open), `.confirm-modal-close` (close), `.confirm-modal-backdrop` (close)
- Added Escape key handler for closing visible modals
- Preserved existing `data-confirm` handler used by 11 other templates
- **Commit:** ee5bf32

### Task 2: Backend -- StepsRepoDeleteView + URL + view context updates
- Added `StepsRepoDeleteView` with server-side guard checking `CIWorkflowStep` usage before deletion
- Added `repo_delete` URL pattern in ci_workflows
- Updated `StepsRepoDetailView` to pass `workflows_using`, `can_delete`, `repo_delete_url` to template
- Updated `WorkflowDetailView` to guard `can_delete` by `services_using.exists()`
- Updated `WorkflowDeleteView` with server-side guard preventing deletion when services reference workflow
- Moved `reverse` and `messages` imports to module level
- **Commit:** b0a4dc0

### Task 3: Templates -- repo detail usage section + workflow detail modal integration
- Added "Workflows Using Steps" section to repo detail with clickable workflow links and count
- Added conditional delete button to repo detail header (visible only when can_delete)
- Replaced browser `confirm()` form in workflow detail with modal trigger button
- Both pages include `_confirm_modal.html` partial with appropriate context
- **Commit:** 1e9aa64

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed duplicate local import of reverse**
- **Found during:** Task 2
- **Issue:** `from django.urls import reverse` was imported locally inside `WorkflowCreateView.post()` and also needed at module level
- **Fix:** Moved to module-level import, removed local duplicate
- **Files modified:** core/views/ci_workflows.py

## Verification Results

- `uv run python manage.py check` -- no errors
- `StepsRepoDeleteView` import verified
- `repo_delete` URL pattern confirmed in urls.py
- `data-confirm-modal` present in both template files
- `_confirm_modal.html` include present in both template files
- `workflows_using` present in repo_detail.html
- Existing `data-confirm` handler preserved in base.html
- Tailwind build and collectstatic successful
