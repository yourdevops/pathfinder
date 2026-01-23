---
phase: quick-011
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/components/nav.html
  - core/templates/core/connections/list.html
  - core/templates/core/connections/plugins.html
  - core/views/connections.py
  - core/urls.py
autonomous: true

must_haves:
  truths:
    - "Clicking Integrations sidebar expands to show Connections and Plugins sub-items"
    - "Currently selected sub-item (Connections or Plugins) is visually highlighted"
    - "Plugins page shows list of installed plugins with name, type, connection count"
    - "Plugins page has search field and type filter"
    - "Each plugin has Add Connection button and Remove button (grayed when no connections)"
    - "Connections page has search field and type filter above list"
    - "Add Connection button on Connections page redirects to Plugins page"
  artifacts:
    - path: "core/templates/core/components/nav.html"
      provides: "Expandable Integrations nav with Connections/Plugins sub-items"
    - path: "core/templates/core/connections/plugins.html"
      provides: "Plugins list page template"
    - path: "core/views/connections.py"
      provides: "PluginListView with plugin data and connection counts"
  key_links:
    - from: "nav.html"
      to: "connections:list, connections:plugins"
      via: "Sidebar sub-navigation links"
    - from: "connections/list.html"
      to: "connections:plugins"
      via: "Add Connection button redirect"
---

<objective>
Implement expandable Integrations sidebar navigation with Connections and Plugins sub-pages.

Purpose: Improve navigation UX by grouping integration-related pages under expandable sidebar section, and add Plugins management page for viewing/managing installed plugins.

Output: Updated nav.html with expandable Integrations section, new Plugins page, search/filter on Connections page.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/templates/core/components/nav.html
@core/templates/core/connections/list.html
@core/views/connections.py
@core/urls.py
@plugins/base.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add expandable Integrations nav section</name>
  <files>core/templates/core/components/nav.html</files>
  <action>
Update the Integrations nav item to be an expandable section with Alpine.js:

1. Replace the simple `<a>` link with an expandable container using Alpine.js `x-data="{ expanded: true }"` (default expanded when on any integrations page)
2. Create parent item with toggle arrow icon (rotates on expand/collapse)
3. Add two sub-items with left indent (~8px padding-left more than parent):
   - Connections (links to connections:list, highlight when on connections path but not plugins)
   - Plugins (links to connections:plugins, highlight when on plugins path)
