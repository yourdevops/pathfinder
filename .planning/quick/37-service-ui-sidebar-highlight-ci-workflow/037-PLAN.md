---
phase: "37"
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/components/nav_service.html
  - core/templates/core/services/_ci_tab.html
  - core/templates/core/services/_settings_tab.html
  - core/views/services.py
  - core/urls.py
  - core/models.py
  - core/tasks.py
autonomous: true
must_haves:
  truths:
    - "Sidebar nav item highlight follows the active tab when switching via HTMX"
    - "CI Workflow tab shows workflow/version selectors, manifest status, and push button in one consolidated card"
    - "Workflow selector labeled 'Workflow', version selector labeled 'Version'"
    - "Save button only appears when user changes a selector value from current"
    - "Push Manifest button only appears when manifest is out-of-date or never pushed"
    - "Push button shows PR status link when a PR already exists"
    - "PR is the only manifest push method — no direct push option exists anywhere"
  artifacts:
    - path: "core/templates/core/components/nav_service.html"
      provides: "Service sidebar with Alpine.js active tab tracking"
    - path: "core/templates/core/services/_ci_tab.html"
      provides: "Consolidated CI workflow management card"
    - path: "core/templates/core/services/_settings_tab.html"
      provides: "Settings tab without push method section"
    - path: "core/views/services.py"
      provides: "Views without ServiceUpdatePushMethodView"
    - path: "core/tasks.py"
      provides: "push_ci_manifest with PR-only logic"
  key_links:
    - from: "core/templates/core/components/nav_service.html"
      to: "core/templates/core/services/detail.html"
      via: "Alpine.js x-data tracks active tab from URL, updates on htmx:pushedIntoHistory"
      pattern: "x-data.*activeTab"
---

<objective>
Fix sidebar nav highlight for HTMX tab navigation, consolidate the CI Workflow tab into a single card with improved UX, and enforce PR-only manifest push flow.

Purpose: Improve service page navigation UX and simplify CI manifest delivery to PR-only.
Output: Updated service templates, views, model, and task code.
</objective>

<context>
@core/templates/core/components/nav_service.html
@core/templates/core/services/detail.html
@core/templates/core/services/_ci_tab.html
@core/templates/core/services/_settings_tab.html
@core/views/services.py
@core/models.py
@core/tasks.py
@core/urls.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix sidebar highlight and enforce PR-only manifest flow (backend)</name>
  <files>
    core/templates/core/components/nav_service.html
    core/templates/core/services/_settings_tab.html
    core/views/services.py
    core/urls.py
    core/models.py
    core/tasks.py
  </files>
  <action>
**1. Fix sidebar nav highlight (`nav_service.html`):**

The current sidebar uses `{% if request.GET.tab == 'ci' %}bg-dark-border{% endif %}` for highlighting. This breaks on HTMX tab switches because only `#tab-content` is swapped — the sidebar is never re-rendered.

Fix by wrapping the `<nav>` element with Alpine.js to track the active tab client-side:

- Add `x-data="{ activeTab: new URLSearchParams(window.location.search).get('tab') || 'details' }"` to the `<nav>` element.
- Add a listener for URL changes from HTMX: `@htmx:pushed-into-history.window="activeTab = new URLSearchParams(window.location.search).get('tab') || 'details'"` (note: HTMX fires `htmx:pushedIntoHistory` on the `window` — use the kebab-case Alpine event shorthand `htmx:pushed-into-history`).
- Replace each `{% if request.GET.tab == 'ci' %}bg-dark-border{% endif %}` pattern with Alpine binding. For example, the CI Workflow link becomes: `:class="activeTab === 'ci' ? 'bg-dark-border' : ''"` while keeping the static base classes `flex items-center px-3 py-2 rounded-lg text-dark-text hover:bg-dark-border/50 transition-colors`.
- For the "Details" link, the condition is `activeTab === 'details'` (which covers both `?tab=details` and no tab param since we default to `'details'`).
- Do the same for all 5 nav items: details, ci, builds, environments, settings.

