---
phase: quick
plan: 023
subsystem: ci-workflows
tags: [template-filter, json, alpine-js, bugfix]
completed: 2026-01-29
duration: "30s"
key-files:
  created:
    - core/templatetags/json_filters.py
  modified:
    - core/templates/core/ci_workflows/_compatible_steps.html
decisions:
  - id: q023-1
    description: "Use mark_safe(json.dumps()) for inline JS object literals"
    rationale: "Output goes directly into Alpine.js @click expression; needs valid JS, not escaped string"
---

# Quick Task 023: Fix CI Step Composer Click Actions Summary

**One-liner:** Added to_json template filter to fix broken Python-dict-to-JS serialization in workflow composer step clicks.

## What Was Done

### Task 1: Create to_json template filter and fix the @click handler

- Created `core/templatetags/json_filters.py` with a `to_json` filter that uses `json.dumps()` + `mark_safe()` to produce valid JS object literals from Python dicts
- Added `{% load json_filters %}` to `_compatible_steps.html`
- Replaced `JSON.parse('{{ step.inputs_schema|escapejs }}' || '{}')` with `{{ step.inputs_schema|to_json }}`

**Root cause:** Django's `escapejs` filter renders the Python repr of a dict (single quotes, `True`/`False`/`None`) which is not valid JSON. `JSON.parse()` then fails silently, preventing the entire `@click` expression from executing, so `addStep()` never fires.

**Fix:** The `to_json` filter uses `json.dumps()` which correctly converts Python `True` to `true`, `False` to `false`, `None` to `null`, and uses double-quoted strings -- producing valid JSON which is also valid JavaScript.

## Verification

- `to_json({'key': 'value', 'nested': True})` outputs `{"key": "value", "nested": true}` (valid JSON)
- `python manage.py check` passes with no issues
- Steps with and without inputs_schema both serialize correctly

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Hash | Description |
|------|-------------|
| 754dcbb | fix(023): fix CI step composer click actions not adding steps |
