---
phase: quick-038
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - core/views/services.py
  - core/templates/core/services/_ci_tab.html
  - theme/templates/base.html
autonomous: true

must_haves:
  truths:
    - "When user picks a different workflow in the dropdown, version list updates instantly without page reload or form submit"
    - "The latest available version is auto-selected as default when switching workflows"
    - "Version dropdown shows correct versions for each workflow from the pre-loaded map"
    - "Saving workflow assignment still works as before via HTMX POST"
    - "Saving version pin still works as before via HTMX POST"
  artifacts:
    - path: "core/views/services.py"
      provides: "workflow_versions_map JSON context for all available workflows and their versions"
    - path: "core/templates/core/services/_ci_tab.html"
      provides: "Unified Alpine ciSelector component driving both workflow and version dropdowns"
    - path: "theme/templates/base.html"
      provides: "Alpine.data ciSelector component registration"
  key_links:
    - from: "core/views/services.py"
      to: "core/templates/core/services/_ci_tab.html"
      via: "workflow_versions_map JSON context variable"
      pattern: "workflow_versions_map"
    - from: "theme/templates/base.html"
      to: "core/templates/core/services/_ci_tab.html"
      via: "Alpine.data ciSelector component"
      pattern: "ciSelector"
---

<objective>
Dynamically swap CI workflow versions in the service CI tab when a different workflow is selected, without requiring a form save/page reload.

Purpose: Currently, the version dropdown only shows versions for the *saved* workflow. When users pick a different workflow in the selector, versions don't update until after saving. This creates confusion -- users can't preview what versions are available for a workflow before committing to it.

Output: A client-side workflow-to-versions map that Alpine swaps instantly on workflow selection, with the latest version auto-selected as default.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/views/services.py (ServiceDetailView.get_context_data for ci tab, around line 353-395)
@core/templates/core/services/_ci_tab.html (full template - workflow + version dropdowns)
@theme/templates/base.html (Alpine.data component registrations - dropdown, copyBtn)
@core/models.py (CIWorkflow, CIWorkflowVersion models, get_available_workflows_for_project)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build workflow-versions map in view and register Alpine ciSelector component</name>
  <files>
    core/views/services.py
    theme/templates/base.html
  </files>
  <action>
**In `core/views/services.py` - ServiceDetailView.get_context_data (ci tab section):**

After the existing `available_workflows` queryset (line ~360), build a `workflow_versions_map` dict that maps every available workflow ID to its list of versions. This replaces the current single-workflow `available_versions` logic.

```python
# Build versions map for ALL available workflows (for client-side dynamic swap)
from core.models import CIWorkflowVersion

workflow_ids = list(available_workflows.values_list("id", flat=True))
all_versions_qs = CIWorkflowVersion.objects.filter(
    workflow_id__in=workflow_ids,
    status__in=[CIWorkflowVersion.Status.AUTHORIZED, CIWorkflowVersion.Status.DRAFT],
).order_by("-published_at", "-created_at")

# Check draft permission
allow_drafts = False
try:
    ci_config = self.project.ci_config
    allow_drafts = ci_config.allow_draft_workflows
except Exception:
    pass

# Build the map: {workflow_id_str: [{id: str, version: str, status: str, label: str, author: str}, ...]}
import json
versions_map = {}
for wf_id in workflow_ids:
    versions_for_wf = []
    for v in all_versions_qs:
        if v.workflow_id != wf_id:
            continue
        if not allow_drafts and v.status == "draft":
            continue
        versions_for_wf.append({
            "id": str(v.id),
            "version": v.version or "",
            "status": v.status,
            "label": "Draft" if v.status == "draft" else ("v" + v.version if v.version else "Draft"),
            "author": str(v.author) if v.author else "",
        })
    versions_map[str(wf_id)] = versions_for_wf

context["workflow_versions_json"] = json.dumps(versions_map)
```

Keep the existing `available_versions` for backwards compatibility with the read-only (non-edit) view, but the edit mode will use the JSON map.

