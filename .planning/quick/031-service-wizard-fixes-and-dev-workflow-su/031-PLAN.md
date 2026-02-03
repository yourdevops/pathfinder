---
phase: quick-031
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/forms/services.py
  - core/views/services.py
  - core/templates/core/services/wizard/step_repository.html
  - core/templates/core/services/wizard/step_workflow.html
  - core/templates/core/services/wizard/step_review.html
  - core/models.py
  - core/migrations/0015_ciworkflow_dev_workflow.py
  - core/forms/ci_workflows.py
  - core/templates/core/ci_workflows/workflow_create.html
  - core/templates/core/ci_workflows/workflow_detail.html
autonomous: true

must_haves:
  truths:
    - "Step 2 auto-selects project's default SCM connection"
    - "Branch field shows 'Main Branch' for new repos, 'Base Branch' for existing repos"
    - "Configuration step (env vars) is now Step 4, Workflow selection is Step 3"
    - "Step 3 shows workflow details preview when selected"
    - "Step 3 has 'View all workflows' link opening in new tab"
    - "Service can be saved in Draft state without CI Workflow with warning"
    - "CIWorkflow model has dev_workflow field (trunk_based default)"
    - "Workflow detail and service wizard show Development Workflow info with trunkbaseddevelopment.com link"
  artifacts:
    - path: "core/forms/services.py"
      provides: "Updated wizard forms with step reordering and auto-select"
    - path: "core/views/services.py"
      provides: "Wizard views with swapped step order and workflow details context"
    - path: "core/templates/core/services/wizard/step_repository.html"
      provides: "Dynamic branch label based on repo mode"
    - path: "core/templates/core/services/wizard/step_workflow.html"
      provides: "Workflow preview, view all link, refresh button, draft warning"
    - path: "core/models.py"
      provides: "CIWorkflow.dev_workflow field"
    - path: "core/migrations/0015_ciworkflow_dev_workflow.py"
      provides: "Migration for dev_workflow field"
---

<objective>
Fix Service creation wizard UX issues and add Development Workflow support to CI Workflows.

Purpose: Improve service creation flow by auto-selecting defaults, clarifying field labels, reordering steps logically, and adding Development Workflow tracking for future multi-workflow support.

Output: Updated wizard with better UX, CIWorkflow model with dev_workflow field, and updated detail views.
</objective>

<context>
@.planning/STATE.md
@core/forms/services.py
@core/views/services.py
@core/templates/core/services/wizard/step_repository.html
@core/templates/core/services/wizard/step_workflow.html
@core/models.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Repository step improvements and wizard step reordering</name>
  <files>
    core/forms/services.py
    core/views/services.py
    core/templates/core/services/wizard/step_repository.html
  </files>
  <action>
1. In `core/forms/services.py` - RepositoryStepForm:
   - In __init__, auto-select the default SCM connection (where `is_default=True`) if one exists for the project
   - Change branch label from static "Branch" to be set dynamically

2. In `core/views/services.py`:
   - Swap the wizard step order: Configuration (env vars) becomes step 4, Workflow selection becomes step 3
   - Update WIZARD_FORMS: `[("project", ...), ("repository", ...), ("workflow", ...), ("configuration", ...), ("review", ...)]`
   - Update WIZARD_TEMPLATES and STEP_TITLES accordingly
   - In get_form_kwargs for "workflow" step, pass project
   - Update _get_review_data to get data from correct step names

3. In `core/templates/core/services/wizard/step_repository.html`:
   - Update JavaScript to change label text dynamically:
     - When "Create new repository" selected: label shows "Main Branch"
     - When "Use existing repository" selected: label shows "Base Branch"
   - Update the label element to have an id (e.g., id="branch-label") so JS can target it
  </action>
  <verify>
    Run `uv run python manage.py check` - no errors
    Navigate to service creation wizard, verify:
    - SCM connection auto-selected if project has default
    - Branch label changes based on repo mode selection
    - Steps are in order: Service -> Repository -> CI Workflow -> Configuration -> Review
  </verify>
  <done>
    Wizard step order is project -> repository -> workflow -> configuration -> review.
    SCM connection auto-selects default.
    Branch label dynamically shows "Main Branch" or "Base Branch" based on mode.
  </done>
</task>

<task type="auto">
  <name>Task 2: Workflow step enhancements</name>
  <files>
    core/views/services.py
    core/templates/core/services/wizard/step_workflow.html
    core/templates/core/services/wizard/step_review.html
  </files>
  <action>
