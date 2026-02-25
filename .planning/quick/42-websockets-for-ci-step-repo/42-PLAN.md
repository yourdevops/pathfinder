---
phase: quick-42
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/consumers.py
  - core/routing.py
  - core/templates/core/ci_workflows/repo_detail.html
  - core/templates/core/ci_workflows/_scan_status.html
  - core/templates/core/ci_workflows/_sync_history.html
  - core/views/ci_workflows.py
  - theme/templates/base.html
autonomous: true
requirements: [QUICK-42]

must_haves:
  truths:
    - "Sync History table updates in real-time when a scan completes without page refresh"
    - "Imported Steps section updates with new/changed/archived steps after scan without page refresh"
    - "Scan status badge transitions (pending -> scanning -> scanned) in real-time via WebSocket"
    - "Repository info (last scanned, branch protection) updates after scan via WebSocket"
  artifacts:
    - path: "core/consumers.py"
      provides: "StepsRepoConsumer with polling and OOB rendering"
      contains: "class StepsRepoConsumer"
    - path: "core/routing.py"
      provides: "WebSocket URL route for steps repo"
      contains: "ws/repos/"
    - path: "core/templates/core/ci_workflows/repo_detail.html"
      provides: "WebSocket connection wrapper and OOB target IDs"
      contains: "ws-connect"
  key_links:
    - from: "core/templates/core/ci_workflows/repo_detail.html"
      to: "/ws/repos/<id>/"
      via: "hx-ext=ws ws-connect"
      pattern: "ws-connect.*ws/repos"
    - from: "core/consumers.py"
      to: "core/templates/core/ci_workflows/_sync_history.html"
      via: "render_to_string with oob=True"
      pattern: "render_to_string.*_sync_history"
---

<objective>
Add WebSocket real-time updates to the CI Steps Repository detail page so that Sync History, Imported Steps, scan status, and repository info update live without page refresh.

Purpose: When adding a new repo or triggering a scan, the user currently has to manually refresh the page to see updated sync logs, imported steps, and scan status. This should feel interactive and responsive, matching the service detail page's WebSocket pattern from Phase 09.

Output: StepsRepoConsumer with poll loop, OOB-targetable partials on repo_detail.html, real-time updates for all dynamic sections.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/consumers.py (ServiceConsumer pattern to follow)
@core/routing.py (add new route)
@core/templates/core/ci_workflows/repo_detail.html (main page)
@core/templates/core/ci_workflows/_scan_status.html (scan badge partial)
@core/templates/core/ci_workflows/_sync_history.html (sync history table)
@core/views/ci_workflows.py (StepsRepoDetailView context)
@core/models.py (StepsRepository, StepsRepoSyncLog, CIStep models)
@theme/templates/base.html (wsStatus Alpine component, fallback warning JS)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create StepsRepoConsumer and add WebSocket route</name>
  <files>
    core/consumers.py
    core/routing.py
  </files>
  <action>
Add a new StepsRepoConsumer class to core/consumers.py following the exact same pattern as ServiceConsumer:

1. **StepsRepoConsumer** in core/consumers.py:
   - Accept `repo_id` from URL route kwargs (integer, same pattern as service_id)
   - Verify repo exists via `_repo_exists()` using `StepsRepository.objects.filter(id=self.repo_id).exists()`
   - `get_current_state()` fetches all data needed for change detection:
     - `repo.scan_status`, `repo.scan_error`, `repo.last_scanned_at`, `repo.protection_valid`, `repo.last_scanned_sha`
     - Active step count and list of step IDs+names+phases (for detecting new/changed/archived steps)
     - Sync logs: last 20 entries with their status, trigger, commit_sha, steps_added/updated/archived, started_at
     - Runtime families count
   - `compute_hash()` reuse the static method from ServiceConsumer (or call the same hashlib pattern)
   - `build_template_context(state)` queries fresh data mirroring StepsRepoDetailView.get() context:
     - `repo` (StepsRepository instance with select_related('connection'))
     - `steps_by_phase` (OrderedDict grouped by phase, same logic as view)
     - `total_steps` (active count)
     - `archived_steps` (archived queryset)
     - `runtimes` (repo.runtimes.all())
     - `sync_logs` (last 20, prefetch_related('entries'))
     - `can_manage = False` (WS push is read-only, no CSRF for forms)
     - `can_delete = False` (read-only)
     - `workflows_using` (CIWorkflow objects using steps from this repo)
   - `render_updates(state)` renders OOB partials and concatenates:
     - `_scan_status.html` with `oob=True` (target: `#scan-status`)
     - `_sync_history.html` with `oob=True` (target: `#sync-history-table`)
     - Imported steps section rendered inline as an OOB div (target: `#imported-steps`)
     - Repository info card (target: `#repo-info`)
   - Poll interval: 3 seconds (same as ServiceConsumer)
   - Import models inside `@database_sync_to_async` methods to avoid AppRegistryNotReady

