---
phase: quick
plan: 030
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/components/_confirm_modal.html
  - theme/templates/base.html
  - core/views/ci_workflows.py
  - core/urls.py
  - core/templates/core/ci_workflows/repo_detail.html
  - core/templates/core/ci_workflows/workflow_detail.html
autonomous: true

must_haves:
  truths:
    - "Repo detail shows which workflows use steps from this repo with clickable links"
    - "Repo can be deleted only when no workflows reference its steps"
    - "Workflow can be deleted only when no services use it"
    - "Deletion triggers a styled confirmation modal, not browser confirm()"
    - "Modal closes on Escape, backdrop click, or Cancel button"
    - "Zero CSP violations in browser console"
    - "Existing data-confirm forms on other pages still work"
  artifacts:
    - path: "core/templates/core/components/_confirm_modal.html"
      provides: "Reusable confirmation modal partial"
    - path: "core/views/ci_workflows.py"
      provides: "StepsRepoDeleteView, updated StepsRepoDetailView, updated WorkflowDetailView/WorkflowDeleteView"
    - path: "core/urls.py"
      provides: "repo_delete URL pattern"
  key_links:
    - from: "repo_detail.html"
      to: "_confirm_modal.html"
      via: "{% include with confirm_action=repo_delete_url %}"
    - from: "workflow_detail.html"
      to: "_confirm_modal.html"
      via: "{% include with confirm_action=workflow_delete_url %}"
    - from: "base.html"
      to: "_confirm_modal.html"
      via: "data-confirm-modal click delegation + .confirm-modal-close + backdrop + Escape"
---

<objective>
Add usage tracking and safe deletion for CI Steps Repositories and CI Workflows, with a reusable CSP-safe confirmation modal component.

