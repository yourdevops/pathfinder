# Phase 5: Services - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Developers can create services through a multi-step wizard that scaffolds repositories from blueprints. Service detail pages show metadata and status with a context-replacing sidebar. Creating repos, linking existing repos, and configuring service-specific environment variables are in scope. Builds (Phase 6) and Deployments (Phase 7) remain placeholders.

</domain>

<decisions>
## Implementation Decisions

### Wizard flow experience
- Step titles bar for progress: "Blueprint" → "Repository" → "Container" → "Review"
- Navigation: can click completed steps to go back, no skipping ahead
- Hybrid validation: name availability validates inline, other fields validate on Next
- Warn before leaving: browser confirmation dialog on navigate-away mid-wizard

### Repository scaffolding
- New or existing repo: user chooses to scaffold new repo OR link existing
- Repo naming: project prefix pattern — service "payment-api" in project "acme" creates repo "acme-payment-api"
- Initial content: blueprint's ssp-template.yaml specifies what to include (blueprint decides)
- Branch setup: single "main" branch only
- Architecture: local git operations (scaffolding) via `git_utils.py`, plugin-specific actions (list repos, PRs) via SCM plugins

### Container configuration
- Fields: environment variables only for now; blueprint-driven configuration deferred
- Default variable: `SERVICE_NAME=<service-name>` (locked from override at environment level)
- Inheritance: show inherited project vars in expandable section, allow adding service-specific vars

### Service detail page
- Tabs: unified "Service" view (metadata + settings combined), Builds (placeholder for Phase 6)
- Permissions: editable fields for contributors/owners, read-only for viewers (no separate Settings tab)
- Status display: badge with color near title — "Draft" (gray), "Active" (green), "Error" (red)
- Context sidebar: service gets its own sidebar (like projects)
- Back button: returns to project's Services list

### Claude's Discretion
- HTMX update patterns for wizard steps
- Exact validation error message styling
- Placeholder content for Builds tab
- Service sidebar layout and icons
- Expandable section animation/styling

</decisions>

<specifics>
## Specific Ideas

- Wizard step titles should feel clear and action-oriented
- Combined detail/settings view avoids unnecessary tab switching for quick edits
- Locked SERVICE_NAME variable ensures services always know their identity

</specifics>

<deferred>
## Deferred Ideas

- Blueprint-defined environment variables with defaults (deferred to later enhancement)
- Container configuration fields (port, resources, health check) — blueprint should define what's configurable
- Deployments tab — Phase 7

</deferred>

---

*Phase: 05-services*
*Context gathered: 2026-01-26*
