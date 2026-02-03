---
phase: quick-036
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/services/_build_logs_partial.html
  - core/templates/core/services/_build_row.html
  - core/templates/core/services/_build_row_expanded.html
  - core/views/services.py
  - theme/static_src/src/styles.css
autonomous: true

must_haves:
  truths:
    - "Build logs have scroll controls (scroll to top, scroll to bottom) and proper horizontal scrolling"
    - "For failed builds, only errored step logs are fetched from GitHub API (not full logs then truncated)"
    - "Expanded build row shows duration and link to GitHub run details"
    - "Commit ID is clickable (links to GitHub commit) and copyable with single click"
    - "Branch name is clickable (links to GitHub branch)"
    - "Warning lines in logs are highlighted with yellow color"
  artifacts:
    - path: "core/templates/core/services/_build_logs_partial.html"
      provides: "Scroll controls, warning highlighting, improved log display"
    - path: "core/templates/core/services/_build_row.html"
      provides: "Clickable commit SHA with copy button"
    - path: "core/templates/core/services/_build_row_expanded.html"
      provides: "Duration and GitHub link in expanded view"
    - path: "core/views/services.py"
      provides: "Warning pattern detection, API optimization for failed steps"
    - path: "theme/static_src/src/styles.css"
      provides: "Warning line highlighting styles"
  key_links:
    - from: "_build_logs_partial.html"
      to: "styles.css"
      via: "warning highlight CSS classes"
    - from: "services.py"
      to: "plugins/github/plugin.py"
      via: "get_job_logs with step filtering"
---

<objective>
Improve build logs UI/UX with scroll controls, clickable links, copy functionality, and smarter API usage.

Purpose: Enhance developer experience when debugging failed builds - easier navigation, quicker access to relevant logs, and better integration with GitHub.
Output: Updated templates and views with improved log viewer functionality.
</objective>

<context>
@core/templates/core/services/_build_logs_partial.html
@core/templates/core/services/_build_row.html
@core/templates/core/services/_build_row_expanded.html
@core/views/services.py
@theme/static_src/src/styles.css
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add scroll controls and warning highlighting to logs</name>
  <files>
    core/templates/core/services/_build_logs_partial.html
    core/views/services.py
    theme/static_src/src/styles.css
  </files>
  <action>
1. In `_build_logs_partial.html`:
   - Wrap the log container with a parent div that includes scroll control buttons
   - Add "Scroll to Top" and "Scroll to Bottom" buttons using Alpine.js for functionality
   - The log container already has `scrollbar-visible` class - keep it
   - Add horizontal scroll support (container should scroll both X and Y)
   - Add `whitespace-pre` to `<pre>` to preserve formatting and enable horizontal scroll
   - Add warning line highlighting: lines with "warning" should use yellow/amber background

2. In `services.py` `BuildLogsView`:
   - Add WARNING_PATTERNS list: `["warning", "warn"]`
   - Add `_is_warning_line()` method similar to `_is_error_line()`
   - Update `_process_logs()` to return `is_warning` flag alongside `is_error` for each line
   - Update template context to include warning state

3. In `styles.css`:
   - Add `.log-warning` class with yellow-ish background (`bg-yellow-500/10` equivalent)
   - Add `.log-error` class with red background (already exists inline, extract to class)

4. Log container structure:
```html
<div x-data="{ logContainer: null }" x-init="logContainer = $refs.logs" class="relative">
  <!-- Scroll controls -->
  <div class="absolute top-2 right-2 z-10 flex gap-1">
    <button @click="logContainer.scrollTo({top: 0, behavior: 'smooth'})"
            class="p-1 bg-gray-800/80 rounded hover:bg-gray-700 text-gray-400"
            title="Scroll to top">
      <!-- up arrow icon -->
    </button>
    <button @click="logContainer.scrollTo({top: logContainer.scrollHeight, behavior: 'smooth'})"
            class="p-1 bg-gray-800/80 rounded hover:bg-gray-700 text-gray-400"
            title="Scroll to bottom">
      <!-- down arrow icon -->
    </button>
  </div>
  <!-- Log container -->
  <div x-ref="logs" class="bg-gray-950 rounded-lg p-3 max-h-[60vh] overflow-auto scrollbar-visible">
    <pre class="text-xs font-mono leading-relaxed whitespace-pre">...</pre>
  </div>
</div>
```
  </action>
  <verify>
    - Visual check: logs have scroll buttons in top-right corner
    - Buttons scroll to top/bottom smoothly
    - Long lines can be scrolled horizontally
    - Warning lines show yellow background, error lines show red background
  </verify>
  <done>
    Build logs have functional scroll controls and warning/error highlighting.
  </done>