2. **routing.py**: Add the new route:
   ```python
   path("ws/repos/<int:repo_id>/", StepsRepoConsumer.as_asgi()),
   ```
   Import StepsRepoConsumer alongside ServiceConsumer.

IMPORTANT: For the OOB partials rendering, the _scan_status.html and _sync_history.html templates need to support conditional `hx-swap-oob` via the established pattern (`{% if oob %}hx-swap-oob="true"{% endif %}`). This will be handled in Task 2 which modifies templates. In the consumer, just set `ctx["oob"] = True` before rendering.

For the imported steps section, render a complete HTML snippet directly in the consumer (not a separate partial) since the repo_detail.html inline template structure is complex with phase grouping. Use `render_to_string` with a new `_imported_steps.html` partial that encapsulates the steps-by-phase loop.

Actually, create TWO new partial templates rendered by the consumer:
- `_imported_steps.html` - the steps-by-phase section (extracted from repo_detail.html lines 138-176)
- `_repo_info.html` - the repository info card (extracted from repo_detail.html lines 47-83)

These partials will be created in Task 2. In this task, just write the consumer assuming they exist.
  </action>
  <verify>
    <automated>cd /Users/fandruhin/work/yourdevops/pathfinder && uv run python manage.py check</automated>
  </verify>
  <done>StepsRepoConsumer exists with poll loop, state hashing, and OOB rendering. WebSocket route registered at /ws/repos/&lt;id&gt;/. Django check passes.</done>
</task>

<task type="auto">
  <name>Task 2: Add OOB targets to templates and wire WebSocket connection</name>
  <files>
    core/templates/core/ci_workflows/repo_detail.html
    core/templates/core/ci_workflows/_scan_status.html
    core/templates/core/ci_workflows/_sync_history.html
    core/templates/core/ci_workflows/_imported_steps.html
    core/templates/core/ci_workflows/_repo_info.html
  </files>
  <action>
Modify templates to support WebSocket OOB swaps following the Phase 09 pattern:

1. **repo_detail.html** - Add WebSocket connection and OOB target IDs:
   - Wrap the main content div with `hx-ext="ws" ws-connect="/ws/repos/{{ repo.id }}/"` (same pattern as service detail.html)
   - Add the disconnected warning banner (copy from service detail.html, id="ws-fallback-warning")
   - The `#scan-status` div already exists (line 22) -- good, it wraps the scan status partial
   - Replace the inline sync history section (lines 129-135) with: `<div id="sync-history-table">{% if sync_logs %}{% include "core/ci_workflows/_sync_history.html" %}{% endif %}</div>` -- keeping the h2 header outside the OOB target
   - Extract the imported steps section (lines 138-176) into `_imported_steps.html` partial. Replace inline content with: `<div id="imported-steps">{% include "core/ci_workflows/_imported_steps.html" %}</div>` -- keeping the h2 header outside
   - Extract the repository info card (lines 47-83) into `_repo_info.html` partial. Replace inline with: `<div id="repo-info">{% include "core/ci_workflows/_repo_info.html" %}</div>`
   - Keep the archived steps section, workflows using section, and runtime families section as-is (these change rarely and are not high-priority for live updates)

2. **_scan_status.html** - Add OOB support:
   - Wrap the entire content in a `<div id="scan-status-inner" {% if oob %}hx-swap-oob="true"{% endif %}>` wrapper div
   - Remove the HTMX polling attributes (`hx-get`, `hx-trigger="every 3s"`, `hx-target`, `hx-swap`) from the scanning and pending status spans since WebSocket now handles live updates
   - The consumer will render this partial with `oob=True`