Also keep `context["available_versions"]` as-is (the current workflow's versions) for the non-edit display.

**In `theme/templates/base.html` - inside the `alpine:init` event listener:**

Register a new `ciSelector` Alpine.data component after the existing `copyBtn` component:

```javascript
Alpine.data('ciSelector', function(initialWf, initialVer, versionsMap) {
    return {
        wfVal: String(initialWf),
        wfInitial: String(initialWf),
        wfOpen: false,
        verVal: String(initialVer),
        verInitial: String(initialVer),
        verOpen: false,
        versionsMap: versionsMap,
        versions: versionsMap[String(initialWf)] || [],
        pickWf: function(v) {
            this.wfVal = v;
            this.wfOpen = false;
            this.versions = this.versionsMap[v] || [];
            this.verVal = this.versions.length > 0 ? this.versions[0].id : 'none';
        },
        pickVer: function(v) {
            this.verVal = v;
            this.verOpen = false;
        }
    };
});
```

Key behaviors:
- `pickWf(v)` updates workflow selection, swaps version list from map, auto-selects first (latest) version
- `pickVer(v)` updates version selection
- `wfVal !== wfInitial` controls "Save" button visibility for workflow form
- `verVal !== verInitial` controls "Save" button visibility for version form
- `versions` array reactively updates when workflow changes

Note: All methods use `function()` syntax (not arrow functions) for Alpine CSP compatibility. All expressions in the template must be single expressions (no semicolons).
  </action>
  <verify>
    Run `uv run python manage.py check` to verify no Django errors. Manually inspect that `theme/templates/base.html` has the `ciSelector` component registered and `core/views/services.py` builds `workflow_versions_json`.
  </verify>
  <done>
    View passes `workflow_versions_json` context with complete map of all available workflows to their versions. Alpine `ciSelector` component registered in base.html with pickWf/pickVer methods.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewrite CI tab template to use ciSelector component with dynamic version swapping</name>
  <files>
    core/templates/core/services/_ci_tab.html
  </files>
  <action>
Rewrite the edit-mode section of `_ci_tab.html` to use a single `ciSelector` Alpine component wrapping both the workflow and version selectors. The version dropdown must render dynamically from Alpine data (using `x-for`) instead of Django `{% for %}` server-rendering.

**Key structural changes:**

1. **Wrap the entire Row 1 `<div class="flex items-start gap-4">` in a single `x-data="ciSelector(...)"` div** instead of having separate `x-data="dropdown(...)"` on each form. Pass:
   - `initialWf`: current `ci_workflow.id` or empty string
   - `initialVer`: current `service.ci_workflow_version_id` or `'none'`
   - `versionsMap`: the JSON map via Django's `json_script` filter or inline

   Use Django's `{{ workflow_versions_json|safe }}` to inline the map (it's already JSON-encoded in the view).

   ```html
   {% if can_edit %}
   <div x-data="ciSelector('{{ ci_workflow.id|default:"" }}', '{{ service.ci_workflow_version_id|default:"none" }}', {{ workflow_versions_json }})"
        class="flex items-start gap-4">
   ```

2. **Workflow dropdown form**: Change from `x-data="dropdown(...)"` to using the parent ciSelector data.
   - Replace `val` with `wfVal`, `open` with `wfOpen`, `initial` with `wfInitial`
   - Replace `pick('...')` with `pickWf('...')`
   - Hidden input: `:value="wfVal"` instead of `:value="val"`
   - Save button: `x-show="wfVal !== wfInitial"`
   - Remove the `x-data="dropdown(...)"` from the workflow `<form>` tag

3. **Version dropdown**: Must always render (not gated by `{% if service.ci_workflow %}`), but conditionally shown via Alpine `x-show="wfVal !== ''"`.
   - Replace Django `{% for ver in available_versions %}` with Alpine `x-for="ver in versions"` using `<template>` tags
   - Hidden input: `:value="verVal"`
   - Trigger button shows selected version: use `x-text` bound to computed label
   - Dropdown items use `:class` for highlighting, `@click="pickVer(ver.id)"` for selection
   - Save button: `x-show="verVal !== verInitial"`
   - Remove the `x-data="dropdown(...)"` from the version `<form>` tag

