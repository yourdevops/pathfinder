---
phase: quick-028
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
files_modified:
  - theme/templates/base.html
  - core/templates/core/projects/create_modal.html
  - core/templates/core/projects/env_var_modal.html
  - core/templates/core/projects/add_member_modal.html
  - core/templates/core/users/list.html
  - core/templates/core/services/_settings_tab.html
  - core/templates/core/ci_workflows/workflow_detail.html
  - core/templates/core/groups/detail.html
  - core/templates/core/connections/detail.html
  - core/templates/core/projects/_settings_tab.html
  - core/templates/core/projects/environment_detail.html
  - core/templates/core/projects/_services_tab.html
  - core/templates/core/services/wizard/step_configuration.html

must_haves:
  truths:
    - "No inline onclick/onsubmit/onchange handlers remain in any template"
    - "All modals open, close (X, Cancel, backdrop, Escape) correctly"
    - "All delete confirmations still prompt before submitting"
    - "Service row click navigation still works"
    - "Wizard env var add/remove/edit still works"
    - "Copy manifest button still works"
  artifacts:
    - path: "theme/templates/base.html"
      provides: "Global data-confirm submit listener and generic closeModal handler"
      contains: "data-confirm"
    - path: "core/templates/core/projects/create_modal.html"
      provides: "CSP-safe modal using Alpine directives"
      contains: "@click"
  key_links:
    - from: "theme/templates/base.html"
      to: "all forms with data-confirm"
      via: "global submit event listener"
      pattern: "addEventListener.*submit"
---

<objective>
Eliminate all CSP-violating inline event handlers across 13 template files, replacing them with Alpine.js directives, data attributes, and addEventListener patterns.

Purpose: The strict CSP policy (`script-src: 'self' 'nonce-...'`) blocks all inline handlers. These violations break modal close buttons, delete confirmations, row navigation, wizard interactions, and the copy manifest button.

Output: Zero inline event handlers remaining. All interactive behavior preserved via CSP-compliant patterns.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@docs/csp-violations-audit.md
@core/templates/core/connections/_attach_modal.html (reference pattern)
@theme/templates/base.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add global data-confirm listener and generic closeModal to base.html</name>
  <files>theme/templates/base.html</files>
  <action>
In the existing nonce'd script block at the bottom of base.html (lines 57-62):

1. Add a global `submit` event listener for `data-confirm` forms:
```javascript
document.addEventListener("submit", function(e) {
    var msg = e.target.dataset.confirm;
    if (msg && !confirm(msg)) e.preventDefault();
});
```

2. Update the existing `closeModal` listener to be generic -- remove all modal overlays, not just `#attach-modal`. Change:
```javascript
document.getElementById("attach-modal")?.remove();
```
to:
```javascript
document.querySelectorAll('.fixed.inset-0.z-50').forEach(function(el) { el.remove(); });
```
This ensures HX-Trigger: closeModal works for ALL modals (create-project, env-var, add-member, etc.), not just attach-modal.
  </action>
  <verify>Inspect base.html -- the nonce'd script block should contain both the data-confirm listener and the generic closeModal handler. No inline handlers in base.html.</verify>
  <done>base.html has global data-confirm submit listener and generic closeModal handler. Zero inline handlers.</done>
</task>

<task type="auto">
  <name>Task 2: Convert Category 1 modal close buttons (3 files, 9 onclick handlers)</name>
  <files>
    core/templates/core/projects/create_modal.html
    core/templates/core/projects/env_var_modal.html
    core/templates/core/projects/add_member_modal.html
  </files>
  <action>
Apply the same pattern as `_attach_modal.html` to all three modals. For each file:

**create_modal.html** (`#create-project-modal`):
- Line 2: Add `x-data @keydown.escape.window="$el.remove()"` to the outer `<div id="create-project-modal">`
- Line 3: Replace `onclick="this.parentElement.remove()"` on backdrop div with `@click="$el.closest('#create-project-modal').remove()"`
- Line 10: Replace `onclick="this.closest('#create-project-modal').remove()"` on X button with `@click="$el.closest('#create-project-modal').remove()"`
- Line 49: Replace `onclick="this.closest('#create-project-modal').remove()"` on Cancel button with `@click="$el.closest('#create-project-modal').remove()"`