1. In `core/views/services.py` - get_context_data for "workflow" step:
   - Add `available_workflows` queryset to context for displaying in template
   - Pass `ci_workflows_url` pointing to `{% url 'ci_workflows:workflow_list' %}` for "View all workflows" link

2. In `core/templates/core/services/wizard/step_workflow.html`:
   - Add "View all workflows" link that opens in new tab (target="_blank") next to the dropdown label
   - Add a "Refresh" button that reloads the page (simple page refresh to re-fetch workflows)
   - Below the dropdown, add an Alpine.js or simple JS section that shows workflow details when one is selected:
     - Display: runtime_family, runtime_version, description, dev_workflow (after Task 3 adds it)
     - Use HTMX to fetch workflow details OR embed workflow data as JSON in template for client-side display
   - Add a warning banner (amber/yellow) when "No CI Workflow" is selected:
     - "Services without a CI Workflow will be saved in Draft status. A CI Workflow is required to transition to Active status."

3. In `core/templates/core/services/wizard/step_review.html`:
   - Add display for Development Workflow info (once Task 3 adds the field)
   - Show warning if no CI workflow selected: "Note: Service will be created in Draft status"
  </action>
  <verify>
    Navigate to Step 3 (Workflow) in service wizard:
    - "View all workflows" link opens workflow list in new tab
    - Refresh button reloads the page
    - Selecting a workflow shows its details (runtime, description)
    - Selecting "No CI Workflow" shows warning about Draft status
  </verify>
  <done>
    Workflow step has view-all link, refresh button, workflow details preview, and draft warning.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add Development Workflow field to CIWorkflow</name>
  <files>
    core/models.py
    core/migrations/0015_ciworkflow_dev_workflow.py
    core/forms/ci_workflows.py
    core/templates/core/ci_workflows/workflow_create.html
    core/templates/core/ci_workflows/workflow_detail.html
  </files>
  <action>
1. In `core/models.py` - CIWorkflow model:
   - Add `dev_workflow` field:
     ```python
     DEV_WORKFLOW_CHOICES = [
         ("trunk_based", "Trunk-Based Development"),
     ]
     dev_workflow = models.CharField(
         max_length=50,
         choices=DEV_WORKFLOW_CHOICES,
         default="trunk_based",
         help_text="Development workflow pattern"
     )
     ```

2. Create migration `core/migrations/0015_ciworkflow_dev_workflow.py`:
   - Run `uv run python manage.py makemigrations core --name ciworkflow_dev_workflow`

3. Apply migration:
   - Run `uv run python manage.py migrate`

4. In `core/forms/ci_workflows.py` - WorkflowCreateForm:
   - Add `dev_workflow` field as a disabled/locked select showing only "Trunk-Based Development"
   - Add help_text explaining more workflows coming soon

5. In `core/templates/core/ci_workflows/workflow_create.html`:
   - Add Dev Workflow field (locked/disabled) after runtime version
   - Add info icon/link to https://trunkbaseddevelopment.com/ with tooltip or helper text

6. In `core/templates/core/ci_workflows/workflow_detail.html`:
   - Add Development Workflow display in the header badges area
   - Show "Trunk-Based Development" badge with info icon linking to https://trunkbaseddevelopment.com/
  </action>
  <verify>
    - `uv run python manage.py check` passes
    - `uv run python manage.py migrate` completes
    - Workflow create page shows locked Dev Workflow field with info link
    - Workflow detail page shows Development Workflow badge with info link
  </verify>
  <done>
    CIWorkflow model has dev_workflow field.
    Workflow create form shows locked Trunk-Based option with info link.
    Workflow detail shows Development Workflow info with link to trunkbaseddevelopment.com.
  </done>
</task>

</tasks>

<verification>
- Service creation wizard has correct step order (Service -> Repository -> CI Workflow -> Configuration -> Review)
- Step 2 auto-selects default SCM connection
- Branch field label changes dynamically based on repo mode
- Step 3 shows workflow details, has view-all link and refresh button
- Draft warning shown when no workflow selected
- CIWorkflow has dev_workflow field (trunk_based default)
- Workflow creation and detail pages show Development Workflow with info link
</verification>

<success_criteria>
- All wizard UX improvements implemented
- Development Workflow field added to CIWorkflow model
- Info links to trunkbaseddevelopment.com present in both workflow create and detail pages
- No errors from `uv run python manage.py check`
- Database migrated successfully
</success_criteria>

<output>
After completion, create `.planning/quick/031-service-wizard-fixes-and-dev-workflow-su/031-SUMMARY.md`
</output>
