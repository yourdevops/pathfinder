---
phase: quick-026
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/ci_workflows/workflow_composer.html
  - core/templates/core/ci_workflows/_compatible_steps.html
autonomous: true

must_haves:
  truths:
    - "Workflow Composer page loads without Alpine CSP parser errors"
    - "User can add steps from the catalog"
    - "User can configure step inputs (text and boolean)"
    - "User can reorder and remove steps"
    - "User can save workflow (steps_json hidden field populated)"
  artifacts:
    - path: "core/templates/core/ci_workflows/workflow_composer.html"
      provides: "CSP-compatible workflow composer using Alpine.data() registration"
    - path: "core/templates/core/ci_workflows/_compatible_steps.html"
      provides: "CSP-compatible step catalog without JSON.parse()"
  key_links:
    - from: "workflow_composer.html scripts block"
      to: "x-data='workflowComposer'"
      via: "Alpine.data('workflowComposer', ...) in alpine:init listener"
    - from: "_compatible_steps.html @click"
      to: "addStep method"
      via: "inline object literal with to_json (no JSON.parse)"
---

<objective>
Fix Alpine CSP parser errors in the CI Workflow Composer by moving complex JavaScript out of HTML attributes into a registered Alpine.data() component.

Purpose: The `@alpinejs/csp` build cannot parse complex JS expressions (arrow functions, Object.keys(), Object.entries(), JSON.stringify(), JSON.parse()) in HTML attributes. These must be moved to script blocks or simplified.

Output: Two updated templates that work with Alpine CSP mode without parser errors.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/templates/core/ci_workflows/workflow_composer.html
@core/templates/core/ci_workflows/_compatible_steps.html
@theme/templates/base.html
@core/templatetags/json_filters.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extract workflow_composer x-data to Alpine.data() component</name>
  <files>
    core/templates/core/ci_workflows/workflow_composer.html
  </files>
  <action>
Move the entire inline x-data component into a `{% block scripts %}` section at the bottom of the template.

1. Add `{% block scripts %}` with a `<script nonce="{{ csp_nonce }}">` tag containing:
   ```js
   document.addEventListener('alpine:init', () => {
       Alpine.data('workflowComposer', () => ({
           // All existing properties and methods from current x-data
           steps: [],
           addStep(step) { ... },
           removeStep(index) { ... },
           moveUp(index) { ... },
           moveDown(index) { ... },
           updateOrders() { ... },
           toggleExpand(index) { ... },
           updateStepConfig(index, inputName, value) { ... },
           phaseBadgeColor(phase) { ... },

           // NEW helper methods replacing inline Object/JSON calls:
           hasInputs(step) {
               return step.inputs_schema && Object.keys(step.inputs_schema).length > 0;
           },
           inputEntries(step) {
               if (!step.inputs_schema) return [];
               return Object.entries(step.inputs_schema).map(([name, def]) => ({name, def}));
           },
           stepsJson() {
               return JSON.stringify(this.steps);
           }
       }));
   });
   ```

   IMPORTANT: Use `alpine:init` event listener because Alpine is loaded with `defer` in `<head>`, and the scripts block is at the end of `<body>`. The `alpine:init` event fires before Alpine processes the DOM, which is exactly when `Alpine.data()` must be called.

2. Change the div from `x-data="{...complex object...}"` to `x-data="workflowComposer"`.

3. Replace CSP-incompatible expressions in HTML attributes:
   - `Object.keys(step.inputs_schema).length > 0` -> `hasInputs(step)` (line 102 x-show)
   - `Object.keys(step.inputs_schema).length > 0` -> `hasInputs(step)` (line 139 x-if)
   - `x-for="[inputName, inputDef] in Object.entries(step.inputs_schema)"` -> `x-for="entry in inputEntries(step)"`
   - All references to `inputName` in the x-for body become `entry.name`
   - All references to `inputDef` in the x-for body become `entry.def`
   - `:value="JSON.stringify(steps)"` -> `:value="stepsJson()"`
   - `step.input_config[inputName]` -> `step.input_config[entry.name]` throughout
   - `updateStepConfig(index, inputName, ...)` -> `updateStepConfig(index, entry.name, ...)`

4. Expressions that ARE CSP-safe and should NOT be changed (simple property access, no function calls):
   - `$event.target.checked`, `$event.target.value`
   - `step.expanded`, `step.id`, `step.name`, `step.phase`
   - `steps.length`, `index === 0`, `index + 1`
   - `phaseBadgeColor(step.phase)` (method call on component -- this is fine)
   - Template literal `steps.length + ' step' + (steps.length !== 1 ? 's' : '')`
  </action>
  <verify>
    Run `uv run python manage.py collectstatic --noinput` to ensure templates are valid.
    Grep for `Object.keys`, `Object.entries`, `JSON.stringify`, `JSON.parse` in `workflow_composer.html` -- they should ONLY appear inside the `<script>` block, NOT in any HTML attribute (`x-data`, `x-show`, `x-for`, `x-if`, `:value`).
  </verify>
  <done>
    workflow_composer.html uses `x-data="workflowComposer"` with all component logic in a script block. No complex JS expressions remain in HTML attributes. Helper methods (hasInputs, inputEntries, stepsJson) replace all Object/JSON calls in attributes.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix _compatible_steps.html JSON.parse() CSP violation</name>
  <files>
    core/templates/core/ci_workflows/_compatible_steps.html
  </files>
  <action>
In the `@click="addStep({...})"` handler (line 24-30), replace:
```
inputs_schema: JSON.parse('{{ step.inputs_schema|to_json|escapejs }}')
```
with:
```
inputs_schema: {{ step.inputs_schema|to_json }}
```

This works because `to_json` outputs valid JSON which is also valid JavaScript object literal syntax. The `to_json` filter from `json_filters.py` calls `json.dumps()` which produces output like `{"key": "value"}` -- this is valid JS when used inline as a value assignment. No `escapejs` needed since JSON output does not contain characters that would break HTML attributes (the `to_json` filter should handle this; if `inputs_schema` is None, it returns `{}`).

Note: Do NOT change the string-based Django template expressions (`'{{ step.uuid }}'`, `'{{ step.name|escapejs }}'`, etc.) -- those are simple string literals, not function calls, and are CSP-safe.
  </action>
  <verify>
    Grep `_compatible_steps.html` for `JSON.parse` -- should return zero matches.
    Verify `to_json` filter output is unquoted in the template (no wrapping single quotes around it).
  </verify>
  <done>
    _compatible_steps.html no longer uses JSON.parse(). inputs_schema is passed as a direct JS object literal via the to_json template filter.
  </done>
</task>

</tasks>

<verification>
1. `grep -n 'Object\.\|JSON\.' core/templates/core/ci_workflows/workflow_composer.html` -- any matches must be inside `<script>` block only, not in HTML attributes
2. `grep -n 'JSON\.parse' core/templates/core/ci_workflows/_compatible_steps.html` -- zero matches
3. `uv run python manage.py collectstatic --noinput` -- succeeds
4. Manual verification: load the Workflow Composer page in browser, confirm no console errors, add/configure/reorder/remove steps, save workflow
</verification>

<success_criteria>
- Both templates load without Alpine CSP parser errors
- No Object.keys/entries/JSON.stringify/JSON.parse in HTML attributes (only in script blocks)
- Workflow composer functionality preserved: add, configure, reorder, remove, save steps
</success_criteria>

<output>
After completion, create `.planning/quick/026-fix-alpine-csp-parser-error-in-ci-workfl/026-SUMMARY.md`
</output>
