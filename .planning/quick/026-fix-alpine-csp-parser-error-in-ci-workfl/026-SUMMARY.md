---
phase: quick-026
plan: 01
subsystem: ci-workflows
tags: [alpine, csp, javascript, templates]
dependency-graph:
  requires: [quick-025]
  provides: [csp-compatible-workflow-composer]
  affects: []
tech-stack:
  added: []
  patterns: [alpine-data-registration, csp-compatible-templates]
key-files:
  created: []
  modified:
    - core/templates/core/ci_workflows/workflow_composer.html
    - core/templates/core/ci_workflows/_compatible_steps.html
decisions:
  - id: Q026-D1
    description: "Use alpine:init event for Alpine.data() registration"
    rationale: "Alpine loaded with defer in head; alpine:init fires before DOM processing"
metrics:
  duration: 1 min
  completed: 2026-01-31
---

# Quick Task 026: Fix Alpine CSP Parser Error in CI Workflow Composer

**One-liner:** Move complex JS (Object.keys/entries, JSON.stringify/parse) from HTML attributes into Alpine.data() script block for CSP compatibility

## What Was Done

### Task 1: Extract workflow_composer x-data to Alpine.data() component
- Moved all inline `x-data="{...}"` logic into `Alpine.data('workflowComposer', ...)` registered via `alpine:init` event listener in a `{% block scripts %}` section
- Changed div from complex inline object to `x-data="workflowComposer"`
- Added three CSP-safe helper methods:
  - `hasInputs(step)` -- replaces `Object.keys(step.inputs_schema).length > 0` in x-show/x-if
  - `inputEntries(step)` -- replaces `Object.entries(step.inputs_schema)` in x-for
  - `stepsJson()` -- replaces `JSON.stringify(steps)` in :value
- Updated all x-for body references from `[inputName, inputDef]` destructuring to `entry.name`/`entry.def`
- **Commit:** d3a6656

### Task 2: Fix _compatible_steps.html JSON.parse() CSP violation
- Replaced `JSON.parse('{{ step.inputs_schema|to_json|escapejs }}')` with direct `{{ step.inputs_schema|to_json }}`
- The `to_json` filter outputs valid JSON which is also valid JS object literal syntax, no parsing needed
- **Commit:** e019b6c

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

1. `Object.*` and `JSON.*` in workflow_composer.html only appear inside `<script>` block (lines 214, 218, 221), not in any HTML attributes
2. Zero `JSON.parse` matches in _compatible_steps.html
3. `collectstatic --noinput` succeeds without errors

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | d3a6656 | feat(quick-026): extract workflow composer x-data to Alpine.data() component |
| 2 | e019b6c | fix(quick-026): remove JSON.parse() CSP violation from compatible steps template |