3. **_sync_history.html** - Add OOB support:
   - Add `{% if oob %}hx-swap-oob="true"{% endif %}` and `id="sync-history-table"` to the root div (the `<div class="bg-dark-surface...">`)
   - No other changes needed; the consumer renders this with the full sync_logs context

4. **_imported_steps.html** (NEW) - Extract from repo_detail.html:
   - Root element: `<div id="imported-steps" {% if oob %}hx-swap-oob="true"{% endif %}>`
   - Content: the steps_by_phase loop (lines 140-175 from repo_detail.html)
   - Include the `{% if steps_by_phase %}...{% else %}...empty state...{% endif %}` conditional
   - Template needs `steps_by_phase`, `total_steps`, `repo` context variables
   - Load humanize tag at top since naturaltime may not be needed here, but keep consistent

5. **_repo_info.html** (NEW) - Extract from repo_detail.html:
   - Root element: `<div id="repo-info" {% if oob %}hx-swap-oob="true"{% endif %}>`
   - Content: the repository info card (lines 47-83 from repo_detail.html) -- the grid with Default Branch, Connection, Last Scanned, Created, Branch Protection, plus the scan_error block
   - Template needs `repo` context variable
   - Load humanize for naturaltime

6. **Update the consumer's render_updates** (back in consumers.py) to render these partials:
   - `render_to_string("core/ci_workflows/_scan_status.html", ctx)` for scan status OOB
   - `render_to_string("core/ci_workflows/_sync_history.html", ctx)` for sync history OOB
   - `render_to_string("core/ci_workflows/_imported_steps.html", ctx)` for imported steps OOB
   - `render_to_string("core/ci_workflows/_repo_info.html", ctx)` for repo info OOB

Note on the scan status OOB target: The existing `#scan-status` div in repo_detail.html wraps the include. The consumer's OOB swap needs to target an ID on the partial's root element. Use `id="scan-status-inner"` on the partial's wrapper div, and add a matching `<div id="scan-status-inner">` wrapper in repo_detail.html around the existing include. The consumer targets `scan-status-inner` via OOB.

IMPORTANT CSP compatibility: No inline scripts needed. The wsStatus Alpine component and fallback warning JS are already in base.html from Phase 09. The `hx-ext="ws"` and `ws-connect` are standard htmx-ext-ws attributes that work without CSP issues.
  </action>
  <verify>
    <automated>cd /Users/fandruhin/work/yourdevops/pathfinder && uv run python manage.py check && make build</automated>
  </verify>
  <done>
    - repo_detail.html has WebSocket connection via hx-ext="ws" ws-connect
    - Scan status, sync history, imported steps, and repo info all have OOB target IDs
    - HTMX polling removed from _scan_status.html (replaced by WebSocket push)
    - All four OOB partials render correctly via both HTTP include and WebSocket push
    - make build succeeds (templates valid, static files collected)
  </done>
</task>

</tasks>

<verification>
1. Register a new steps repo or trigger a rescan on an existing one
2. Without refreshing the page, observe:
   - Scan status badge transitions from "Scanning..." to "Scanned" automatically
   - Sync History table gains a new row showing the completed scan
   - Imported Steps section updates with any newly discovered steps
   - Repository info card updates "Last Scanned" timestamp
3. WebSocket connection status dot appears in the browser (if service nav is visible) or connection is verifiable via browser DevTools Network/WS tab
4. Opening browser DevTools should show WebSocket connection to /ws/repos/&lt;id&gt;/ with periodic messages only when state changes
</verification>

<success_criteria>
- StepsRepoConsumer polls every 3s, detects state changes via SHA-256 hash, sends OOB HTML only on change
- Sync History table, Imported Steps, scan status badge, and repo info all update in real-time
- No HTMX polling remains on the repo detail page (WebSocket replaces it entirely)
- Existing HTTP rendering still works (OOB attributes only added when oob=True)
- Django check passes, make build succeeds
</success_criteria>

<output>
After completion, create `.planning/quick/42-websockets-for-ci-step-repo/42-SUMMARY.md`
</output>
