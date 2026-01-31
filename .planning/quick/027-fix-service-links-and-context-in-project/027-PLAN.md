---
phase: quick
plan: 027
type: execute
wave: 1
depends_on: []
files_modified:
  - theme/templates/base.html
  - core/templates/core/services/detail.html
  - core/templates/core/components/nav_service.html
  - core/templates/core/projects/_services_tab.html
  - core/templates/core/services/_details_tab.html
  - core/templates/core/services/_settings_tab.html
  - core/views/services.py
autonomous: true

must_haves:
  truths:
    - "Clicking a service name on the project services tab navigates to the service detail page with the service sidebar"
    - "Service detail page shows service-scoped sidebar (nav_service.html) replacing the project sidebar"
    - "Service sidebar has a Settings nav item that shows service settings (env vars, delete)"
  artifacts:
    - path: "theme/templates/base.html"
      provides: "block sidebar support for context-replacing navigation"
      contains: "block sidebar"
    - path: "core/templates/core/services/_settings_tab.html"
      provides: "Service settings tab with env vars and danger zone"
    - path: "core/templates/core/components/nav_service.html"
      provides: "Settings nav item in service sidebar"
      contains: "Settings"
  key_links:
    - from: "core/templates/core/projects/_services_tab.html"
      to: "projects:service_detail"
      via: "anchor tag with href"
      pattern: "<a href.*service_detail"
    - from: "core/templates/core/services/detail.html"
      to: "core/components/nav_service.html"
      via: "block sidebar override"
      pattern: "block sidebar"
---

<objective>
Fix three related issues with service navigation and context:
1. Service names on the project services tab should be proper clickable links (not just row onclick)
2. Service detail page should replace the sidebar with service-scoped navigation (nav_service.html)
3. Add a Settings tab to the service view for env vars and delete functionality

Root cause of issue 2: base.html has no `{% block sidebar %}` -- sidebar is hardcoded via context processor. Service detail.html defines block sidebar but it's ignored.

Purpose: Make service navigation work correctly with proper context-replacing sidebar pattern.
Output: Working service links, service-scoped sidebar, and settings tab.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@theme/templates/base.html
@core/templates/core/services/detail.html
@core/templates/core/components/nav_service.html
@core/templates/core/components/nav_project.html
@core/templates/core/projects/_services_tab.html
@core/templates/core/services/_details_tab.html
@core/views/services.py
@core/context_processors.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add block sidebar to base.html and fix service sidebar rendering</name>
  <files>
    theme/templates/base.html
    core/templates/core/services/detail.html
    core/templates/core/projects/_services_tab.html
  </files>
  <action>
  1. In `theme/templates/base.html`, wrap the sidebar include logic (lines 32-36) in a `{% block sidebar %}...{% endblock %}` block. This allows child templates to override the sidebar. The existing logic becomes the default:

  ```html
  {% block sidebar %}
  {% if in_project_context and current_project %}
      {% include "core/components/nav_project.html" %}
  {% else %}
      {% include "core/components/nav.html" %}
  {% endif %}
  {% endblock %}
  ```

  2. In `core/templates/core/services/detail.html`, the existing `{% block sidebar %}` with `{% include "core/components/nav_service.html" %}` will now work correctly since base.html defines the block.

  3. In `core/templates/core/projects/_services_tab.html`, make the service name a proper `<a>` tag link inside the table row. Keep the row `onclick` for the full row clickability, but add an actual anchor on the service name text so it looks clickable:

  Change the `<span class="text-dark-text font-medium">` inside the `<td>` to an `<a>` tag:
  ```html
  <a href="{% url 'projects:service_detail' project_name=project.name service_name=service.name %}"
     class="text-dark-text hover:text-dark-accent font-medium transition-colors">
      {{ service.name }}
  </a>
  ```

  The table row already has `onclick` for the whole row, so this just adds the visual link indicator on the name itself.
  </action>
  <verify>
  - `uv run python manage.py check` passes
  - Visit a project page, verify service names appear as links (hover shows pointer/color change)
  - Click a service name, verify the service detail page loads WITH the service-scoped sidebar (back arrow to project, service name header, Details/CI/Builds/Environments nav items)
  </verify>
  <done>Service detail page renders with service-scoped sidebar (nav_service.html) replacing the project sidebar. Service names on project page are proper anchor links.</done>