4. **Version trigger button display**: Instead of server-rendered `x-show` per version, use a single dynamic display:
   ```html
   <span x-show="verVal === 'none'" class="text-sm text-dark-muted">Not pinned</span>
   <template x-for="ver in versions">
       <div x-show="verVal === ver.id" class="flex items-center gap-2">
           <span class="text-sm text-dark-text" x-text="ver.label"></span>
           <!-- Status badge via x-show -->
           <span x-show="ver.status === 'authorized'" class="px-1.5 py-0.5 text-xs rounded-full bg-green-500/20 text-green-300">Authorized</span>
           <span x-show="ver.status === 'draft'" class="px-1.5 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-300">Draft</span>
       </div>
   </template>
   ```

5. **Version dropdown panel items**: Also use `x-for`:
   ```html
   <template x-for="ver in versions">
       <div @click="pickVer(ver.id)"
            :class="verVal === ver.id && 'bg-dark-accent/5'"
            class="px-3 py-2.5 cursor-pointer hover:bg-dark-bg/50 transition-colors">
           <div class="flex items-center gap-2">
               <span class="text-sm text-dark-text" x-text="ver.label"></span>
               <span x-show="ver.status === 'authorized'" class="px-1.5 py-0.5 text-xs rounded-full bg-green-500/20 text-green-300">Authorized</span>
               <span x-show="ver.status === 'draft'" class="px-1.5 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-300">Draft</span>
               <span x-show="ver.status === 'revoked'" class="px-1.5 py-0.5 text-xs rounded-full bg-red-500/20 text-red-300">Revoked</span>
               <span x-show="ver.author" class="text-xs text-dark-muted ml-auto" x-text="ver.author"></span>
           </div>
       </div>
   </template>
   ```

6. **No-versions state**: Show "No versions available" when `versions.length === 0` and a workflow is selected:
   ```html
   <span x-show="wfVal !== '' && versions.length === 0" class="text-sm text-dark-muted py-2.5">No versions available</span>
   ```

7. **Keep the read-only (non-edit) section unchanged** -- it still uses server-rendered `{% if %}` / `{% for %}` since it's static display.

8. **Close the wrapping div** after both selectors.

**IMPORTANT Alpine CSP constraints:**
- All `@click` handlers must be single expressions: `pickWf('{{ wf.id }}')` is fine
- No semicolons in any directive expression
- No arrow functions
- `x-for` uses `"ver in versions"` syntax (supported by CSP build)
- `:class` with ternary is fine: `verVal === ver.id && 'bg-dark-accent/5'`

**IMPORTANT:** The workflow dropdown items STILL use Django `{% for wf in available_workflows %}` because workflow data is static (doesn't change client-side). Only version dropdown items switch to Alpine `x-for` because they need to reactively update.
  </action>
  <verify>
    Run `uv run python manage.py check` to verify template syntax. Run `make build && make run` and navigate to a service's CI tab. Test:
    1. Pick a different workflow in the dropdown -- version list should update immediately
    2. The latest version should be auto-selected
    3. Clicking "Save" on workflow form should submit and refresh the tab
    4. Clicking "Save" on version form should submit and refresh the tab
    5. Selecting "No workflow" should hide the version selector
  </verify>
  <done>
    Version dropdown dynamically updates when selecting different workflows. Latest version auto-selected. Both Save buttons work. No page reload needed to see versions for a different workflow.
  </done>
</task>

</tasks>

<verification>
- `uv run python manage.py check` passes with no errors
- Navigate to service CI tab with a service that has a workflow assigned
- Switch workflow selection to a different workflow -- versions update instantly in the dropdown
- Latest version is auto-selected as default when switching workflows
- "Save" button on workflow selector appears when selection differs from current
- "Save" button on version selector appears when selection differs from current
- Both Save buttons submit correctly via HTMX and refresh the tab
- Selecting "No workflow" hides the version section
- Read-only view (viewer role) still displays correctly with server-rendered data
</verification>

<success_criteria>
CI workflow version dropdown dynamically swaps to show the correct versions for whatever workflow is currently selected in the dropdown, without requiring a form save or page reload. The latest available version is auto-selected as default.
</success_criteria>

<output>
After completion, create `.planning/quick/38-dynamic-ci-workflow-version-swapping-in-/038-SUMMARY.md`
</output>
