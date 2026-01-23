---
phase: quick-008
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/context_processors.py
  - theme/templates/base.html
  - core/templates/core/components/nav_settings.html
  - core/templates/core/settings/general.html
  - core/templates/core/settings/user_management.html
  - core/templates/core/settings/audit_logs.html
  - core/templates/core/settings/api_tokens.html
  - core/templates/core/settings/notifications.html
  - core/templates/core/projects/detail.html
  - core/templates/core/projects/_services_tab.html
  - core/templates/core/projects/_environments_tab.html
  - core/templates/core/projects/_members_tab.html
autonomous: true

must_haves:
  truths:
    - "Settings pages show ONLY the settings sidebar, not stacked with main nav"
    - "Settings and Projects content areas have consistent padding matching Users page"
    - "Project detail page has no redundant tab navigation in header (sidebar has tabs)"
    - "Empty state icons are reasonably sized (not giant)"
  artifacts:
    - path: "core/templates/core/components/nav_settings.html"
      provides: "Reusable settings sidebar component"
    - path: "core/context_processors.py"
      provides: "in_settings_context detection"
    - path: "theme/templates/base.html"
      provides: "Context-aware sidebar switching"
  key_links:
    - from: "core/context_processors.py"
      to: "theme/templates/base.html"
      via: "in_settings_context variable"
    - from: "theme/templates/base.html"
      to: "nav_settings.html"
      via: "conditional include"
---

<objective>
Fix Settings and Projects UI layout issues: Settings sidebar should REPLACE main nav (AWS-style context replacement), add proper padding to content areas, remove redundant tab navigation from project detail header, and fix oversized empty state icons.

Purpose: Consistent navigation UX where Settings has its own context-replacing sidebar, matching the existing project sidebar pattern.
Output: Clean UI with proper sidebar replacement and consistent padding across Settings and Projects pages.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@core/context_processors.py
@theme/templates/base.html
@core/templates/core/components/nav.html
@core/templates/core/components/nav_project.html
@core/templates/core/settings/general.html
@core/templates/core/projects/detail.html
@core/templates/core/users/list.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add in_settings_context to context processor and create settings sidebar</name>
  <files>
    core/context_processors.py
    theme/templates/base.html
    core/templates/core/components/nav_settings.html
  </files>
  <action>
1. Update `core/context_processors.py` - add `in_settings_context` to the `navigation_context` function:
   - Add `'in_settings_context': False` to the initial context dict
   - After the project context check, add settings context detection:
     ```python
     # Check if we're in a settings URL
     if hasattr(request, 'resolver_match') and request.resolver_match:
         if request.resolver_match.url_name and request.resolver_match.app_name == 'settings':
             context['in_settings_context'] = True
     ```
   - Alternatively, check if URL path starts with '/settings/'

2. Create `core/templates/core/components/nav_settings.html` as a reusable settings sidebar:
   - Use same structure as nav_project.html (fixed left-0 top-0 h-full w-64 bg-dark-surface)
   - Add "Back to Dashboard" link at top (pointing to projects:list, with left arrow icon)
   - Add "Settings" header section with title and description
   - Include all 5 settings nav items with icons: General, User Management, Audit & Logs, API & Tokens, Notifications
   - Use `active_section` variable for highlighting active item (bg-dark-border when active)
   - Keep user section at bottom (same as nav.html)

3. Update `theme/templates/base.html` to support settings context:
   - Change the nav conditional from:
     ```
     {% if in_project_context and current_project %}
         {% include "core/components/nav_project.html" %}
     {% else %}
         {% include "core/components/nav.html" %}
     {% endif %}
     ```
   - To:
     ```
     {% if in_settings_context %}
         {% include "core/components/nav_settings.html" %}
     {% elif in_project_context and current_project %}
         {% include "core/components/nav_project.html" %}
     {% else %}
         {% include "core/components/nav.html" %}
     {% endif %}
     ```
  </action>
  <verify>
    - context_processors.py has in_settings_context detection
    - nav_settings.html exists with proper structure
    - base.html has three-way conditional for sidebar
  </verify>
  <done>Settings context detected via context processor, settings sidebar component created, base.html conditionally includes it</done>
</task>

<task type="auto">
  <name>Task 2: Simplify Settings templates - remove duplicate sidebar and fix padding</name>
  <files>
    core/templates/core/settings/general.html
    core/templates/core/settings/user_management.html
    core/templates/core/settings/audit_logs.html
    core/templates/core/settings/api_tokens.html
    core/templates/core/settings/notifications.html
  </files>
  <action>
