# Phase 4: Blueprints - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Platform engineers can publish service templates (blueprints) from git URLs; developers can browse available blueprints filtered by project connections. Blueprints display metadata synced from ssp-template.yaml and show available git tag versions. Service creation using blueprints is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### SCM Abstraction
- SCM operations abstract from specific plugins — use Git protocol, not plugin-specific APIs
- At registration: select SCM provider if repository requires auth, "None" option for public repos
- Admins can edit SCM provider and URL after blueprint creation (supports migration scenarios like Bitbucket → GitHub)

### Registration Flow
- Immediate fetch + preview when operator enters git URL — show parsed manifest before committing
- Block registration if ssp-template.yaml is invalid or missing — cannot proceed without valid manifest
- Single page form layout with URL, SCM provider selection, and live preview panel
- After successful registration, redirect to blueprint detail page

### Blueprint Listing
- Compact list layout (table-style rows with columns), not cards
- Flat list with filter controls, not grouped by plugin or category
- Full details visible: name, description, tags, ci.plugin, deploy.plugin, version count, last synced
- Filter by tags and deploy plugin via controls (not grouped sections)

### Version Management
- Dropdown selector on blueprint detail page for choosing version
- Latest semantic version auto-selected as default (v1.2.3 > v1.2.2)
- Pre-release versions (alpha, beta, rc) hidden by default
- Toggle to reveal pre-releases when needed
- Any version (including betas) selectable during service creation (Phase 5)

### Availability Filtering
- Unavailable blueprints (no matching deploy connection) shown but dimmed in list
- Tooltip on dimmed items: "Requires [plugin] connection"
- Global catalog view: filters based on any connection in the system
- Project context view: filters based on connections attached to that project
- Toggle control: "Show unavailable" (default: hidden)
- Clicking dimmed blueprint opens detail page with setup hint banner: "Add a [plugin] connection to use this blueprint"

### Claude's Discretion
- Tags display style (badges vs text)
- Exact filter UI placement and controls
- Loading states during fetch/preview
- Column sorting behavior
- Error state handling and retry patterns

</decisions>

<specifics>
## Specific Ideas

- Git only (no Mercurial or other VCS) — simplifies implementation
- Preview should show parsed manifest fields (name, description, tags, plugins) before committing

</specifics>

<deferred>
## Deferred Ideas

- Bitbucket plugin support — future phase (architecture supports multiple SCM providers)

</deferred>

---

*Phase: 04-blueprints*
*Context gathered: 2026-01-26*
