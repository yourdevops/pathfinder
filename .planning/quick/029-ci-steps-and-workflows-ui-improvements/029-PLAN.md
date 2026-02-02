---
phase: quick-029
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/ci_workflows/steps_catalog.html
  - core/templates/core/ci_workflows/_steps_table.html
  - core/templates/core/ci_workflows/step_detail.html
  - core/templates/core/ci_workflows/_compatible_steps.html
  - core/templates/core/ci_workflows/workflow_create.html
  - core/templates/core/ci_workflows/workflow_composer.html
  - core/views/ci_workflows.py
  - core/forms/ci_workflows.py
autonomous: true
must_haves:
  truths:
    - "Steps catalog shows 'CI Engine' header and human-friendly engine names"
    - "Steps catalog table is sortable by clicking column headers"
    - "Steps catalog defaults to phase ordering: Setup > Test > Build > Package"
    - "Versions filter in steps catalog uses a dynamic selector driven by runtime selection"
    - "Clicking a step row navigates to step detail page with repo/file@version link"
    - "Workflow creation dialog has CI Engine as first selection driving Runtime and Version"
    - "Workflow composer sorts available steps by phase: Setup > Test > Build > Package"
    - "Each step in composer has (i) button opening step detail in new window"
  artifacts:
    - path: "core/templates/core/ci_workflows/steps_catalog.html"
      provides: "Sortable steps catalog with CI Engine header"
    - path: "core/templates/core/ci_workflows/_steps_table.html"
      provides: "Table rows with human-friendly engine names and data attributes for sorting"
    - path: "core/templates/core/ci_workflows/step_detail.html"
      provides: "Step detail page with link to repo file at version"
    - path: "core/templates/core/ci_workflows/workflow_create.html"
      provides: "Workflow creation with CI Engine first"
    - path: "core/templates/core/ci_workflows/_compatible_steps.html"
      provides: "Step cards with (i) info button"
    - path: "core/views/ci_workflows.py"
      provides: "Engine display name mapping for steps, engine-driven form endpoints"
    - path: "core/forms/ci_workflows.py"
      provides: "WorkflowCreateForm with engine field"
  key_links:
    - from: "core/templates/core/ci_workflows/steps_catalog.html"
      to: "core/views/ci_workflows.py"
      via: "engine_display_map context variable"
    - from: "core/templates/core/ci_workflows/workflow_create.html"
      to: "core/views/ci_workflows.py"
      via: "HTMX cascade: engine > runtime_family > runtime_version"
---

<objective>
Improve CI Steps catalog and Workflow creation UX with 7 targeted enhancements: rename Engine header to "CI Engine" with human-friendly names, add table sorting with phase-based default, improve version filter, add repo/file@version links on step detail, add CI Engine selection to workflow creation, sort composer steps by phase, and add info buttons on composer steps.

Purpose: Make the CI Steps and Workflows UI more usable and informative.
Output: Updated templates, views, and forms for both Steps catalog and Workflow creation.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/views/ci_workflows.py
@core/forms/ci_workflows.py
@core/templates/core/ci_workflows/steps_catalog.html
@core/templates/core/ci_workflows/_steps_table.html
@core/templates/core/ci_workflows/_compatible_steps.html
@core/templates/core/ci_workflows/step_detail.html
@core/templates/core/ci_workflows/workflow_create.html
@core/templates/core/ci_workflows/workflow_composer.html
@core/models.py (CIStep, StepsRepository, RuntimeFamily models)
@plugins/base.py (get_available_engines, CICapableMixin)
@plugins/github/plugin.py (engine_name="github_actions", engine_display_name="GitHub Actions")
</context>

<tasks>