IMPORTANT: Alpine.js in this project uses the CSP-compatible build (`alpine-csp.min.js`). This build does NOT support `x-data` with inline object expressions. Instead, define the component properly:
- Use `x-data` with a registered Alpine component via `Alpine.data()`, OR
- Use a simpler approach: since Alpine CSP build supports `x-init` with method references but NOT inline expressions, the safest approach is to use plain JavaScript with HTMX events instead of Alpine for this.

**Revised approach (no Alpine, pure JS + HTMX):** Add a small `<script>` block at the bottom of `nav_service.html` that:
1. On DOMContentLoaded: reads `window.location.search` to get current tab, applies `bg-dark-border` class to the matching nav link, removes it from others.
2. Listens to `htmx:pushedIntoHistory` on `window`: same logic — read new URL, update active classes.
3. Each nav `<a>` gets a `data-tab="details"`, `data-tab="ci"`, etc. attribute for easy selection.
4. Remove all the Django `{% if %}` highlight logic from the class attributes — the JS handles it entirely.

The function:
```
function updateSidebarHighlight() {
  var tab = new URLSearchParams(window.location.search).get('tab') || 'details';
  document.querySelectorAll('[data-service-nav]').forEach(function(el) {
    if (el.dataset.serviceNav === tab) {
      el.classList.add('bg-dark-border');
    } else {
      el.classList.remove('bg-dark-border');
    }
  });
}
```
Call on DOMContentLoaded and on `htmx:pushedIntoHistory`.

Add `data-service-nav="details"`, `data-service-nav="ci"`, etc. to each nav link. Use `nonce="{{ csp_nonce }}"` on the script tag.

**2. Remove push method from settings tab (`_settings_tab.html`):**

Delete the entire "CI Manifest Push Method" section (lines 74-106 in current file) — the `<div class="bg-dark-surface ...">` block with the radio buttons for PR vs Direct.

**3. Remove `ServiceUpdatePushMethodView` from views (`services.py`):**

Delete the entire `ServiceUpdatePushMethodView` class (lines 809-819). It is no longer needed.

**4. Remove push method URL (`urls.py`):**

Delete the URL pattern for `service_update_push_method` (the path with `ci/push-method/`). Also remove `ServiceUpdatePushMethodView` from the import statement at the top.

**5. Hardcode PR-only in model (`models.py`):**

Change the `ci_manifest_push_method` field: keep it in the model for now (avoids migration), but change the default and choices to ONLY `"pr"`. Update choices to `[("pr", "Pull Request")]` (single option). This is a non-breaking change that doesn't need a migration.

**6. Remove direct push logic from task (`tasks.py`):**

In the `push_ci_manifest` function, remove the `if service.ci_manifest_push_method == "direct":` branch entirely. Keep only the PR (else) branch as the sole code path. Remove the conditional — just execute the PR logic unconditionally. Keep the rest of the function intact.
  </action>
  <verify>
    Run `cd /Users/fandruhin/work/yourdevops/pathfinder && uv run python manage.py check --fail-level WARNING` to verify no Django errors.
    Run `cd /Users/fandruhin/work/yourdevops/pathfinder && uv run python -c "from core.views.services import *"` to verify imports work.
    Grep for `ServiceUpdatePushMethodView` in urls.py — should not exist.
    Grep for `service_update_push_method` in urls.py — should not exist.
    Grep for `direct` in tasks.py push_ci_manifest function — should not exist.
  </verify>
  <done>
    Sidebar highlight updates dynamically when switching tabs via HTMX.
    Push method setting removed from Settings tab.
    ServiceUpdatePushMethodView and its URL removed.
    push_ci_manifest only uses PR flow.
  </done>
</task>

