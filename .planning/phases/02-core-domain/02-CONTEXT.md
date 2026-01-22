# Phase 2: Core Domain - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Projects with membership roles and Environments with deploy targets. Platform engineers can organize work into Projects; developers have scoped access via group membership. Projects contain Environments (deployment contexts) with env vars that inherit from project level.

</domain>

<decisions>
## Implementation Decisions

### Project Membership UX
- Member list grouped by role (Owners, Contributors, Viewers sections)
- Groups assigned to projects, not individual users
- Group displayed as expandable name only (click to see members)
- Admin, Operator, and Project Owner can assign/reassign groups and roles
- No minimum owner requirement (admins can always manage)
- "Add Group" modal: search/select group first, then pick role
- No timestamps on member list (keep it clean)
- Edit mode toggle to reveal remove options (not inline buttons)

### Environment Presentation
- List/table view for environments within project
- Production flag shown via row styling (different background/border)
- Minimal row content for Phase 2: name + default badge only
- Env vars in accordion/expandable section
- Inherited vars shown with "inherited" badge, can override
- First created environment becomes default
- Default can be changed in environment settings
- Dedicated creation page for new environments

### Project Navigation
- Claude's discretion on tab layout (lean toward context-replacing sidebar with back button, AWS/Jenkins pattern)
- Project header: name + description only
- Services tab is default when opening project
- HTMX partial swap for tab content (no full page reload)
- Distinct URLs for each tab (/projects/uuid/services, etc.)
- Settings tab: single page with sections (not nested tabs)
- Project list: table/list view with columns: name, description, environments count, last activity

### Sidebar Navigation Restructure
- Full restructure in Phase 2 (not deferred)
- DevSSP logo/icon as home button
- Projects (links to list, no inline expansion)
- Blueprints (catalog, placeholder for Phase 4)
- Integrations (placeholder for Phase 3)
- Settings (admin-only): General, User Management (Users, Groups), Audit & Logs, API/Tokens, Notifications
- Documentation (external link to docs site)
- User profile at bottom: slide-out panel with user info, links, logout

### Empty States
- No projects: minimal text + Create Project button
- No environments: "Add your first environment" prompt
- No members: empty list with "No groups assigned" help text
- Project creation: modal for basics, then redirect to settings tab

### Claude's Discretion
- Exact tab layout implementation (responsive, mobile-friendly)
- Row styling specifics for production environments
- Slide-out panel design details
- Column sorting and filtering on project list
- Additional best-practice columns on project list

</decisions>

<specifics>
## Specific Ideas

- Context-replacing sidebar pattern (like AWS Console, Jenkins) — when entering a project, project nav replaces main nav with back button
- "I would want to see number of Services deployed and last deployment at a glance" — deferred to later phases when deployments exist
- Horizontal tabs should be scrollable on mobile if chosen over sidebar pattern

</specifics>

<deferred>
## Deferred Ideas

- Environment row showing service count, last deployment, health status — requires Phase 5-7 (Services, Builds, Deployments)
- API and Tokens settings section — future phase
- Notifications settings section — future phase
- Documentation content — external docs site

</deferred>

---

*Phase: 02-core-domain*
*Context gathered: 2026-01-22*