</task>

<task type="auto">
  <name>Task 2: Add Settings tab to service view</name>
  <files>
    core/templates/core/components/nav_service.html
    core/templates/core/services/_settings_tab.html
    core/views/services.py
    core/templates/core/services/_details_tab.html
  </files>
  <action>
  1. In `core/views/services.py` `ServiceDetailView`:
     - Add "settings" to `valid_tabs` list (in both `get_template_names` and `get_context_data`)
     - In the settings tab context, provide the same data as the details tab for env vars plus the can_edit flag:
       ```python
       elif tab == "settings":
           context["merged_env_vars"] = self.service.get_merged_env_vars()
           context["can_edit"] = self.user_project_role in ("contributor", "owner")
       ```

  2. Create `core/templates/core/services/_settings_tab.html` with:
     - Environment Variables section (move from _details_tab.html -- show merged env vars with source badges and locked indicators)
     - Danger Zone section with delete button (move from _details_tab.html)
     - Keep the same styling patterns as the existing _details_tab.html sections

  3. In `core/templates/core/services/_details_tab.html`:
     - Remove the "Environment Variables" section (lines ~70-101) -- moved to settings
     - Remove the "Danger Zone" section (lines ~103-125) -- moved to settings
     - Keep: header with status, service info grid (handler, status, repository, branch), scaffold error

  4. In `core/templates/core/components/nav_service.html`, add a Settings nav item after Environments:
     ```html
     <!-- Settings -->
     <a href="{% url 'projects:service_detail' project_name=project.name service_name=service.name %}?tab=settings"
        hx-get="{% url 'projects:service_detail' project_name=project.name service_name=service.name %}?tab=settings"
        hx-target="#tab-content"
        hx-push-url="true"
        class="flex items-center px-3 py-2 rounded-lg text-dark-text hover:bg-dark-border/50 transition-colors {% if request.GET.tab == 'settings' %}bg-dark-border{% endif %}">
         <svg class="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
             <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
             <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
         </svg>
         Settings
     </a>
     ```
     Use the same gear icon SVG as the project settings nav item in nav_project.html.
  </action>
  <verify>
  - `uv run python manage.py check` passes
  - Navigate to a service detail page, verify Settings appears in the service sidebar
  - Click Settings tab, verify env vars and danger zone (delete) are shown
  - Verify Details tab no longer shows env vars or danger zone
  - Verify HTMX tab switching works (click between Details, Settings, CI, etc.)
  </verify>
  <done>Service view has a Settings tab accessible from the sidebar. Env vars and delete functionality are in the Settings tab. Details tab shows only service info (handler, status, repo, branch).</done>
</task>

</tasks>

<verification>
1. `uv run python manage.py check` -- no template or view errors
2. Navigate to project page, click a service name -- service detail loads with service sidebar
3. Service sidebar shows: Details, CI Workflow, Builds, Environments, Settings
4. Clicking "Settings" in service sidebar shows env vars and delete button
5. Back arrow in service sidebar returns to project page
6. All HTMX tab switching works correctly within service view
</verification>

<success_criteria>
- Services are clickable links from the project services tab
- Service detail page shows service-scoped sidebar (not project sidebar)
- Service Settings tab exists with env vars and delete functionality
- All existing service functionality (Details, CI, Builds, Environments tabs) continues to work
</success_criteria>

<output>
After completion, create `.planning/quick/027-fix-service-links-and-context-in-project/027-SUMMARY.md`
</output>