<task type="auto">
  <name>Task 1: Steps catalog improvements — CI Engine header, human-friendly names, sortable table, version selector</name>
  <files>
    core/views/ci_workflows.py
    core/templates/core/ci_workflows/steps_catalog.html
    core/templates/core/ci_workflows/_steps_table.html
  </files>
  <action>
  **1a. Engine display names in _steps_table.html:**
  In `_filter_steps()` in views/ci_workflows.py, build an `engine_display_map` dict mapping engine identifiers to display names using `get_available_engines()` (which returns list of (engine_name, display_name) tuples). Add it to the returned context dict.
  In `_steps_table.html`, replace `{{ step.engine|default:"—" }}` with a lookup: show the human-friendly name. Since Django templates can't do dict lookups with variable keys easily, the simplest approach is to annotate each step object in `_filter_steps()` with `step.engine_display` before returning. Loop through `steps_list` and set `step.engine_display = engine_display_map.get(step.engine, step.engine)`. Then use `{{ step.engine_display|default:"—" }}` in the template.

  **1b. Rename "Engine" header to "CI Engine":**
  In `steps_catalog.html`, change `<th>` from "Engine" to "CI Engine".

  **1c. Default sort by phase (Setup > Test > Build > Package):**
  The current queryset already orders by `phase, name`. The phase DB values are: setup, build, test, package. The desired display order is Setup > Test > Build > Package. Update the `.order_by()` in `_filter_steps()` to use Django's `Case/When` for custom phase ordering:
  ```python
  from django.db.models import Case, When, Value, IntegerField
  phase_ordering = Case(
      When(phase='setup', then=Value(0)),
      When(phase='test', then=Value(1)),
      When(phase='build', then=Value(2)),
      When(phase='package', then=Value(3)),
      default=Value(4),
      output_field=IntegerField(),
  )
  steps = CIStep.objects.all().select_related("repository").annotate(phase_order=phase_ordering).order_by("phase_order", "name")
  ```

  **1d. Sortable table headers:**
  Add Alpine.js inline `x-data` on the table wrapper in `steps_catalog.html` for client-side sorting. Each `<th>` becomes clickable with `@click` to sort. Use a small Alpine component that:
  - Stores `sortCol` (default: 'phase') and `sortDir` (default: 'asc')
  - On header click, toggles direction if same col, else sets new col with 'asc'
  - Adds `data-sort-*` attributes to each `<tr>` in `_steps_table.html` for name, phase (using numeric values: setup=0, test=1, build=2, package=3), engine, repository
  - Uses `x-sort` or manual DOM reordering via Alpine to sort rows

  Since the table body is loaded via HTMX, the simplest approach is: add `data-sort-name`, `data-sort-phase` (numeric), `data-sort-engine`, `data-sort-repo` attributes to each `<tr>` in `_steps_table.html`. In `steps_catalog.html`, wrap the table in an Alpine `x-data` component that handles sorting by reading data attributes and reordering DOM rows. Add sort indicator arrows on the active column header.

  **1e. Version filter as HTMX-driven selector:**
  The version filter already exists as a `<select>` dropdown. Currently it shows all versions. Enhance it so that when a runtime is selected, it fetches versions via HTMX from the existing `RuntimeVersionsView` endpoint. Update the runtime_version `<select>` to use `hx-get` on the runtime `<select>` change to populate versions dynamically (similar to workflow_create.html pattern). The runtime `<select>` should include `hx-get="{% url 'ci_workflows:runtime_versions' %}"` with `hx-target` pointing to the version select, and `hx-include="[name='runtime']"` but map the param name. Since `RuntimeVersionsView` expects `runtime_family` param but the catalog filter uses `runtime`, add a small adapter: in `RuntimeVersionsView.get()`, also check for `request.GET.get("runtime", "")` as a fallback for `runtime_family`. Then wire the runtime select's `hx-get` to `{% url 'ci_workflows:runtime_versions' %}` with `hx-target="#version-filter"`, give the version select `id="version-filter"`. The version select should also trigger the table filter on change (keep existing hx-get for table filtering).
  </action>
  <verify>
  Run `uv run python manage.py check` to verify no Django errors.
  Run `uv run python manage.py tailwind build && uv run python manage.py collectstatic --noinput` to rebuild.
  Visually: steps catalog page loads, shows "CI Engine" header with "GitHub Actions" instead of "github_actions", table rows are sortable by clicking headers, default sort is by phase (Setup first), version filter populates dynamically when runtime is selected.
  </verify>
  <done>
  Steps catalog shows "CI Engine" column header with human-friendly engine names. Table is client-side sortable by all column headers. Default ordering is Setup > Test > Build > Package. Version filter dynamically populates based on selected runtime.
  </done>
</task>