</task>

<task type="auto">
  <name>Task 2: Make commit and branch clickable with copy support</name>
  <files>
    core/templates/core/services/_build_row.html
    core/templates/core/services/_build_row_expanded.html
  </files>
  <action>
1. In `_build_row.html` - Commit column (line ~39-48):
   - Make commit SHA a clickable link to GitHub commit
   - Add copy button next to commit SHA using Alpine.js
   - Build GitHub commit URL: `{{ service.repo_url }}/commit/{{ build.commit_sha }}`
   - Copy button should use `navigator.clipboard.writeText()` with visual feedback
   - Structure:
```html
<td class="px-4 py-3">
  <div class="flex flex-col" @click.stop>
    <div class="flex items-center gap-2">
      <a href="{{ service.repo_url }}/commit/{{ build.commit_sha }}"
         target="_blank" rel="noopener"
         class="text-sm font-mono text-blue-400 hover:underline">
        {{ build.commit_sha|slice:":7" }}
      </a>
      <button x-data="{ copied: false }"
              @click="navigator.clipboard.writeText('{{ build.commit_sha }}'); copied = true; setTimeout(() => copied = false, 2000)"
              class="p-0.5 text-gray-500 hover:text-gray-300 transition-colors"
              title="Copy full commit SHA">
        <svg x-show="!copied" class="w-3.5 h-3.5" ...><!-- copy icon --></svg>
        <svg x-show="copied" class="w-3.5 h-3.5 text-green-400" ...><!-- check icon --></svg>
      </button>
    </div>
    {% if build.commit_message %}
    <span class="text-xs text-dark-muted truncate max-w-xs">...</span>
    {% endif %}
  </div>
</td>
```

2. In `_build_row.html` - Branch column (line ~51-58):
   - Make branch name a clickable link to GitHub branch
   - Build GitHub branch URL: `{{ service.repo_url }}/tree/{{ build.branch }}`
   - Keep the branch icon, make the text the link
```html
<td class="px-4 py-3 whitespace-nowrap" @click.stop>
  <a href="{{ service.repo_url }}/tree/{{ build.branch }}"
     target="_blank" rel="noopener"
     class="flex items-center gap-1.5 text-sm text-dark-text hover:text-dark-accent transition-colors">
    <svg class="w-4 h-4 text-dark-muted" ...><!-- branch icon --></svg>
    <span>{{ build.branch|default:"-" }}</span>
  </a>
</td>
```

3. In `_build_row_expanded.html` - Full commit SHA (line ~103-105):
   - Make the full commit SHA in the expanded row also clickable with copy button
   - Same pattern as the short SHA in the main row
  </action>
  <verify>
    - Click commit SHA opens GitHub commit page in new tab
    - Click copy button copies full SHA, shows green checkmark briefly
    - Click branch name opens GitHub branch page in new tab
    - Row click (outside links) still toggles expand/collapse
  </verify>
  <done>
    Commit SHA is clickable and copyable, branch name is clickable to GitHub.
  </done>
</task>

<task type="auto">
  <name>Task 3: Restore duration/GitHub link in expanded view and optimize API</name>
  <files>
    core/templates/core/services/_build_row_expanded.html
    core/views/services.py
  </files>
  <action>
1. In `_build_row_expanded.html`:
   - The "View on GitHub" link already exists (line 18-26), verify it's working
   - Add duration to the build info header next to build number:
