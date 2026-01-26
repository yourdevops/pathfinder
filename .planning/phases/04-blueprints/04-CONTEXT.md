# Phase 4: Blueprints - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Platform engineers can publish service templates (blueprints) from git URLs; developers can browse available blueprints filtered by project connections. Blueprints display metadata synced from ssp-template.yaml and show available git tag versions. Service creation using blueprints is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Blueprint listing
- Compact list layout (table-style rows with columns), not cards
- Flat list with filter controls, not grouped by plugin or category
- Full details visible: name, description, tags, ci.plugin, deploy.plugin, version count, last synced
- Filter by tags and deploy plugin via controls (not grouped sections)

### Registration flow
- Single URL field entry — paste git URL, click register
- Save blueprint record immediately, sync runs in background (async)
- Blueprint shows "Syncing..." status until complete
- Sync errors shown as status badge on detail page with expandable error message
- Auto-detect GitHub connection — use first available, prompt if none exist

### Version management
- Dropdown selector on blueprint detail page for choosing version
- Latest semantic version auto-selected as default (v1.2.3 > v1.2.2)
- Pre-release versions (alpha, beta, rc) hidden by default
- Toggle to reveal pre-releases when needed
- Any version (including betas) selectable during service creation (Phase 5)

### Availability filtering
- Unavailable blueprints (no matching deploy connection) shown but dimmed in list
- Tooltip on dimmed items: "Requires [plugin] connection"
- Global catalog view: filters based on any connection in the system
- Project context view: filters based on connections attached to that project
- Toggle control: "Show unavailable" (default: hidden)
- Clicking dimmed blueprint opens detail page with setup hint banner: "Add a [plugin] connection to use this blueprint"

### Claude's Discretion
- Tags display style (badges vs text)
- Exact filter UI placement and controls
- Loading states during sync
- Column sorting behavior

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-blueprints*
*Context gathered: 2026-01-26*