**env_var_modal.html** (`#env-var-modal`):
- Line 2: Add `x-data @keydown.escape.window="$el.remove()"` to outer `<div id="env-var-modal">`
- Line 4: Replace `onclick="this.parentElement.remove()"` on overlay div with `@click="$el.closest('#env-var-modal').remove()"`
- Line 14: Replace `onclick="this.closest('#env-var-modal').remove()"` on X button with `@click="$el.closest('#env-var-modal').remove()"`
- Line 68: Replace `onclick="this.closest('#env-var-modal').remove()"` on Cancel button with `@click="$el.closest('#env-var-modal').remove()"`

**add_member_modal.html** (`#add-member-modal`):
- Line 2: Add `x-data @keydown.escape.window="$el.remove()"` to outer `<div id="add-member-modal">`
- Line 4: Replace `onclick="this.parentElement.remove()"` on overlay div with `@click="$el.closest('#add-member-modal').remove()"`
- Line 12: Replace `onclick="this.closest('#add-member-modal').remove()"` on X button with `@click="$el.closest('#add-member-modal').remove()"`
- Line 55: Replace `onclick="this.closest('#add-member-modal').remove()"` on Cancel button with `@click="$el.closest('#add-member-modal').remove()"`

IMPORTANT: Use Alpine CSP build syntax. The project uses `alpine-csp.min.js` which means `x-data` expression evaluation works via the CSP-compatible build. The `$el` magic property and `.remove()` / `.closest()` are native DOM calls, which work fine with the CSP build.
  </action>
  <verify>grep -rn "onclick" in all three files should return zero results. Each file should have `x-data`, `@keydown.escape.window`, and `@click` directives.</verify>
  <done>All 9 onclick handlers across 3 modal files replaced with Alpine @click directives. Escape key closes modals.</done>
</task>

<task type="auto">
  <name>Task 3: Convert Category 2 users list modal (toggle hidden pattern to Alpine x-show)</name>
  <files>core/templates/core/users/list.html</files>
  <action>
This modal uses `document.getElementById('createModal').classList.remove/add('hidden')` pattern with 3 inline onclick handlers (lines 9, 84, 142). Convert to Alpine:

1. Wrap the entire block content in an Alpine scope. Add `x-data="{ showCreateModal: false }"` to the outermost `<div class="p-8">` (line 6).

2. Line 9: Replace `onclick="document.getElementById('createModal').classList.remove('hidden')"` on the "Create User" button with `@click="showCreateModal = true"`.

3. Line 80: On the modal outer div `<div id="createModal" class="fixed inset-0 bg-black/50 ...">`:
   - Replace `{% if not show_modal %}hidden{% endif %}` with `x-show="showCreateModal" x-cloak`
   - Add `@keydown.escape.window="showCreateModal = false"`
   - Keep the `id="createModal"` for backwards compat but it is no longer functionally needed.
   - Handle server-side `show_modal` context: add `x-init="showCreateModal = {{ show_modal|yesno:'true,false' }}"` so that when form has errors, the modal re-opens.

4. Line 84: Replace `onclick="document.getElementById('createModal').classList.add('hidden')"` on X button with `@click="showCreateModal = false"`.

5. Line 142: Replace `onclick="document.getElementById('createModal').classList.add('hidden')"` on Cancel button with `@click="showCreateModal = false"`.

6. Also fix the Category 3 violation in this same file -- line 59: Replace `onsubmit="return confirm('Are you sure you want to delete {{ user.username }}?')"` with `data-confirm="Are you sure you want to delete {{ user.username }}?"` (the global listener from Task 1 handles it).

NOTE on Alpine CSP build: The CSP build does NOT support inline expressions in `x-data` like `x-data="{ showCreateModal: false }"`. Instead, you must register the component data via `Alpine.data()` in a nonce'd script. Add a script block at the bottom of the template:

```html
<script nonce="{{ csp_nonce }}">
document.addEventListener('alpine:init', () => {
    Alpine.data('userListPage', () => ({
        showCreateModal: {{ show_modal|yesno:"true,false" }},
    }));
});
</script>
```

Then use `x-data="userListPage"` on the outer div. Use `x-show="showCreateModal"` and `@click="showCreateModal = true"` etc. -- these reference properties, not inline expressions, so the CSP build handles them.