Purpose: Users need visibility into dependency chains (which workflows use a repo's steps, which services use a workflow) and safe deletion guarded by those dependencies, using styled modals instead of browser confirm() dialogs.
Output: Reusable modal partial, global modal handlers, repo delete view+URL, updated repo detail and workflow detail pages.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docs/plan-usage-tracking-deletion-modal.md
@core/views/ci_workflows.py
@core/urls.py
@theme/templates/base.html
@core/templates/core/ci_workflows/repo_detail.html
@core/templates/core/ci_workflows/workflow_detail.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Modal infrastructure — reusable partial + global handlers</name>
  <files>
    core/templates/core/components/_confirm_modal.html
    theme/templates/base.html
  </files>
  <action>
1. Create NEW file `core/templates/core/components/_confirm_modal.html` — a reusable confirmation modal partial using `{% include ... with %}` template variables:
   - `confirm_id` — unique HTML id (e.g. "confirm-delete-repo")
   - `confirm_title` — heading text
   - `confirm_message` — body text
   - `confirm_action` — form POST URL (must be a context variable, not {% url %})
   - `confirm_button_text` — submit label (defaults to "Delete" via `|default:"Delete"`)

   Structure: outer `fixed inset-0 z-50 flex items-center justify-center hidden`, backdrop with `confirm-modal-backdrop` class, panel with `bg-dark-surface border border-dark-border rounded-lg shadow-xl w-full max-w-md mx-4`, title+message in p-6, action buttons in flex justify-end gap-3 p-4 border-t. Cancel button has class `confirm-modal-close`. Form with method="post" action="{{ confirm_action }}" containing {% csrf_token %} and red submit button. Close X button in header also has `confirm-modal-close` class. No Alpine needed — pure CSS hidden class toggling.

   See exact HTML in docs/plan-usage-tracking-deletion-modal.md Task 1.

2. Edit `theme/templates/base.html` — add two event listeners AFTER the existing `data-href` handler (after the click handler for `tr[data-href]`), BEFORE `</script>`:

   a. Click handler for `data-confirm-modal` attribute (opens modal by removing `hidden`), `.confirm-modal-close` buttons (closes by adding `hidden`), and `.confirm-modal-backdrop` clicks (closes by adding `hidden`).

   b. Keydown handler for Escape key — closes all visible `.fixed.inset-0.z-50:not(.hidden)` elements.

   See exact JavaScript in docs/plan-usage-tracking-deletion-modal.md Task 2.

   IMPORTANT: Do NOT remove the existing `data-confirm` handler (submit event listener with `confirm()` call) — 11 other templates use it.
  </action>
  <verify>
    - `_confirm_modal.html` exists and contains `confirm_id`, `confirm_action`, `csrf_token`
    - `base.html` contains `data-confirm-modal` handler AND still contains original `data-confirm` handler
    - `uv run python manage.py check` passes
  </verify>
  <done>Reusable modal partial created; global open/close/escape handlers added to base.html; existing data-confirm behavior preserved.</done>
</task>

<task type="auto">
  <name>Task 2: Backend — StepsRepoDeleteView + URL + view context updates</name>
  <files>
    core/views/ci_workflows.py
    core/urls.py
  </files>
  <action>
1. In `core/views/ci_workflows.py`, add `StepsRepoDeleteView` after `StepsRepoScanStatusView` (around line 165):
   - Class inherits `OperatorRequiredMixin, View`
   - POST handler: get_object_or_404(StepsRepository, name=repo_name), check `CIWorkflowStep.objects.filter(step__repository=repo).exists()` — if true, `messages.error()` and redirect to repo_detail; otherwise `repo.delete()` and redirect to repo_list.
   - Add `from django.contrib import messages` if not already imported.

2. In `core/urls.py`, add URL pattern after `repo_scan_status`:
   `path("repos/<dns:repo_name>/delete/", StepsRepoDeleteView.as_view(), name="repo_delete")`
   Add `StepsRepoDeleteView` to the imports from ci_workflows views.

3. Modify `StepsRepoDetailView.get()` — before the `return render(...)`, add:
   ```python
   workflows_using = (
       CIWorkflow.objects.filter(workflow_steps__step__repository=repo)
       .distinct()
       .order_by("name")
   )
   can_delete = can_manage and not workflows_using.exists()
   ```
   Add to context dict: `"workflows_using": workflows_using`, `"can_delete": can_delete`, `"repo_delete_url": reverse("ci_workflows:repo_delete", kwargs={"repo_name": repo.name})`.
   Add `from django.urls import reverse` if not already imported.

4. Modify `WorkflowDetailView.get()` — change `can_delete` logic to:
   ```python
   is_operator = request.user.is_authenticated and (
       has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
   )
   can_delete = is_operator and not services_using.exists()
   ```
   Add to context: `"workflow_delete_url": reverse("ci_workflows:workflow_delete", kwargs={"workflow_name": workflow.name})`

5. Modify `WorkflowDeleteView.post()` — add server-side guard: if `workflow.services.exists()`, `messages.error()` and redirect to workflow_detail; otherwise delete and redirect to workflow_list.
  </action>
  <verify>
    - `uv run python manage.py check` passes
    - `uv run python manage.py shell -c "from core.views.ci_workflows import StepsRepoDeleteView; print('OK')"` succeeds
    - grep confirms `repo_delete` in urls.py
  </verify>
  <done>StepsRepoDeleteView exists with server-side guard; repo_delete URL registered; StepsRepoDetailView passes workflows_using and can_delete to context; WorkflowDetailView guards can_delete by services_using; WorkflowDeleteView has server-side guard.</done>
</task>

<task type="auto">
  <name>Task 3: Templates — repo detail usage section + workflow detail modal integration</name>
  <files>
    core/templates/core/ci_workflows/repo_detail.html
    core/templates/core/ci_workflows/workflow_detail.html
  </files>
  <action>
1. In `repo_detail.html`:
   a. In the header area (inside `flex items-center gap-3`, after the Rescan form), add a conditional delete button:
      `{% if can_delete %}` — button with `type="button" data-confirm-modal="confirm-delete-repo"` and red styling (`bg-red-500/20 hover:bg-red-500/30 text-red-400`).

   b. Between "Runtime Families" section and "Imported Steps" section, add "Workflows Using Steps" section:
      `{% if workflows_using %}` — div with h2 showing count, then a list of linked workflow names in `bg-dark-surface border border-dark-border rounded-lg divide-y divide-dark-border`. Each item is an `<a>` to `{% url 'ci_workflows:workflow_detail' workflow_name=wf.name %}` showing `wf.name` and truncated `wf.description`.

   c. At end of content block (before closing `</div>` of `p-8`), add modal include:
      `{% if can_delete %}{% include "core/components/_confirm_modal.html" with confirm_id="confirm-delete-repo" confirm_title="Delete Repository" confirm_message="Are you sure you want to delete this repository and all its imported steps? This cannot be undone." confirm_action=repo_delete_url confirm_button_text="Delete Repository" %}{% endif %}`

   See exact HTML in docs/plan-usage-tracking-deletion-modal.md Task 4.

2. In `workflow_detail.html`:
   a. Replace the existing `data-confirm` delete form (the form with `method="post"` and `data-confirm` attribute around lines 40-49) with a conditional button:
      `{% if can_delete %}` — button with `type="button" data-confirm-modal="confirm-delete-workflow"` and red styling.

   b. Before closing `</div>` of `p-8`, add modal include:
      `{% if can_delete %}{% include "core/components/_confirm_modal.html" with confirm_id="confirm-delete-workflow" confirm_title="Delete Workflow" confirm_message="Are you sure you want to delete this workflow? This cannot be undone." confirm_action=workflow_delete_url confirm_button_text="Delete Workflow" %}{% endif %}`

   See exact HTML in docs/plan-usage-tracking-deletion-modal.md Task 5.
  </action>
  <verify>
    - grep confirms `data-confirm-modal` in both template files
    - grep confirms `_confirm_modal.html` include in both template files
    - grep confirms `workflows_using` in repo_detail.html
    - `uv run python manage.py check` passes
    - Rebuild UI: `uv run python manage.py tailwind build && uv run python manage.py collectstatic --noinput`
  </verify>
  <done>Repo detail shows "Workflows Using Steps" section with linked names; delete button appears only when can_delete is true; workflow detail uses modal instead of browser confirm(); both pages include the reusable modal partial.</done>
</task>

</tasks>

<verification>
1. `uv run python manage.py check` — no errors
2. `make run` — server starts without errors
3. Navigate to Steps Repositories > click a repo:
   - "Workflows Using Steps" section appears with linked workflow names (if any)
   - Delete button visible only if no workflows reference repo steps
   - Click delete -> styled modal appears -> confirm -> repo deleted -> redirect to repo list
4. Navigate to Workflows > click a workflow:
   - Delete button visible only if no services use it
   - Click delete -> styled modal -> confirm -> deleted -> redirect to workflow list
5. Escape key and backdrop click close modals
6. Browser console: zero CSP errors
7. Other pages with `data-confirm` forms still work (e.g. groups detail)
</verification>

<success_criteria>
- Reusable `_confirm_modal.html` partial works via include-with pattern
- Global modal handlers in base.html (open, close, escape) work without Alpine or inline JS
- Repo detail shows workflow usage with links; deletion guarded by usage
- Workflow detail deletion guarded by service usage
- Server-side guards on both delete views prevent circumvention
- Zero CSP violations
- Existing `data-confirm` behavior on 11 other templates unaffected
</success_criteria>

<output>
After completion, create `.planning/quick/030-usage-tracking-deletion-modal/030-SUMMARY.md`
</output>
