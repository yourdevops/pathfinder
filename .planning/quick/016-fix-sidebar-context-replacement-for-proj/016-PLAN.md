---
phase: quick
plan: 016
type: execute
wave: 1
depends_on: []
files_modified:
  - core/context_processors.py
autonomous: true

must_haves:
  truths:
    - "Sidebar shows project-specific navigation (Details, Services, Environments, Members) when viewing a project"
    - "Sidebar shows main navigation (Service Catalog, Blueprints, etc.) when NOT viewing a project"
    - "Back button appears in logo position when in project context"
  artifacts:
    - path: "core/context_processors.py"
      provides: "Project context detection via project_name URL kwarg"
      contains: "project_name"
  key_links:
    - from: "core/context_processors.py"
      to: "request.resolver_match.kwargs"
      via: "project_name lookup"
      pattern: "project_name.*kwargs"
---

<objective>
Fix sidebar context replacement for project navigation

Purpose: When selecting an existing project, the context items (Details, Services, Environments, Members) should replace the parent items on the sidebar. Currently, the context processor checks for `project_uuid` which no longer exists after Phase 4.1 slug URL migration.

Output: Working project-scoped sidebar that replaces main navigation when in project context.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Relevant decisions:
- 02-03: Context-replacing sidebar (AWS style) - Clearer project context, dedicated project nav
- 03.1-03: Details as first nav item in project sidebar - Default landing page for projects
- 04.1-01: Custom 'dns' path converter for name-based URLs
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update context processor to use project_name</name>
  <files>core/context_processors.py</files>
  <action>
In `navigation_context()` function, update the project context detection logic:

1. Change the check from `'project_uuid' in request.resolver_match.kwargs` to `'project_name' in request.resolver_match.kwargs`

2. Change the Project lookup from:
   ```python
   project = Project.objects.get(uuid=request.resolver_match.kwargs['project_uuid'])
   ```
   to:
   ```python
   project = Project.objects.get(name=request.resolver_match.kwargs['project_name'])
   ```

This aligns the context processor with the Phase 4.1 URL changes where projects now use `dns:project_name` in URLs instead of `uuid:project_uuid`.
  </action>
  <verify>
1. Start dev server: `source venv/bin/activate && python manage.py runserver`
2. Navigate to a project (e.g., http://localhost:8000/projects/test-project/)
3. Verify the sidebar shows:
   - "Back to Projects" link in logo position
   - Project name header
   - Details, Services, Environments, Members navigation items
4. Navigate back to projects list
5. Verify the sidebar returns to main navigation with Service Catalog, Blueprints, etc.
  </verify>
  <done>
Project-scoped sidebar appears when viewing any project page, main sidebar appears everywhere else.
  </done>
</task>

</tasks>

<verification>
- [ ] Project detail page shows project-scoped sidebar
- [ ] Project environment pages show project-scoped sidebar
- [ ] Projects list page shows main sidebar
- [ ] Other pages (blueprints, connections, settings) show main sidebar
- [ ] No Python errors in console
</verification>

<success_criteria>
- Sidebar correctly switches between main nav and project nav based on URL context
- All project-scoped URLs trigger the project sidebar
- Navigation highlight states work correctly in both sidebars
</success_criteria>

<output>
After completion, create `.planning/quick/016-fix-sidebar-context-replacement-for-proj/016-SUMMARY.md`
</output>