WAIT -- actually check the existing `_attach_modal.html` reference: it uses bare `x-data` (no expression) with `$el.remove()` in the directives. The CSP build allows calling methods on `$el` because those are native DOM operations, not evaluated expressions. But `x-data="{ showCreateModal: false }"` IS an expression that the CSP build cannot evaluate.

Simpler approach: Use the same pattern as the other modals -- just use `x-data` (bare) with `x-ref` and toggle via a CSS class or remove/add. But this modal is different because it lives in the page (not HTMX-loaded), so we cannot use `.remove()`.

REVISED APPROACH -- use Alpine `$store` or a separate `<template>` approach. Actually the simplest CSP-safe approach:

Add to the nonce'd script block:
```javascript
document.addEventListener('alpine:init', () => {
    Alpine.store('createModal', { open: {{ show_modal|yesno:"true,false" }} });
});
```

Then:
- Outer div: `x-data` (bare, to enable Alpine on descendants)
- "Create User" button: `@click="$store.createModal.open = true"`
- Modal div: `x-show="$store.createModal.open"` with `x-cloak` and `@keydown.escape.window="$store.createModal.open = false"`
- X button: `@click="$store.createModal.open = false"`
- Cancel button: `@click="$store.createModal.open = false"`

`$store` access is a property lookup, not expression evaluation, so it works with the CSP build.

Add `x-cloak` style if not already present. Check if base.html or tailwind includes `[x-cloak] { display: none !important; }`. If not, add it to base.html `<head>`.
  </action>
  <verify>grep -n "onclick\|onsubmit" core/templates/core/users/list.html should return zero. The "Create User" button should open the modal, X/Cancel/Escape should close it. Delete user forms should have data-confirm attributes.</verify>
  <done>Users list page uses Alpine $store for modal toggle. Delete confirmation uses data-confirm. Zero inline handlers.</done>
</task>

<task type="auto">
  <name>Task 4: Convert Category 3 delete confirmations (10 remaining onsubmit handlers across 6 files)</name>
  <files>
    core/templates/core/services/_settings_tab.html
    core/templates/core/ci_workflows/workflow_detail.html
    core/templates/core/groups/detail.html
    core/templates/core/connections/detail.html
    core/templates/core/projects/_settings_tab.html
    core/templates/core/projects/environment_detail.html
  </files>
  <action>
For each file, replace `onsubmit="return confirm('...')"` with `data-confirm="..."` on the form element. The global listener added in Task 1 handles the rest.

Specific replacements:

1. **services/_settings_tab.html** line 54:
   `onsubmit="return confirm('Are you sure you want to delete this service? This action cannot be undone.')"`
   -> `data-confirm="Are you sure you want to delete this service? This action cannot be undone."`

2. **ci_workflows/workflow_detail.html** line 42:
   `onsubmit="return confirm('Are you sure you want to delete this workflow?')"`
   -> `data-confirm="Are you sure you want to delete this workflow?"`

3. **groups/detail.html** line 22:
   `onsubmit="return confirm('Are you sure you want to delete this group?')"`
   -> `data-confirm="Are you sure you want to delete this group?"`

4. **groups/detail.html** line 94:
   `onsubmit="return confirm('Remove {{ membership.user.username }} from this group?')"`
   -> `data-confirm="Remove {{ membership.user.username }} from this group?"`

5. **connections/detail.html** line 329:
   `onsubmit="return confirm('Are you sure you want to delete this connection? This action cannot be undone.')"`
   -> `data-confirm="Are you sure you want to delete this connection? This action cannot be undone."`

6. **projects/_settings_tab.html** line 195:
   `onsubmit="return confirm('Remove {{ membership.group.name }} from this project?')"`
   -> `data-confirm="Remove {{ membership.group.name }} from this project?"`

7. **projects/_settings_tab.html** line 228:
   `onsubmit="return confirm('Remove {{ membership.group.name }} from this project?')"`
   -> `data-confirm="Remove {{ membership.group.name }} from this project?"`

8. **projects/_settings_tab.html** line 261:
   `onsubmit="return confirm('Remove {{ membership.group.name }} from this project?')"`
   -> `data-confirm="Remove {{ membership.group.name }} from this project?"`

9. **projects/_settings_tab.html** line 306:
   `onsubmit="return confirm('Are you sure you want to archive this project? This action can be undone by an administrator.')"`
   -> `data-confirm="Are you sure you want to archive this project? This action can be undone by an administrator."`

