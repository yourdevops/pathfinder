# Phase 3: Integrations - Context

**Gathered:** 2026-01-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Platform engineers can register and health-check GitHub and Docker connections. Plugins provide isolated, self-contained connection handlers. Projects can attach SCM connections; environments can attach deploy connections. Services using these connections are built in Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Plugin Architecture
- Plugins isolated from core app — removable without breaking functionality
- Each plugin provides its own registration form, using core CSS styling
- Auto-discovery from `plugins/` directory for valid plugin packages
- Core defines URL namespace (`/integrations/<plugin>/<connection>/`), plugins add routes within
- Claude decides: URL routing approach (callback functions vs urlpatterns)
- Filesystem deletion of plugin = orphan connections with "Plugin missing" warning
- UI deletion of plugin blocked if any connection uses it
- Connections show usage counter on card; full usage list on connection detail page
- Connection deletion blocked if any service uses it; allowed if just attached but unused

### Connection Registration
- Dedicated page for each connection type (not modal from list)
- Step wizard for complex connections (GitHub: Auth → Webhook → Confirm)
- "Test Connection" button available but optional — save allowed without passing test
- Claude decides: Docker form approach (wizard with fewer steps or simple single-page form)

### Health Status Display
- Status pill indicator: "Healthy" (green), "Unhealthy" (red), "Unknown" (gray)
- Periodic background checks with configurable interval (General Settings, default 15 min)
- Checks spread evenly across interval to avoid load spikes
- Manual "Check Now" bypasses schedule for immediate result
- Hover/click shows: last check time + response summary
- No notification on health state change (visual indicator only)

### Credential Handling
- Sensitive fields (API keys, private keys) completely hidden after save — no reveal option
- Editing: empty field = keep existing value; fill in to replace
- Claude decides: encryption approach (fitting Django + SQLite stack)
- Only Admins and Operators can create/edit connections

### Project/Environment Attachment
- SCM connections attached via Project Settings tab
- Multiple SCM connections per project allowed
- Multiple deploy connections per environment allowed
- Only Operators can attach/detach connections
- UI: Grouped sections (SCM, CI, Deploy) with list per section
- Each list item shows: connection name, plugin name, status pill, link to detail
- "+ Add Connection" button per category opens modal with pre-filtered available connections
- Detach blocked if any service uses that connection
- Connection detail page shows which services actually use the connection

### Claude's Discretion
- Docker registration form structure (wizard or single-page)
- URL routing approach for plugins
- Encryption implementation for sensitive fields

</decisions>

<specifics>
## Specific Ideas

- "Plugins should be isolated from the core app — removable without breaking core functionality"
- Connections should work like physical resources: show usage count on cards, block deletion until unused
- Health checks spread evenly across interval to avoid "waves of load"
- Attachment UI grouped by category (SCM, CI, Deploy) — each with its own section and add button

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-integrations*
*Context gathered: 2026-01-23*