<task type="auto">
  <name>Task 2: Step detail — add repo/file@version link</name>
  <files>
    core/templates/core/ci_workflows/step_detail.html
    core/views/ci_workflows.py
  </files>
  <action>
  In `StepDetailView.get()`, compute a source URL for the step's file in its repository. The step has `step.repository.git_url` (e.g., "https://github.com/org/ci-steps-repo"), `step.directory_name` (e.g., "setup-python"), and `step.commit_sha`. Also need the engine file name from the plugin.

  Build the source link:
  ```python
  from plugins.base import get_ci_plugin_for_engine
  ci_plugin = get_ci_plugin_for_engine(step.engine)
  engine_file = ci_plugin.engine_file_name if ci_plugin else "action.yml"

  # Build GitHub-style URL: {git_url}/blob/{commit_sha}/{directory_name}/{engine_file}
  # Strip trailing .git from git_url if present
  base_url = step.repository.git_url.rstrip("/")
  if base_url.endswith(".git"):
      base_url = base_url[:-4]
  source_url = f"{base_url}/blob/{step.commit_sha}/{step.directory_name}/{engine_file}" if step.commit_sha else ""
  ```

  Pass `source_url` and `engine_file` to the template context.

  In `step_detail.html`, add a "Source" row in the General info card, after the "Commit SHA" row:
  ```html
  {% if source_url %}
  <div>
      <dt class="text-sm text-dark-muted">Source</dt>
      <dd>
          <a href="{{ source_url }}" target="_blank" rel="noopener noreferrer"
             class="text-dark-accent hover:text-dark-accent/80 transition-colors text-sm font-mono inline-flex items-center gap-1">
              {{ step.directory_name }}/{{ engine_file }}@{{ step.commit_sha|truncatechars:8 }}
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
          </a>
      </dd>
  </div>
  {% endif %}
  ```

  Also add the CI Engine display name to the step detail page. Compute it in the view:
  ```python
  engine_display = ci_plugin.engine_display_name if ci_plugin else step.engine
  ```
  Add a "CI Engine" row in the General info card showing `engine_display`.
  </action>
  <verify>
  Run `uv run python manage.py check` to verify no errors.
  Navigate to a step detail page and verify the source link appears with the correct URL format and opens in a new tab.
  </verify>
  <done>
  Step detail page shows a clickable "Source" link in format `directory/file@sha` that opens the repository file at the correct version in a new browser tab. CI Engine name is displayed.
  </done>
</task>

