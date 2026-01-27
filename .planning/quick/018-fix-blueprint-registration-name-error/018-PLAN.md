---
phase: quick-018
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/views/blueprints.py
autonomous: true

must_haves:
  truths:
    - "Blueprint registration succeeds and redirects to detail page"
    - "Blueprint name is set from manifest at creation time"
  artifacts:
    - path: "core/views/blueprints.py"
      provides: "BlueprintRegisterView with name field set"
      contains: "name=manifest.get"
  key_links:
    - from: "BlueprintRegisterView.post()"
      to: "Blueprint.objects.create()"
      via: "manifest name extraction"
      pattern: "name=manifest\\.get\\('name'"
---

<objective>
Fix blueprint registration name error by setting blueprint name from manifest at creation time.

Purpose: Blueprint registration currently fails with NoReverseMatch because the name field is empty when redirecting to the detail page. The manifest is already fetched and contains the name - it just needs to be passed to the create() call.

Output: Working blueprint registration that correctly sets the name field.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@core/views/blueprints.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add name field to Blueprint.objects.create()</name>
  <files>core/views/blueprints.py</files>
  <action>
In BlueprintRegisterView.post() at line 221-226, modify the Blueprint.objects.create() call to include the name field from the manifest.

Current code (line 221-226):
```python
blueprint = Blueprint.objects.create(
    git_url=git_url,
    connection=connection,
    sync_status='pending',
    created_by=request.user.username,
)
```

Updated code:
```python
blueprint = Blueprint.objects.create(
    name=manifest.get('name', ''),
    git_url=git_url,
    connection=connection,
    sync_status='pending',
    created_by=request.user.username,
)
```

The manifest variable is already available at this point (line 209) from the read_manifest_from_repo() call.

Note: The sync task will later verify/update the name if needed, but setting it at creation time:
1. Enables the redirect to work immediately
2. Is consistent with the preview validation flow (manifest must be valid to register)
3. Avoids race condition between create and sync completion
  </action>
  <verify>
Run: `grep -A 6 "Blueprint.objects.create" core/views/blueprints.py | grep "name=manifest"`
Expected: Line containing `name=manifest.get('name', '')` appears in output
  </verify>
  <done>Blueprint.objects.create() call includes name=manifest.get('name', '') and the redirect to blueprints:detail will work correctly</done>
</task>

</tasks>

<verification>
1. Grep verification: `grep -n "name=manifest" core/views/blueprints.py` shows the fix is in place
2. Syntax check: `python -c "import core.views.blueprints"` completes without error
</verification>

<success_criteria>
- BlueprintRegisterView.post() sets name from manifest at Blueprint creation
- No syntax errors in the modified file
- The fix enables successful blueprint registration with proper redirect
</success_criteria>

<output>
After completion, create `.planning/quick/018-fix-blueprint-registration-name-error/018-SUMMARY.md`
</output>
