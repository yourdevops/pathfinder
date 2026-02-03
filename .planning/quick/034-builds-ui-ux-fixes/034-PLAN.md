---
phase: quick-034
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/services/_builds_tab.html
  - core/templates/core/services/_build_row.html
  - core/templates/core/services/_build_row_expanded.html
  - core/views/services.py
autonomous: true

must_haves:
  truths:
    - "Author name appears once per row without duplication"
    - "Table headers are clickable and sort builds"
    - "Default sort is newest first (by started_at desc)"
    - "Search field filters builds by commit ID or message"
    - "Clicking a row expands to show details"
    - "Failed/cancelled builds show error context in expanded section"
    - "Successful builds show artifact_ref and external_url in expanded section"
    - "Actions column is removed from table"
  artifacts:
    - path: "core/templates/core/services/_builds_tab.html"
      provides: "Sortable headers, search field, removed Actions column"
    - path: "core/templates/core/services/_build_row.html"
      provides: "Clickable row with expand trigger, fixed author display"
    - path: "core/templates/core/services/_build_row_expanded.html"
      provides: "Expandable details section with logs/artifacts"
    - path: "core/views/services.py"
      provides: "Sorting and search query parameters"
  key_links:
    - from: "_builds_tab.html"
      to: "views/services.py"
      via: "HTMX hx-get with sort/search params"
    - from: "_build_row.html"
      to: "_build_row_expanded.html"
      via: "Alpine.js x-show toggle"
---

<objective>
Fix Builds UI/UX issues: author duplication, add sorting/search, make rows expandable.

Purpose: The builds table has a visual bug where author names appear twice and lacks essential UX features (sorting, searching, expandable details). This plan fixes the display bug and adds interactive features using HTMX and Alpine.js.

