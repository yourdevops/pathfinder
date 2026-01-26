---
phase: quick
plan: 015
type: execute
wave: 1
depends_on: []
files_modified:
  - core/models.py
  - core/tasks.py
  - core/views/blueprints.py
  - core/templates/core/blueprints/detail.html
  - core/templates/core/blueprints/_preview.html
  - core/templates/core/blueprints/list.html
  - core/migrations/NNNN_blueprint_deploy_plugins.py
autonomous: true

must_haves:
  truths:
    - "Blueprint can require multiple deploy plugins"
    - "Blueprint is available if ANY of its deploy_plugins has active connection"
    - "UI displays comma-separated list of required plugins"
  artifacts:
    - path: "core/models.py"
      provides: "Blueprint.deploy_plugins JSONField and updated availability methods"
      contains: "deploy_plugins = models.JSONField"
    - path: "core/migrations/*_blueprint_deploy_plugins.py"
      provides: "Field migration with data conversion"
  key_links:
    - from: "core/tasks.py"
      to: "Blueprint.deploy_plugins"
      via: "full required_plugins list assignment"
      pattern: "blueprint\\.deploy_plugins\\s*="
---

<objective>
Change Blueprint model's `deploy_plugin` CharField to `deploy_plugins` JSONField (list) to support blueprints requiring multiple deployment targets.

Purpose: Some blueprints need multiple deploy connections (e.g., kubernetes + docker-registry). Current single field cannot express this.
Output: Updated model, migration, views, and templates supporting plugin lists.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@core/models.py (lines 360-440 - Blueprint model)
@core/tasks.py (lines 165-180 - sync task deploy_plugin logic)
@core/views/blueprints.py (lines 31-48, 106, 129-136, 279)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update Blueprint model and create migration</name>
  <files>core/models.py, core/migrations/NNNN_blueprint_deploy_plugins.py</files>
  <action>
1. In core/models.py line 371, change:
   - FROM: `deploy_plugin = models.CharField(max_length=63, blank=True)`
   - TO: `deploy_plugins = models.JSONField(default=list)  # List of required deploy plugin names`

2. Update `is_available_for_project()` (lines 410-425):
   - If `self.deploy_plugins` is empty list, return True
   - Check if ANY plugin in `self.deploy_plugins` has matching active connection
   - Use: `for plugin in self.deploy_plugins: if EnvironmentConnection exists for plugin, return True`
   - Return False if none match

3. Update `is_available_globally()` (lines 427-439):
   - Same logic: empty list = True, check ANY plugin has active IntegrationConnection

4. Create migration:
   - Run `python manage.py makemigrations core --name blueprint_deploy_plugins`
   - Edit migration to add data migration step that converts existing string values to single-element lists (or empty list if blank)
  </action>
  <verify>
    - `python manage.py makemigrations --check` shows no changes needed
    - `python manage.py migrate` succeeds
    - `python manage.py shell -c "from core.models import Blueprint; print(Blueprint._meta.get_field('deploy_plugins'))"` shows JSONField
  </verify>
  <done>Blueprint model has deploy_plugins JSONField, availability methods check any-match, migration applied</done>
</task>

<task type="auto">
  <name>Task 2: Update sync task and views</name>
  <files>core/tasks.py, core/views/blueprints.py</files>
  <action>
1. In core/tasks.py lines 172-178, update deploy plugin extraction:
   ```python
   # Get deploy plugins from required_plugins or fallback to type
   deploy_config = manifest.get('deploy', {})
   required_plugins = deploy_config.get('required_plugins', [])
   if required_plugins:
       blueprint.deploy_plugins = required_plugins  # Store full list
   else:
       deploy_type = deploy_config.get('type', '')
       blueprint.deploy_plugins = [deploy_type] if deploy_type else []
   ```

2. In core/views/blueprints.py:

   a. Line 33-38 (BlueprintListView.get): Collect deploy_plugins
      - Change `deploy_plugins.add(bp.deploy_plugin)` to flatten all lists:
        `deploy_plugins.update(bp.deploy_plugins)` (since deploy_plugins is already a list)

   b. Line 47: Change `'required_plugin': bp.deploy_plugin` to:
      `'required_plugins': bp.deploy_plugins if not is_available else []`

   c. Lines 106 and 129-136 (_get_deploy_plugin method and call):
      - Rename to `_get_deploy_plugins(self, manifest)` returning list
      - Return `required_plugins` if present, else `[deploy_config.get('type')]` if type exists, else `[]`
      - Update call site in preview_data to use 'deploy_plugins' key

   d. Line 279 (BlueprintDetailView): Change to:
      `required_plugins = blueprint.deploy_plugins if not is_available else []`
      Pass `required_plugins` (list) to template instead of `required_plugin` (string)
  </action>
  <verify>
    - `python manage.py check` passes
    - Grep for `deploy_plugin` (singular) in views should only find references to the old pattern in comments if any
  </verify>
  <done>Sync task stores full plugin list, views pass lists to templates</done>
</task>

<task type="auto">
  <name>Task 3: Update templates to display plugin lists</name>
  <files>core/templates/core/blueprints/detail.html, core/templates/core/blueprints/_preview.html, core/templates/core/blueprints/list.html</files>
  <action>
1. detail.html line 78:
   - Change `{{ blueprint.deploy_plugin|default:"None" }}`
   - TO: `{{ blueprint.deploy_plugins|join:", "|default:"None" }}`

2. _preview.html line 39:
   - Change `{{ preview_data.deploy_plugin|default:"None" }}`
   - TO: `{{ preview_data.deploy_plugins|join:", "|default:"None" }}`

3. list.html:
   a. Line 89 (data-plugin attribute):
      - Change `data-plugin="{{ item.blueprint.deploy_plugin }}"`
      - TO: `data-plugin="{{ item.blueprint.deploy_plugins|join:',' }}"`

   b. Line 94 (filterPlugin check in x-show):
      - Change `$el.dataset.plugin === filterPlugin`
      - TO: `$el.dataset.plugin.split(',').includes(filterPlugin)`
      (This allows filtering to match if ANY of the plugins matches the filter)

   c. Line 103 (title attribute for unavailable):
      - Change `title="Requires {{ item.required_plugin }} connection"`
      - TO: `title="Requires {{ item.required_plugins|join:', ' }} connection"`

   d. Line 125 (deploy plugin column):
      - Change `{{ item.blueprint.deploy_plugin|default:"-" }}`
      - TO: `{{ item.blueprint.deploy_plugins|join:", "|default:"-" }}`
  </action>
  <verify>
    - Run dev server: `python manage.py runserver`
    - Visit /blueprints/ - list should show comma-separated plugins
    - Register a blueprint with multiple required_plugins in manifest - should display all
  </verify>
  <done>All templates display plugin lists with comma separation, filtering works with any-match logic</done>
</task>

</tasks>

<verification>
- `python manage.py check` passes
- `python manage.py migrate` succeeds
- Blueprint with `deploy_plugins: ["kubernetes", "docker-registry"]` displays both in UI
- Blueprint is available if ANY of its deploy_plugins has active connection
- List page filter matches blueprints with any matching plugin
</verification>

<success_criteria>
- Blueprint.deploy_plugins is JSONField storing list of strings
- Existing single-value data migrated to single-element lists
- Availability logic uses any-match (OR) for multiple plugins
- UI displays comma-separated list everywhere
- Filtering on list page matches any plugin in the list
</success_criteria>

<output>
After completion, create `.planning/quick/015-support-multiple-deploy-plugins-in-bluep/015-SUMMARY.md`
</output>
