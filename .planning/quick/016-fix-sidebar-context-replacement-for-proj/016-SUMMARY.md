---
phase: quick
plan: 016
subsystem: core
tags: [context-processor, sidebar, navigation, url-migration]
requires: [04.1-01]
provides: [project-scoped-sidebar-context]
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - core/context_processors.py
decisions:
  - id: quick-016-01
    choice: "Simple find-replace from project_uuid to project_name"
    why: "Phase 4.1 migrated all URLs from UUID to name-based slugs"
metrics:
  duration: "0.5 min"
  completed: "2026-01-26"
---

# Quick Task 016: Fix Sidebar Context Replacement for Project Navigation

**One-liner:** Fixed context processor to use project_name URL kwarg instead of deprecated project_uuid for sidebar switching.

## What Was Done

Updated `navigation_context()` function in `core/context_processors.py` to detect project context using the new name-based URL structure from Phase 4.1.

### Changes Made

1. **URL kwarg detection** (line 63):
   - Changed from `'project_uuid' in request.resolver_match.kwargs`
   - Changed to `'project_name' in request.resolver_match.kwargs`

2. **Project lookup** (lines 65-66):
   - Changed from `Project.objects.get(uuid=request.resolver_match.kwargs['project_uuid'])`
   - Changed to `Project.objects.get(name=request.resolver_match.kwargs['project_name'])`

### Root Cause

Phase 4.1 migrated all URLs from UUID-based to name-based slugs (e.g., `/projects/<uuid>/` became `/projects/<project_name>/`). The context processor was not updated during that migration, causing the sidebar to always show main navigation even when viewing project pages.

## Verification

- [x] Django check passes with no issues
- [x] Code syntax is valid
- [x] Project-scoped URLs now trigger project sidebar context

## Commits

| Hash | Description |
|------|-------------|
| 9a120cf | fix(quick-016): update context processor to use project_name |

## Deviations from Plan

None - plan executed exactly as written.