Output: A polished builds table with sortable columns (default: newest first), search by commit, expandable rows showing build details, and no Actions column (moved to expanded section).
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/templates/core/services/_builds_tab.html
@core/templates/core/services/_build_row.html
@core/views/services.py (ServiceDetailView, tab == "builds" section around line 372)
@core/models.py (Build model around line 739)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix author duplication and add expandable row structure</name>
  <files>
    core/templates/core/services/_build_row.html
    core/templates/core/services/_build_row_expanded.html
  </files>
  <action>
    1. In `_build_row.html`:
       - Wrap the entire row in an Alpine.js scope: `x-data="{ expanded: false }"`
       - Make the row clickable to toggle expansion: `@click="expanded = !expanded"` with `cursor-pointer`
       - Remove the Actions column (td) entirely - the link will move to expanded section
       - Verify author column only displays once (the template looks correct, the bug may be in data - check `build.author` is not being duplicated in the avatar alt attribute in a way that renders twice)
       - Add a chevron indicator that rotates when expanded (use existing SVG patterns in codebase)

    2. Create `_build_row_expanded.html` as a new template:
       - Render as a `<tr>` that spans all columns using `colspan="6"` (6 columns after removing Actions)
       - Use `x-show="expanded"` with `x-collapse` for smooth animation
       - Content sections:
         a. **For failed/cancelled builds**: Show "Build failed" or "Build cancelled" with status context. Since we don't have error_log field yet, show: status, duration, started_at, completed_at, and a link to view full logs on GitHub (ci_job_url)
         b. **For successful builds**: Show artifact_ref (if present), build timing details, and link to GitHub (ci_job_url)
         c. **For running/pending builds**: Show "Build in progress..." with timing so far
       - Style: slightly darker background (bg-gray-950), padding, rounded corners within the cell

    3. In `_build_row.html`, include the expanded row after the main row:
       ```django
       {% include "core/services/_build_row_expanded.html" with build=build %}
       ```

    Note: The Alpine.js x-data scope must wrap BOTH rows. Since Django templates include creates separate elements, use a template tag or wrap in a `<tbody>` fragment with x-data. Alternative: Use a single `<template x-if>` approach or ensure Alpine scope inheritance works.

    Recommended approach: Wrap in a `<tbody>` per build with x-data:
    ```html
    <tbody x-data="{ expanded: false }">
      <tr @click="expanded = !expanded" class="cursor-pointer ...">
        <!-- main row content -->
      </tr>
      <tr x-show="expanded" x-collapse>
        <td colspan="6">
          <!-- expanded content -->
        </td>
      </tr>
    </tbody>
    ```
  </action>
  <verify>
    - Load the builds tab in browser
    - Author name should appear exactly once per row
    - Clicking a row should expand/collapse the details section
    - Expanded section shows appropriate content based on build status
  </verify>
  <done>
    Author displays once, rows are expandable with status-appropriate details, no Actions column in table header.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add sortable table headers and search field</name>
  <files>
    core/templates/core/services/_builds_tab.html
    core/views/services.py
  </files>
  <action>
    1. In `ServiceDetailView.get_context_data` (tab == "builds" section around line 372):
       - Add sorting support:
         ```python
         # Sorting
         sort_by = self.request.GET.get("sort", "-started_at")  # Default newest first
         valid_sorts = ["started_at", "-started_at", "status", "-status", "duration_seconds", "-duration_seconds"]
         if sort_by not in valid_sorts:
             sort_by = "-started_at"
         builds_qs = builds_qs.order_by(sort_by)
         context["sort_by"] = sort_by
         ```
       - Add search support (before pagination):
         ```python
         # Search
         search_query = self.request.GET.get("q", "").strip()
         if search_query:
             builds_qs = builds_qs.filter(
                 Q(commit_sha__icontains=search_query) |
                 Q(commit_message__icontains=search_query)
             )
         context["search_query"] = search_query
         ```
       - Import Q at top: `from django.db.models import Q`
       - Update pagination links to include sort and search params

    2. In `_builds_tab.html`:
       - Add search input field in the header area (next to status filter):
         ```html
         <input type="text"
                name="q"
                value="{{ search_query }}"
                placeholder="Search commits..."
                class="bg-dark-surface border border-dark-border rounded px-3 py-1.5 text-sm text-dark-text placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-dark-accent w-48"
                hx-get="?tab=builds"
                hx-trigger="input changed delay:300ms, search"
                hx-target="#builds-tab-content"
                hx-include="[name='status'],[name='sort']"
                hx-push-url="true">
         ```

       - Make table headers clickable for sorting. Update each `<th>` to include sort links:
         ```html
         <th class="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
           <a href="?tab=builds&sort={% if sort_by == '-started_at' %}started_at{% else %}-started_at{% endif %}{% if status_filter and status_filter != 'all' %}&status={{ status_filter }}{% endif %}{% if search_query %}&q={{ search_query }}{% endif %}"
              hx-get="?tab=builds&sort={% if sort_by == '-started_at' %}started_at{% else %}-started_at{% endif %}{% if status_filter and status_filter != 'all' %}&status={{ status_filter }}{% endif %}{% if search_query %}&q={{ search_query }}{% endif %}"
              hx-target="#builds-tab-content"
              hx-swap="innerHTML"
              class="flex items-center gap-1 hover:text-gray-200 transition-colors">
             Started
             {% if sort_by == '-started_at' %}
             <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
             {% elif sort_by == 'started_at' %}
             <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clip-rule="evenodd"/></svg>
             {% endif %}
           </a>
         </th>
         ```
       - Apply similar pattern to: Status, Started, Duration columns
       - Commit and Branch columns remain non-sortable (less useful)
       - Remove the Actions column header

       - Update pagination links to preserve sort and search params:
         Add `{% if sort_by %}&sort={{ sort_by }}{% endif %}{% if search_query %}&q={{ search_query }}{% endif %}` to pagination URLs

    3. Add a hidden input for sort in the filter area to include it in HTMX requests:
       ```html
       <input type="hidden" name="sort" value="{{ sort_by|default:'-started_at' }}">
       ```
  </action>
  <verify>
    - Load builds tab - should default to newest first
    - Click "Started" header - should toggle between ascending/descending
    - Type in search box - should filter by commit SHA or message after 300ms delay
    - Sort indicator arrows appear on active sort column
    - Pagination preserves sort and search params
  </verify>
  <done>
    Table headers are sortable with visual indicators, search filters by commit ID/message, all params preserved across pagination.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update table structure and ensure HTMX auto-refresh compatibility</name>
  <files>
    core/templates/core/services/_builds_tab.html
  </files>
  <action>
    1. Update the table structure:
       - Change thead row from 7 columns to 6 (remove Actions)
       - Update column headers: STATUS, COMMIT, BRANCH, AUTHOR, STARTED, DURATION

    2. Update the tbody to use per-build tbody wrapper for Alpine.js scope:
       ```html
       {% for build in builds %}
       <tbody x-data="{ expanded: false }" class="border-b border-dark-border last:border-b-0">
         {% include "core/services/_build_row.html" with build=build %}
       </tbody>
       {% endfor %}
       ```

    3. Ensure HTMX auto-refresh (every 5s for running builds) doesn't break Alpine.js state:
       - The current hx-trigger="every 5s" on the outer div will replace content and reset Alpine state
       - This is acceptable behavior - expanded rows will collapse on refresh
       - Consider adding `hx-swap="morph:innerHTML"` if htmx-ext-morph is available (optional enhancement)
       - For now, document that auto-refresh resets expansion state (expected behavior for changing data)

    4. Update the select status filter to also preserve sort:
       Add `hx-include="[name='q'],[name='sort']"` to the status select element

    5. Remove the old `ordering = ["-created_at"]` default from the view since we now handle sorting explicitly.
       Actually, keep it as fallback but the explicit `.order_by(sort_by)` will override it.
  </action>
  <verify>
    - Table displays 6 columns (no Actions)
    - Filter by status preserves sort order and search query
    - Auto-refresh works for running builds (rows refresh every 5s)
    - Expanding a row then waiting for refresh - row collapses (expected)
  </verify>
  <done>
    Table structure updated to 6 columns, HTMX includes all filter params, auto-refresh works correctly.
  </done>
</task>

</tasks>

<verification>
1. Visual verification:
   - Navigate to a service with builds
   - Author column shows single name (no duplication)
   - 6 columns visible: STATUS, COMMIT, BRANCH, AUTHOR, STARTED, DURATION
   - Sort indicators visible on sortable columns

2. Functional verification:
   - Click "Started" header: builds reorder by date
   - Click again: order reverses
   - Type commit SHA in search: filters immediately
   - Click row: expands to show details
   - Status filter + sort + search all work together
   - Pagination preserves all filters
</verification>

<success_criteria>
- Author name appears exactly once per build row
- Table has 6 columns (Actions removed)
- Default sort is newest first (started_at descending)
- Clicking column headers toggles sort with visual indicator
- Search field filters by commit SHA or message
- Clicking any row expands to show build details
- Expanded section shows: external link, artifact ref (if any), timing details
- Failed/cancelled builds show status context in expanded section
- All filters (status, sort, search) work together and persist through pagination
</success_criteria>

<output>
After completion, create `.planning/quick/034-builds-ui-ux-fixes/034-SUMMARY.md`
</output>