<task type="auto">
  <name>Task 2: Consolidate CI Workflow tab into single card with improved UX</name>
  <files>
    core/templates/core/services/_ci_tab.html
    core/views/services.py
  </files>
  <action>
**Redesign `_ci_tab.html` to merge the 4 separate blocks (Assigned Workflow, Pinned Workflow Version, Manifest Status, Push to Repository) into ONE consolidated card.**

The new single card structure:

```
<div class="bg-dark-surface border border-dark-border rounded-lg">
  <!-- Card Header -->
  <div class="p-4 border-b border-dark-border">
    <h2 class="text-lg font-semibold text-dark-text">CI Workflow</h2>
    <p class="text-dark-muted text-sm mt-1">Manage the CI workflow assigned to this service.</p>
  </div>

  <div class="p-4 space-y-5">
    <!-- Row 1: Workflow selector -->
    <!-- Row 2: Version selector (only if workflow assigned) -->
    <!-- Row 3: Manifest status + Push button (only if workflow assigned) -->
  </div>
</div>
```

**Row 1 — Workflow** (label: "Workflow"):

If `can_edit`:
- A `<div>` with label "Workflow" (text-sm font-medium text-dark-text mb-1).
- A flex row with `<select>` dropdown (same options as current) and a Save button.
- The Save button should be HIDDEN by default and shown only when the user changes the select value. Use a small inline `<script>` block (with `nonce="{{ csp_nonce }}"`) that:
  - On the select's `change` event, compares `select.value` to a `data-initial` attribute on the select (set to the currently saved workflow id or empty).
  - If different, show the save button (remove `hidden` class). If same, hide it (add `hidden` class).
- The form action remains `{% url 'projects:service_assign_workflow' ... %}`.
- The save button has class `hidden` by default: `class="hidden px-3 py-1.5 text-sm bg-dark-accent hover:bg-dark-accent/80 text-white rounded transition-colors"` and an id like `id="workflow-save-btn"`.

If not `can_edit`: show the workflow name as read-only text (same as current).

**Row 2 — Version** (label: "Version", only shown if `service.ci_workflow`):

If `can_edit`:
- Label "Version" (text-sm font-medium text-dark-text mb-1).
- Flex row with version `<select>` and a Save button (hidden by default, shown on change).
- Same pattern: `data-initial="{{ service.ci_workflow_version_id|default:'' }}"` on the select, JS compares on change.
- Form action: `{% url 'projects:service_pin_version' ... %}`.
- If a version is pinned, show a small badge next to the label: `<span class="px-2 py-0.5 text-xs rounded bg-green-500/20 text-green-300">v{{ service.ci_workflow_version.version }}</span>`.

If not `can_edit`: show pinned version as read-only text.

**Row 3 — Manifest Status + Push** (only shown if `service.ci_workflow`):

A flex row (items-center justify-between) with:

Left side — Status display:
- The manifest status badge (same rendering logic as current: never_pushed=gray, synced=green, out_of_date=amber).
- If `ci_manifest_pushed_at`: "Last pushed: X ago" text.