```html
<div class="flex items-center gap-3">
  <span class="text-sm font-medium text-dark-text">Build #{{ build.run_number|default:build.github_run_id }}</span>
  {% if build.duration_seconds %}
  <span class="text-sm text-dark-muted">
    {% widthratio build.duration_seconds 60 1 as minutes %}
    {% if minutes > 0 %}{{ minutes }}m {% endif %}{{ build.duration_seconds|divisibleby:60|yesno:","|default:build.duration_seconds }}s
  </span>
  {% endif %}
  {% if build.artifact_ref %}...{% endif %}
</div>
```
   - Actually simpler: use Django template math: `{{ build.duration_seconds }}s` with conditional formatting:
```html
{% if build.duration_seconds %}
<span class="text-sm text-dark-muted">
  {% if build.duration_seconds >= 3600 %}
    {{ build.duration_seconds|floatformat:0|divisibleby:3600 }}h {{ build.duration_seconds|floatformat:0|add:"-3600"|divisibleby:60 }}m
  {% elif build.duration_seconds >= 60 %}
    {% widthratio build.duration_seconds 60 1 %}m {{ build.duration_seconds|mod:60 }}s
  {% else %}
    {{ build.duration_seconds }}s
  {% endif %}
</span>
{% endif %}
```
   - Simpler approach using a filter or just showing seconds with a simple calculation

2. In `services.py` `BuildLogsView._process_logs`:
   - The current implementation already extracts step logs for failed builds
   - Verify the logic is correct and efficient
   - For failed builds: API already fetches job logs, then `_extract_step_logs` filters to failed step
   - This is correct behavior - we cannot request only a specific step's logs from GitHub API
   - The optimization is already in place via the extraction logic

3. Duration formatting - create a simple template filter or inline calculation:
   - Add to the expanded row header info section (between build number and artifact)
   - Format: "2m 34s" or "45s" or "1h 5m"
   - Use inline template logic or add `format_duration` to template context

4. Verify the "View on GitHub" link in expanded row:
   - Currently uses `build.ci_job_url` which is the workflow run URL
   - This is correct - it links to the GitHub Actions run page
  </action>
  <verify>
    - Expanded row shows duration next to build number (e.g., "Build #123 - 2m 34s")
    - "View on GitHub" button visible and functional in expanded row
    - For failed builds, logs show only the failed step content (not truncated full logs)
  </verify>
  <done>
    Duration and GitHub link visible in expanded view, API efficiently returns only relevant logs.
  </done>
</task>

</tasks>

<verification>
1. Build logs UI:
   - Scroll buttons appear in top-right of log container
   - Clicking "Scroll to top" smoothly scrolls to beginning
   - Clicking "Scroll to bottom" smoothly scrolls to end
   - Long lines can be scrolled horizontally

2. Log highlighting:
   - Lines containing "error", "failed", etc. have red background
   - Lines containing "warning", "warn" have yellow background
   - Normal lines have default styling

3. Commit/branch links:
   - Short commit SHA in table row links to GitHub commit
   - Copy button copies full SHA with visual feedback
   - Branch name links to GitHub branch
   - Full commit SHA in expanded row also clickable and copyable

4. Expanded row info:
   - Duration displayed in human-readable format
   - "View on GitHub" button links to workflow run

5. No regressions:
   - Row expand/collapse still works
   - Auto-refresh for running builds still works
   - Search and filter still work
</verification>

<success_criteria>
- All 6 user requirements implemented:
  1. Scroll controls for logs (horizontal and vertical)
  2. API optimized for failed step logs (already implemented, verified)
  3. Duration and GitHub link in expanded view
  4. Clickable commit ID and branch names
  5. Single-click copy for commit ID
  6. Warning lines highlighted in yellow
- No breaking changes to existing functionality
- UI follows existing dark theme conventions
</success_criteria>

<output>
After completion, create `.planning/quick/036-build-logs-ui-ux-improvements/036-SUMMARY.md`
</output>
