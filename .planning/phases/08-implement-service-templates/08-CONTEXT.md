# Phase 8: Implement Service Templates - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the template registration system and integrate templates into the service creation wizard. Operators can register git repos as templates via `pathfinder.yaml` manifests, sync versions via git tags, and developers select templates when creating services to get pre-populated scaffolding and environment variables. The design docs in `docs/templates/` are the authoritative implementation guide.

</domain>

<decisions>
## Implementation Decisions

### Template list & detail UI
- Table layout for templates list (like Steps/Repos pages), not cards
- Table columns: name, description, runtimes, version count, sync status, last synced
- Template detail is a single scrollable page with sections (not tabbed)
- Version list on detail page shows tag + synced date only — no per-version manifest metadata
- Templates get their own top-level expandable section in the sidebar navigation

### Wizard template picker UX
- Template selection is a dropdown selector (not visual cards) — same pattern as the CI Workflow selector on the wizard's CI step
- Version dropdown appears below the template dropdown when a template is selected — same pattern as CI Workflow version picker
- No visual indicator that pre-populated vars came from the template — per design doc: "no template origin marker"
- Template filtering in wizard: if Project has a `ProjectTemplateConfig` with allowed templates, use that list; if nothing is pinned, show all registered templates

### Registration & sync flow
- Single page registration form: SCM connection dropdown + git URL + Register button
- Sync status visible in both list table and detail page
- Webhook registration uses abstract plugin method for setting up webhooks/branch protection rules from the selected SCM connection — consistent with plugin architecture
- Template deregistration is hard delete with guard — blocked if any service references this template
- Tags that disappear from remote on sync are flagged as unavailable but not deleted from Pathfinder

### Model & data references
- Template model lives in the core app (alongside Service, Project, etc.)
- Service references template via FK to Template + text field for version string
- FK to Template enables deletion guard; version is a historical text reference, not an FK
- Separate `ProjectTemplateConfig` model for project-level template settings (allowed templates M2M, default template FK) — not merged into ProjectCIConfig

### Scaffolding task
- Replace the existing `scaffold_repository` task entirely — it's a leftover from old Blueprints
- New scaffolding for new repos: fetch template at selected tag's commit SHA, copy file tree excluding `pathfinder.yaml`, apply variable substitution, include CI Workflow manifest if assigned — one atomic operation
- Existing repo onboarding: CI workflow manifest push remains a separate mechanism (existing `push_ci_manifest` task)
- Scaffold status tracking per design doc: pending → success/failed

### Claude's Discretion
- Exact sync status indicators and badge styling
- HTMX patterns for manual sync button refresh
- Form validation UX for registration errors
- Template detail page section ordering and spacing

</decisions>

<specifics>
## Specific Ideas

- Template selector in wizard should match the CI Workflow selector pattern exactly — dropdown with version picker below
- Project template config follows the same pattern as ProjectCIConfig — separate model, separate settings section
- The `docs/templates/` folder (design.md, template-registration.md, README.md) and `docs/wizard.md` are the authoritative design references for all implementation decisions
- `docs/env-vars.md` defines the variable cascade behavior that templates feed into

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-implement-service-templates*
*Context gathered: 2026-02-24*