Right side — Action area:
- If `ci_manifest_pr_url`: show "View Pull Request" link (blue, opens in new tab).
- If `can_edit` AND manifest is out-of-date or never-pushed (i.e., `ci_manifest_status != 'synced'` or `ci_manifest_out_of_date`): show the "Push Manifest" button as a form POST to `{% url 'projects:service_push_manifest' ... %}`.
- The Push button text: if `ci_manifest_pr_url` exists, label it "Update Pull Request" instead of "Push Manifest" (since there's an existing PR that will be updated).
- If manifest is synced and not out of date: no push button shown.

**Keep the Manifest Preview section below as a separate card** (unchanged from current).

**Update the view context** (`ServiceDetailView.get_context_data`, tab == "ci" branch):

The view already passes all needed context variables. No changes needed to the view UNLESS we need additional data. Check: we need `service.ci_workflow_version_id` for the `data-initial` attribute on the version select. The `service` object is already in context, so `{{ service.ci_workflow_version_id }}` works in template. No view changes needed for this task.

**Script for save-on-change behavior:**

At the bottom of `_ci_tab.html`, add a `<script nonce="{{ csp_nonce }}">` block:
```javascript
(function() {
  function setupChangeDetect(selectId, btnId) {
    var sel = document.getElementById(selectId);
    var btn = document.getElementById(btnId);
    if (!sel || !btn) return;
    var initial = sel.dataset.initial || '';
    sel.addEventListener('change', function() {
      if (sel.value !== initial) {
        btn.classList.remove('hidden');
      } else {
        btn.classList.add('hidden');
      }
    });
  }
  setupChangeDetect('workflow-select', 'workflow-save-btn');
  setupChangeDetect('version-select', 'version-save-btn');
})();
```

Add `id="workflow-select"` and `data-initial="{{ ci_workflow.id|default:'' }}"` to the workflow select.
Add `id="version-select"` and `data-initial="{{ service.ci_workflow_version_id|default:'' }}"` to the version select.
  </action>
  <verify>
    Run `cd /Users/fandruhin/work/yourdevops/pathfinder && make build` to rebuild static + collect.
    Run `cd /Users/fandruhin/work/yourdevops/pathfinder && uv run python manage.py check --fail-level WARNING` to verify no template issues.
    Visually inspect: the CI tab should show one card with Workflow selector, Version selector, and manifest status row.
  </verify>
  <done>
    CI Workflow tab has single consolidated card.
    Workflow selector labeled "Workflow" with save-on-change.
    Version selector labeled "Version" with save-on-change.
    Manifest status and push button in same card.
    Push button only shown when out-of-date/never-pushed.
    Push button label is context-aware (shows "Update Pull Request" when PR exists).
    Manifest Preview remains as separate card below.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    1. Sidebar nav highlight now follows active tab dynamically via JS + HTMX events
    2. CI Workflow tab consolidated into single card with Workflow/Version selectors and smart save/push buttons
    3. PR-only manifest push enforced (direct push removed from model, views, URLs, tasks, and settings UI)
  </what-built>
  <how-to-verify>
    1. Start the app: `make run` (in the pathfinder directory)
    2. Navigate to any service detail page (e.g., http://localhost:8000/projects/{project}/services/{service}/)
    3. Click each sidebar nav item (Details, CI Workflow, Builds, Environments, Settings) — verify the highlight moves to the clicked item each time
    4. On the CI Workflow tab:
       a. Verify single consolidated card with "Workflow" and "Version" sections
       b. Change the workflow dropdown — Save button should appear. Change back — Save button should hide
       c. Change the version dropdown — Save button should appear. Change back — Save button should hide
       d. If manifest is out of date, Push Manifest button should be visible
       e. If a PR exists, button should say "Update Pull Request" and PR link should be visible
    5. On the Settings tab: verify "CI Manifest Push Method" section is gone
    6. Try navigating to `/projects/{project}/services/{service}/ci/push-method/` — should return 404
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<verification>
- `uv run python manage.py check` passes
- No references to `ServiceUpdatePushMethodView` in urls.py or views imports
- No references to `service_update_push_method` URL name in any template
- `push_ci_manifest` in tasks.py has no `direct` push branch
- Sidebar highlight updates on every HTMX tab switch
</verification>

<success_criteria>
1. Sidebar navigation highlight follows the active tab when switching via HTMX clicks
2. CI Workflow tab shows one consolidated card with Workflow, Version, and Manifest Status sections
3. Save buttons appear only on value change
4. Push Manifest button appears only when manifest is out-of-date or never pushed
5. Push button label reflects PR awareness
6. No direct push option exists anywhere in the application
7. All Django checks pass
</success_criteria>

<output>
After completion, create `.planning/quick/37-service-ui-sidebar-highlight-ci-workflow/037-SUMMARY.md`
</output>