10. **projects/environment_detail.html** line 244:
    `onsubmit="return confirm('Are you sure you want to delete this environment? This action cannot be undone.')"`
    -> `data-confirm="Are you sure you want to delete this environment? This action cannot be undone."`

This is a pure search-and-replace within each form tag. Do NOT change any other attributes on the form elements.
  </action>
  <verify>grep -rn "onsubmit" across all listed files should return zero results. grep -rn "data-confirm" should show 10 instances in these 6 files (plus 1 in users/list.html from Task 3).</verify>
  <done>All 10 onsubmit handlers replaced with data-confirm attributes. Confirmation dialogs fire via global listener.</done>
</task>

<task type="auto">
  <name>Task 5: Convert Category 4 row click + Category 6 copy manifest button</name>
  <files>
    core/templates/core/projects/_services_tab.html
    core/templates/core/ci_workflows/workflow_detail.html
  </files>
  <action>
**Category 4 -- _services_tab.html line 30:**
Replace `onclick="window.location='{% url 'projects:service_detail' project_name=project.name service_name=service.name %}'"` on the `<tr>` with Alpine `@click` directive:
```html
<tr class="hover:bg-dark-border/30 cursor-pointer" x-data
    @click="window.location.href = '{% url 'projects:service_detail' project_name=project.name service_name=service.name %}'">
```

WAIT -- the CSP build cannot evaluate `window.location.href = '...'` as an expression. Use event delegation instead.

