---
phase: quick
plan: 023
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templatetags/json_filters.py
  - core/templates/core/ci_workflows/_compatible_steps.html
autonomous: true

must_haves:
  truths:
    - "Clicking an available step in the composer adds it to the selected steps basket"
    - "Steps with inputs_schema render their config panel when expanded"
    - "Steps with empty inputs_schema still add correctly on click"
  artifacts:
    - path: "core/templatetags/json_filters.py"
      provides: "to_json template filter for safe JSON serialization"
    - path: "core/templates/core/ci_workflows/_compatible_steps.html"
      provides: "Fixed @click handler using proper JSON serialization"
  key_links:
    - from: "core/templates/core/ci_workflows/_compatible_steps.html"
      to: "Alpine.js addStep() in workflow_composer.html"
      via: "@click handler with valid JSON for inputs_schema"
      pattern: "addStep\\("
---

<objective>
Fix the CI Step Composer so clicking available steps actually adds them to the workflow.

Purpose: The @click handler in _compatible_steps.html uses `JSON.parse('{{ step.inputs_schema|escapejs }}')` which fails silently because Django renders Python dicts with single quotes, True/False/None -- not valid JSON. This JS error prevents the entire @click expression from executing, so addStep() never fires.

Output: Working step selection in the workflow composer.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/templates/core/ci_workflows/_compatible_steps.html
@core/templates/core/ci_workflows/workflow_composer.html
@core/templatetags/audit_tags.py (example of existing templatetag module)
@core/models.py (CIStep model, lines 529-568 -- inputs_schema is JSONField)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create to_json template filter and fix the @click handler</name>
  <files>
    core/templatetags/json_filters.py
    core/templates/core/ci_workflows/_compatible_steps.html
  </files>
  <action>
1. Create `core/templatetags/json_filters.py` with a `to_json` template filter:
   - Import `json` and `django.utils.safestring.mark_safe`
   - Register a `@register.filter(name='to_json')` that calls `json.dumps(value)` and returns the result (NOT marked safe -- we want escapejs to handle escaping)
   - Actually, the better approach: the filter should return `mark_safe(json.dumps(value))` because we will use it INSIDE a JS string literal that is already inside an @click attribute. We need valid JSON output directly.

   Wait -- let me be precise about the fix. The current code is:
   ```
   inputs_schema: JSON.parse('{{ step.inputs_schema|escapejs }}' || '{}')
   ```

   The problem: `{{ step.inputs_schema|escapejs }}` renders Python repr, not JSON.

   The fix: Replace with a `to_json` filter that produces valid JSON. The cleanest approach:
   ```
   inputs_schema: {{ step.inputs_schema|to_json }}
   ```
   No JSON.parse needed -- just output the JSON object literal directly into the JS expression. The `to_json` filter should use `json.dumps()` and `mark_safe()` since it produces a JS object literal for inline use.

2. In `_compatible_steps.html`, add `{% load json_filters %}` at the top (after the comment block).

3. Replace line 28:
   ```
   inputs_schema: JSON.parse('{{ step.inputs_schema|escapejs }}' || '{}')
   ```
   With:
   ```
   inputs_schema: {{ step.inputs_schema|to_json }}
   ```
   This outputs a valid JS object literal directly (json.dumps of a Python dict produces valid JS).

IMPORTANT: Do NOT change any other lines in the template. Only add the load tag and fix the inputs_schema line.
  </action>
  <verify>
    1. `source venv/bin/activate && python -c "from core.templatetags.json_filters import to_json; print(to_json({'key': 'value', 'nested': True}))"`
       Should output: `{"key": "value", "nested": true}` (valid JSON with lowercase true)
    2. `source venv/bin/activate && python manage.py check` -- no errors
    3. Manual browser test: Navigate to CI Workflows -> Create a workflow -> select runtime -> on composer page, click an available step. It should appear in the left "Workflow Steps" basket.
  </verify>
  <done>
    - Clicking any available step in the composer adds it to the workflow steps basket
    - Steps with inputs_schema show their configuration when expanded
    - Steps with empty inputs_schema ({}) add without error
    - No JavaScript console errors when clicking steps
  </done>
</task>

</tasks>

<verification>
1. `python manage.py check` passes
2. Browser: Navigate to workflow composer, click available steps -- they appear in the basket
3. Browser console: No JS errors on step click
4. Verify steps with and without inputs_schema both work
</verification>

<success_criteria>
- Available steps are clickable and get added to the workflow basket
- The to_json filter correctly serializes Python dicts to valid JSON/JS object literals
- No regression in other workflow composer functionality (reorder, remove, save)
</success_criteria>

<output>
After completion, create `.planning/quick/023-fix-ci-step-composer-click-actions-not-a/023-SUMMARY.md`
</output>