4. Keep the link icon in the parent, use smaller bullet or no icon for sub-items
5. Parent should NOT be clickable as link, only toggles expansion
6. Auto-expand when on any /connections/* path using `x-init="expanded = $el.querySelector('a[href*=connections]')?.closest('[x-data]')?.classList.contains('bg-dark-border')"`
7. Match existing hover/active styling patterns (bg-dark-border for active, hover:bg-dark-border/50)

Styling:
- Parent: Same as other nav items, but with chevron icon on right
- Sub-items: text-sm, pl-11 (to align with other nav text), slightly muted color when inactive
- Active sub-item: bg-dark-border/50 with text-dark-text
  </action>
  <verify>
Visual inspection: Sidebar shows expandable Integrations with Connections/Plugins sub-items.
`grep -q "x-data" core/templates/core/components/nav.html` returns success.
  </verify>
  <done>Integrations sidebar section expands/collapses to show Connections and Plugins links with proper highlighting.</done>
</task>

<task type="auto">
  <name>Task 2: Create Plugins list page with search/filter</name>
  <files>core/templates/core/connections/plugins.html, core/views/connections.py, core/urls.py</files>
  <action>
Create PluginListView in core/views/connections.py:

```python
class PluginListView(LoginRequiredMixin, ListView):
    """List all installed plugins with connection counts."""
    template_name = 'core/connections/plugins.html'
    context_object_name = 'plugins_list'

    def get_queryset(self):
        # Return list of plugin dicts with connection counts
        plugins_data = []
        for name, plugin in registry.all().items():
            connection_count = IntegrationConnection.objects.filter(plugin_name=name).count()
            plugins_data.append({
                'name': name,
                'display_name': plugin.display_name,
                'category': plugin.category,
                'connection_count': connection_count,
                'can_remove': connection_count == 0,  # Only removable if no connections
            })
        return plugins_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ['scm', 'deploy', 'ci']  # For filter dropdown
        context['can_manage'] = (
            has_system_role(self.request.user, 'admin') or
            has_system_role(self.request.user, 'operator')
        )
        return context
```

Add URL pattern in core/urls.py connections_patterns:
```python
path('plugins/', PluginListView.as_view(), name='plugins'),
```

Update __init__.py import to include PluginListView.

Create template core/templates/core/connections/plugins.html:
- Page header: "Plugins" with subtitle "Manage installed integration plugins"
- Search input (Alpine.js client-side filter by name/type)
- Category filter dropdown (All, SCM, Deploy, CI)
- Grid of plugin cards showing:
  - Plugin display_name
  - Category badge (colored: scm=blue, deploy=green, ci=purple)
  - Connection count (e.g., "3 connections")
  - [+ Add Connection] button linking to connections:create with plugin_name
  - [Remove] button (disabled/grayed out if connection_count > 0, with title explaining why)
- Empty state if no plugins installed

Card styling: Match existing dark theme (bg-dark-surface, border-dark-border, hover states).
Filter with Alpine.js: x-data="{ search: '', category: '' }" with x-show on cards.
  </action>
  <verify>
`python manage.py check` passes.
Visit /connections/plugins/ shows plugin list with Docker and GitHub plugins.
Search filters plugins by name.
Category filter shows only matching plugins.
  </verify>
  <done>Plugins page displays all installed plugins with search, category filter, connection counts, and action buttons.</done>
</task>

<task type="auto">
  <name>Task 3: Add search/filter to Connections page and redirect Add button</name>
  <files>core/templates/core/connections/list.html</files>
  <action>
Update core/templates/core/connections/list.html:

1. Add search and filter bar below header, above connection sections:
   - Search input (Alpine.js client-side filter by connection name)
   - Category filter dropdown (All, SCM, Deploy, Other)
   - Use Alpine.js x-data="{ search: '', category: '' }" at page level

2. Wrap each connection section in x-show logic to filter:
   - Each connection card gets x-show="(search === '' || connection.name.toLowerCase().includes(search.toLowerCase())) && (category === '' || category === connection.category)"
   - This requires passing category to card context

3. Change "Add Connection" button behavior:
   - Instead of dropdown showing plugins, make it a simple button/link
   - Links directly to {% url 'connections:plugins' %}
   - Tooltip: "Select a plugin to add a new connection"
   - Remove the Alpine dropdown logic from this button

4. Keep the empty state dropdown for selecting plugins (when no connections exist)
   - Or also change to redirect to plugins page

Search/filter bar styling:
- Flex row with gap-4
- Search: w-64 input with search icon
- Filter: select dropdown with dark theme styling
  </action>
  <verify>
Visit /connections/ page shows search field and category filter.
Typing in search filters connection cards in real-time.
Category dropdown filters to show only matching categories.
"Add Connection" button navigates to /connections/plugins/ page.
  </verify>
  <done>Connections page has working search and category filter, Add Connection redirects to Plugins page for plugin selection.</done>
</task>

</tasks>

<verification>
1. Navigate to app, verify Integrations sidebar expands to show Connections and Plugins
2. Click Connections - verify page loads with search/filter, sub-item highlighted
3. Click Plugins - verify page loads with plugin list, sub-item highlighted
4. Search/filter works on both pages
5. Add Connection button on Connections page goes to Plugins page
6. Add Connection button on Plugins page creates connection for that plugin
7. Remove button grayed out when plugin has connections
</verification>

<success_criteria>
- Expandable Integrations nav with Connections/Plugins sub-items
- Active sub-item visually highlighted
- Plugins page lists all installed plugins with connection counts
- Both pages have functional search and category filters
- Add Connection flow goes through Plugins page for selection
- Remove button properly disabled when plugin has active connections
</success_criteria>

<output>
After completion, create `.planning/quick/011-integrations-sidebar-expansion-with-plug/011-SUMMARY.md`
</output>