REVISED: Add a `data-href` attribute to the `<tr>` and use a global click listener in base.html (or a nonce'd script at bottom of the template):

On the `<tr>`:
```html
<tr class="hover:bg-dark-border/30 cursor-pointer"
    data-href="{% url 'projects:service_detail' project_name=project.name service_name=service.name %}">
```

Remove the `onclick` entirely. Then add to base.html's nonce'd script block:
```javascript
document.addEventListener("click", function(e) {
    var row = e.target.closest("tr[data-href]");
    if (row && !e.target.closest("a, button")) {
        window.location.href = row.dataset.href;
    }
});
```

The `!e.target.closest("a, button")` guard prevents navigation when clicking the link inside the row (which has its own navigation).

**Category 6 -- workflow_detail.html line 131:**
Remove `onclick="copyManifest()"` from the button. Add an `id` attribute (it already has `id="copy-btn"`). In the existing nonce'd `<script>` block at the bottom (line 144), add an event listener:

Change from:
```javascript
function copyManifest() { ... }
```
to:
```javascript
function copyManifest() {
    const yamlContent = document.getElementById('manifest-yaml').textContent;
    navigator.clipboard.writeText(yamlContent).then(() => {
        const btn = document.getElementById('copy-text');
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy to Clipboard'; }, 2000);
    });
}
document.getElementById('copy-btn').addEventListener('click', copyManifest);
```

And remove `onclick="copyManifest()"` from the button element on line 131.
  </action>
  <verify>grep -n "onclick" in both files should return zero results. Service row clicks should navigate. Copy manifest button should copy YAML and show "Copied!" feedback.</verify>
  <done>Row click uses data-href with global listener. Copy button uses addEventListener. Zero inline handlers in both files.</done>
</task>

<task type="auto">
  <name>Task 6: Convert Category 5 dynamic inline handlers in wizard step_configuration.html</name>
  <files>core/templates/core/services/wizard/step_configuration.html</files>
  <action>
The `renderEnvVars()` function (line 66-89) builds HTML via template literals with inline `onchange` and `onclick` handlers that CSP blocks when inserted via `innerHTML`. Refactor to use event delegation.

Replace the entire `renderEnvVars` function. Instead of putting `onchange="updateEnvVar(${i}, 'key', this.value)"` and `onclick="removeEnvVar(${i})"` in the generated HTML, use `data-` attributes and event delegation:

1. In the generated HTML template, replace:
   - `onchange="updateEnvVar(${i}, 'key', this.value)"` with `data-action="update-key" data-index="${i}"`
   - `onchange="updateEnvVar(${i}, 'value', this.value)"` with `data-action="update-value" data-index="${i}"`
   - `onclick="removeEnvVar(${i})"` with `data-action="remove" data-index="${i}"`

2. Add event delegation on the container after the `renderEnvVars` function definition:

```javascript
const container = document.getElementById('env-vars-container');

container.addEventListener('change', function(e) {
    var idx = parseInt(e.target.dataset.index);
    if (e.target.dataset.action === 'update-key') {
        updateEnvVar(idx, 'key', e.target.value);
    } else if (e.target.dataset.action === 'update-value') {
        updateEnvVar(idx, 'value', e.target.value);
    }
});

container.addEventListener('click', function(e) {
    var btn = e.target.closest('[data-action="remove"]');
    if (btn) {
        removeEnvVar(parseInt(btn.dataset.index));
    }
});
```

3. Move the `const container` declaration to the top of the script (before `renderEnvVars`) so it can be shared. The existing `renderEnvVars` function already references `document.getElementById('env-vars-container')` -- replace that with the shared `container` variable.

4. The `button type="button"` for remove should keep its classes but lose the `onclick`. Use `data-action="remove" data-index="${i}"` on it.

Full revised `renderEnvVars` innerHTML template:
```javascript
row.innerHTML = `
    <input type="text" value="${v.key}" placeholder="KEY"
           class="flex-1 px-2 py-1 bg-dark-surface border border-dark-border rounded text-dark-text text-sm font-mono"
           data-action="update-key" data-index="${i}">
    <span class="text-dark-muted">=</span>
    <input type="text" value="${v.value}" placeholder="value"
           class="flex-1 px-2 py-1 bg-dark-surface border border-dark-border rounded text-dark-text text-sm"
           data-action="update-value" data-index="${i}">
    <button type="button" data-action="remove" data-index="${i}"
            class="p-1 text-dark-muted hover:text-red-400 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
    </button>
`;
```
  </action>
  <verify>grep -n "onclick\|onchange" core/templates/core/services/wizard/step_configuration.html should return zero results. Navigate to the service creation wizard, step to Configuration, add/edit/remove env vars -- all interactions should work.</verify>
  <done>Wizard env var interactions use event delegation via data-action/data-index attributes. Zero inline handlers in generated HTML.</done>
</task>

<task type="auto">
  <name>Task 7: Add x-cloak CSS and final verification sweep</name>
  <files>theme/templates/base.html</files>
  <action>
1. Check if `[x-cloak]` style exists anywhere (base.html, tailwind config, or CSS files). If NOT present, add to base.html `<head>` section:
```html
<style nonce="{{ csp_nonce }}">[x-cloak] { display: none !important; }</style>
```
This prevents the users list modal from flashing on page load before Alpine initializes.

2. Run a final grep across ALL template files to confirm zero inline event handlers remain:
```bash
grep -rn "onclick\|onsubmit\|onchange\|onkeydown\|onkeyup\|onmouseover\|onfocus\|onblur" core/templates/ theme/templates/
```
Any remaining hits must be addressed.
  </action>
  <verify>The grep command above returns zero results. The x-cloak style is present (either in CSS or base.html).</verify>
  <done>x-cloak prevents modal flash. Zero inline event handlers across entire template codebase.</done>
</task>

</tasks>

<verification>
Run a comprehensive grep to confirm no inline handlers remain:
```bash
grep -rn 'onclick=\|onsubmit=\|onchange=\|onkeydown=\|onload=' core/templates/ theme/templates/
```
Expected: zero results.

Start the dev server (`make run`) and test:
1. Projects page: Create Project modal opens/closes (X, Cancel, backdrop, Escape)
2. Environment variables modal opens/closes
3. Add Group modal opens/closes
4. Users page: Create User modal opens/closes; delete user shows confirm dialog
5. Groups detail: delete group and remove member show confirm dialogs
6. Connections detail: delete connection shows confirm dialog
7. Project settings: remove group members and archive project show confirm dialogs
8. Services tab: clicking a service row navigates to detail page
9. Service wizard: can add, edit, remove env vars in configuration step
10. CI Workflow detail: copy manifest button copies YAML and shows "Copied!"
</verification>

<success_criteria>
- Zero inline event handlers (onclick, onsubmit, onchange) in any template file
- All modal open/close interactions work (Alpine @click, @keydown.escape, $store)
- All delete confirmations prompt via data-confirm + global listener
- Service row navigation works via data-href + global listener
- Wizard env var CRUD works via event delegation
- Copy manifest works via addEventListener
- No CSP violations in browser console
</success_criteria>

<output>
After completion, create `.planning/quick/028-address-csp-violation-findings/028-SUMMARY.md`
</output>
