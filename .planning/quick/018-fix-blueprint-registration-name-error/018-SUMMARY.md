---
phase: quick-018
plan: 01
subsystem: blueprints
tags: [bugfix, blueprint-registration, views]
dependency-graph:
  requires: [04-02, 04-03]
  provides: [working-blueprint-registration]
  affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - core/views/blueprints.py
decisions: []
metrics:
  duration: "< 1 min"
  completed: 2026-01-27
---

# Quick Task 018: Fix Blueprint Registration Name Error

**One-liner:** Set blueprint name from manifest at creation time to fix NoReverseMatch redirect error

## What Changed

### Task 1: Add name field to Blueprint.objects.create()

In `BlueprintRegisterView.post()`, the blueprint creation was missing the `name` field. The manifest was already being read and validated (line 209), but the name wasn't being passed to the create call.

**Before (line 221-226):**
```python
blueprint = Blueprint.objects.create(
    git_url=git_url,
    connection=connection,
    sync_status='pending',
    created_by=request.user.username,
)
```

**After (line 221-227):**
```python
blueprint = Blueprint.objects.create(
    name=manifest.get('name', ''),
    git_url=git_url,
    connection=connection,
    sync_status='pending',
    created_by=request.user.username,
)
```

This ensures:
1. The redirect to `blueprints:detail` works immediately (line 232)
2. Consistency with preview validation flow (manifest must be valid to register)
3. No race condition between create and sync completion

## Commits

| Commit | Description | Files |
|--------|-------------|-------|
| b4a723c | fix(quick-018): set blueprint name from manifest at creation | core/views/blueprints.py |

## Verification

- [x] `grep -A 6 "Blueprint.objects.create" core/views/blueprints.py | grep "name=manifest"` shows the fix
- [x] `python manage.py check` passes with no errors
- [x] Blueprint registration will now redirect correctly to detail page

## Deviations from Plan

None - plan executed exactly as written.
