# Phase 5: Services - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Service creation wizard and service management pages. Developers can create services via a 4-page wizard that scaffolds repositories from blueprints. Services are tracked with their builds and deployments. Build webhooks and deployment execution are separate phases (6 and 7).

</domain>

<decisions>
## Implementation Decisions

### Deploy Type Scope
- Phase 5 supports **container deployments only** via Docker plugin
- Serverless and static deploy types deferred to future phases
- Blueprint's `deploy.type: container` is the only supported type for now

### Project Tab Structure
- Keep current 3-tab layout: **Services | Environments | Settings**
- Members section remains inside Settings tab (per quick-017)
- Services tab is default landing page for projects

### Service List Display
- **Table/list view** for services (not card-based)
- Columns: name, status, template, last activity
- Click row to navigate to service detail

### Wizard Flow Experience
- Step titles bar for progress: "Blueprint" → "Repository" → "Configuration" → "Review"
- Navigation: can click completed steps to go back, no skipping ahead
- Hybrid validation: name availability validates inline, other fields validate on Next
- Warn before leaving: browser confirmation dialog on navigate-away mid-wizard

### Wizard Page 3: Configuration
- Page 3 shows **service-level environment variables only**
- No port/resources/health check configuration in Phase 5
- Technology-specific configuration deferred to future iterations
- Page always displayed, but zero env vars is valid (user can click Next)
- Default variable: `SERVICE_NAME=<service-name>` (locked from override at environment level)
- Inheritance: show inherited project vars in expandable section, allow adding service-specific vars

### Repository Flow
- Support **both** new repo creation AND existing repo scaffolding
- **New repos:** Create repo, push template to `main` branch
- **Existing repos:** Create `feature/{service-name}` branch, apply template, open PR
- Branch prefix hardcoded to `feature/` (not configurable)
- Repo naming: project prefix pattern — service "payment-api" in project "acme" creates repo "acme-payment-api"
- Initial content: blueprint's ssp-template.yaml specifies what to include (blueprint decides)
- Architecture: local git operations (scaffolding) via `git_utils.py`, plugin-specific actions (list repos, PRs) via SCM plugins

### Service Detail Page
- Uses **context-replacing sidebar** (like project detail)
- Sidebar nav items: **Details, Builds, Environments**
- **Details** = Overview + Settings combined on single page
- **Builds** tab always shown (even if no builds yet) — placeholder for Phase 6
- **Environments** tab shows deployment information per environment — placeholder for Phase 7
- Permissions: editable fields for contributors/owners, read-only for viewers
- Status display: badge with color near title — "Draft" (gray), "Active" (green), "Error" (red)
- Back button: returns to project's Services list

### Claude's Discretion
- Environments tab detail level (deployment history depth)
- Table column specifics and sorting
- Empty state messaging
- Loading states and HTMX update patterns
- Exact validation error message styling
- Service sidebar layout and icons

</decisions>

<specifics>
## Specific Ideas

- Service list should follow existing table patterns in the codebase
- Service detail sidebar mirrors project detail sidebar behavior
- "Deploy Now" checkbox only available for new repo creation (per wizard.md)
- For existing repos, deployment waits until PR merged and first build completes
- Wizard step titles should feel clear and action-oriented
- Combined detail/settings view avoids unnecessary tab switching for quick edits
- Locked SERVICE_NAME variable ensures services always know their identity

</specifics>

<deferred>
## Deferred Ideas

- **Serverless deploy type** (Lambda/Cloud Functions) — future phase
- **Static deploy type** (S3/CDN) — future phase
- **Port/resource/health configuration** — future iteration when blueprints define these
- **Configurable branch prefix** — could add to SiteConfiguration later
- **Blueprint-defined environment variables with defaults** — deferred to later enhancement

</deferred>

---

*Phase: 05-services*
*Context gathered: 2026-01-26*