<task type="auto">
  <name>Task 3: Workflow creation — CI Engine first, then Runtime, then Version; composer info buttons and phase sort</name>
  <files>
    core/forms/ci_workflows.py
    core/views/ci_workflows.py
    core/templates/core/ci_workflows/workflow_create.html
    core/templates/core/ci_workflows/_compatible_steps.html
    core/templates/core/ci_workflows/workflow_composer.html
    core/urls.py
  </files>
  <action>
  **3a. Add CI Engine field to WorkflowCreateForm:**
  In `core/forms/ci_workflows.py`, add an `engine` field to `WorkflowCreateForm` BEFORE `runtime_family`:
  ```python
  engine = forms.ChoiceField(
      choices=[],
      widget=forms.Select(attrs={"class": DARK_SELECT}),
  )
  ```
  In `__init__`, populate engine choices from `get_available_engines()`:
  ```python
  from plugins.base import get_available_engines
  engine_choices = [("", "-- Select CI engine --")] + list(get_available_engines())
  self.fields["engine"].choices = engine_choices
  ```
  The field order should be: name, description, engine, runtime_family, runtime_version.

  **3b. Add HTMX endpoint for engine-filtered runtimes:**
  Create a new view `EngineRuntimesView` in `views/ci_workflows.py` that returns `<option>` elements for runtime families available for the selected engine. Query `RuntimeFamily` objects via their `repository__engine` field:
  ```python
  class EngineRuntimesView(LoginRequiredMixin, View):
      def get(self, request):
          engine = request.GET.get("engine", "")
          if not engine:
              return HttpResponse('<option value="">-- Select engine first --</option>')
          families = RuntimeFamily.objects.filter(
              repository__engine=engine
          ).values_list("name", flat=True).distinct().order_by("name")
          options = ['<option value="">-- Select runtime --</option>']
          for f in families:
              options.append(f'<option value="{f}">{f.title()}</option>')
          return HttpResponse("\n".join(options))
  ```
  Register URL: `path("engine-runtimes/", EngineRuntimesView.as_view(), name="engine_runtimes")` in `ci_workflows_patterns` (before the dynamic workflow paths).

  Import `EngineRuntimesView` in `core/urls.py`.

  **3c. Update workflow_create.html:**
  Add the CI Engine field as the first selection after description. Field order: Name, Description, CI Engine, Runtime Family, Runtime Version.

  The CI Engine select should drive Runtime Family via HTMX:
  ```html
  <select name="engine" id="id_engine"
          hx-get="{% url 'ci_workflows:engine_runtimes' %}"
          hx-trigger="change"
          hx-target="#id_runtime_family"
          hx-include="[name='engine']"
          class="...">
  ```

  The Runtime Family select should drive Runtime Version via HTMX (already exists, keep it).

  When engine changes, also clear the version select by adding `hx-swap="innerHTML"` behavior. The simplest way: when engine changes, it replaces runtime_family options. When runtime_family changes, it replaces runtime_version options (already wired).

  Also pass the engine value through to the composer. In `WorkflowCreateView.post()`, add `engine` to the URL params:
  ```python
  params = urlencode({
      "name": form.cleaned_data["name"],
      "description": form.cleaned_data.get("description", ""),
      "engine": form.cleaned_data["engine"],
      "runtime_family": form.cleaned_data["runtime_family"],
      "runtime_version": form.cleaned_data["runtime_version"],
  })
  ```

  **3d. Add (i) info button to each step in the composer's available steps panel:**
  In `_compatible_steps.html`, add an info button next to each step card's add (+) button. The (i) button should open the step detail page in a new window/tab:
  ```html
  <a href="{% url 'ci_workflows:step_detail' step_uuid=step.uuid %}"
     target="_blank" rel="noopener noreferrer"
     class="p-1 text-dark-muted hover:text-dark-accent transition-colors flex-shrink-0"
     title="View step details"
     @click.stop>
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
  </a>
  ```
  Place this BEFORE the existing add (+) button. Use `@click.stop` to prevent the parent div's `@click="addStepFromEl($el)"` from firing.

  **3e. Composer available steps are already sorted by phase (Setup > Test > Build > Package):**
  The `_build_compatible_context` method in `WorkflowComposerView` already groups by phase in order `["setup", "build", "test", "package"]` and renders them grouped. However, per the requirement, the sort should be Setup > Test > Build > Package. Update the `phase_order` list in `_build_compatible_context` and `CompatibleStepsView.get()` to: `["setup", "test", "build", "package"]`.

  Also update the same ordering in `StepsRepoDetailView.get()` for consistency.
  </action>
  <verify>
  Run `uv run python manage.py check` to verify no Django errors.
  Run `uv run python manage.py tailwind build && uv run python manage.py collectstatic --noinput`.
  Visually: Workflow creation page shows CI Engine dropdown first, selecting an engine populates runtimes, selecting runtime populates versions. Composer shows (i) button on each available step that opens detail in new tab. Available steps are ordered Setup > Test > Build > Package.
  </verify>
  <done>
  Workflow creation has CI Engine as first selection driving Runtime and Version cascades. Composer has (i) info buttons on each available step opening detail in new window. Available steps sorted by phase: Setup > Test > Build > Package.
  </done>
</task>

</tasks>

<verification>
1. `uv run python manage.py check` passes with no errors
2. `uv run python manage.py tailwind build` completes successfully
3. Steps catalog page loads with "CI Engine" header showing human-friendly names
4. Table headers are clickable for sorting, default sort is Setup > Test > Build > Package
5. Version filter populates dynamically when a runtime is selected
6. Step detail page shows source link to repo/file@version
7. Workflow creation shows CI Engine > Runtime > Version cascade
8. Composer available steps have (i) info buttons opening new tabs
9. Composer steps sorted by phase: Setup > Test > Build > Package
</verification>

<success_criteria>
All 7 UI improvements from the description are implemented and working:
1. "CI Engine" header with human-friendly names in steps catalog
2. Sortable table with phase-based default sorting
3. Dynamic version filter selector
4. Step detail shows repo/file@version link
5. Workflow creation has CI Engine as first selection
6. Composer sorts available steps by phase
7. (i) button on each composer step opens detail in new window
</success_criteria>

<output>
After completion, create `.planning/quick/029-ci-steps-and-workflows-ui-improvements/029-SUMMARY.md`
</output>