For ALL 5 settings templates (general.html, user_management.html, audit_logs.html, api_tokens.html, notifications.html):

1. REMOVE the entire outer structure:
   - Remove `<div class="flex min-h-screen">`
   - Remove the entire `<aside>` settings sidebar block (51 lines of duplicate code)
   - Remove `<div class="flex-1 p-6">`
   - Remove `<div class="max-w-4xl">`

2. Keep ONLY the inner content with proper padding:
   ```django
   {% extends "base.html" %}

   {% block title %}[Page Title] - DevSSP{% endblock %}

   {% block content %}
   <div class="p-8">
       <div class="max-w-4xl">
           <h1 class="text-2xl font-bold text-dark-text mb-6">[Page Title]</h1>
           ... rest of actual content ...
       </div>
   </div>
   {% endblock %}
   ```

3. Use `p-8` padding (matching users/list.html pattern)

The sidebar is now handled by base.html via the `in_settings_context` conditional.
  </action>
  <verify>
    ```bash
    # Check no settings template has <aside> tags
    grep -l "<aside" core/templates/core/settings/*.html || echo "OK: no aside tags"
    # Check all have p-8 wrapper
    grep -l 'class="p-8"' core/templates/core/settings/*.html | wc -l  # should be 5
    ```
  </verify>
  <done>All 5 settings templates simplified to content-only with p-8 padding, sidebar handled by base.html</done>
</task>

<task type="auto">
  <name>Task 3: Fix Projects detail page - remove redundant tabs and fix icons</name>
  <files>
    core/templates/core/projects/detail.html
    core/templates/core/projects/_services_tab.html
    core/templates/core/projects/_environments_tab.html
    core/templates/core/projects/_members_tab.html
  </files>
  <action>
1. Update `core/templates/core/projects/detail.html`:
   - Change padding from `p-6` to `p-8` (match Users page)
   - REMOVE the entire tab navigation section:
     ```html
     <!-- REMOVE THIS ENTIRE BLOCK -->
     <div class="border-b border-dark-border mb-6">
         <nav class="flex space-x-4">
             ... all the tab links ...
         </nav>
     </div>
     ```
   - Keep project header (h1 + description) and tab-content div
   - The sidebar (nav_project.html) already has the tab navigation links

2. Update empty state icons in project tab templates (reduce from w-16 h-16 to w-12 h-12):
   - `_services_tab.html`: Change `w-16 h-16` to `w-12 h-12` on the SVG icon
   - `_environments_tab.html`: Change `w-16 h-16` to `w-12 h-12` on empty state SVG
   - `_members_tab.html`: Change `w-16 h-16` to `w-12 h-12` on empty state SVG
  </action>
  <verify>
    ```bash
    # Check no nav tab bar in detail.html
    grep -c 'nav class="flex space-x-4"' core/templates/core/projects/detail.html  # should be 0
    # Check p-8 padding
    grep 'class="p-8"' core/templates/core/projects/detail.html
    # Check icons are w-12
    grep -c 'w-16 h-16' core/templates/core/projects/_*_tab.html  # should be 0
    ```
  </verify>
  <done>Project detail header simplified to title+description only, tabs removed (handled by sidebar), icons sized to w-12</done>
</task>

</tasks>

<verification>
1. Start dev server: `source venv/bin/activate && python manage.py runserver`
2. Login and navigate to Settings > General:
   - ONLY settings sidebar visible (no main nav stacking)
   - "Back to Dashboard" link at top of sidebar
   - Content has proper p-8 padding
3. Navigate between all 5 settings pages - sidebar persists, active item highlighted
4. Navigate to Projects > [any project]:
   - Project sidebar visible (replaces main nav)
   - NO duplicate tab bar in content area
   - Header shows only project name + description
5. Check empty states in Services/Environments/Members tabs - icons are w-12 h-12
</verification>

<success_criteria>
- Settings pages show ONLY settings sidebar (context-replacing, like AWS)
- Settings content has consistent p-8 padding matching Users page
- Project detail has NO redundant tab navigation in header
- Empty state icons are w-12 h-12 (not giant w-16 h-16)
- All navigation still works (sidebar links, HTMX tab switching)
</success_criteria>

<output>
After completion, create `.planning/quick/008-fix-settings-and-projects-ui-sidebar-rep/008-SUMMARY.md`
</output>
