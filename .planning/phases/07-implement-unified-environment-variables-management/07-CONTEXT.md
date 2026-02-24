# Phase 7: Implement Unified Environment Variables Management - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Bring the environment variables system into alignment with `docs/env-vars.md`. Build a unified, reusable UI component for env var editing across all levels (project, service, environment, wizard). Implement the full cascade resolution with system-injected PTF_* variables, lock enforcement at project and service levels, and the description field. Prepare the deployment gate resolution logic. Two environment contexts exist: Project > Environment (shared across services) and Service > Environment (full resolved cascade for a specific service+environment combo).

</domain>

<decisions>
## Implementation Decisions

### Unified UI component — Layout
- Stacked rows, not a full table. Each variable as a horizontal row with key=value inline, badges/actions on the right
- Inline editing (click to edit in place), not modal dialogs
- Add variable via "Add variable" button that reveals an empty inline editable row at the bottom
- Variables grouped by source level: upstream (read-only) vars shown first with visual separator, then current-level editable vars below

### Unified UI component — Lock icon
- Lock icon on the LEFT side of each row, with three visual states:
  - **Ghost/missing** (not locked) — clickable, switches to locked on this level
  - **Calm red** (locked on this level) — clickable, removes lock
  - **Grey** (locked on upstream level) — not clickable, hover tooltip: "Locked on {source} level"

### Unified UI component — Description & Source
- Description shown as tooltip on hover over the key (not always visible)
- Source level (System, Project, Service, Environment) included in the tooltip alongside description: "From: {source}. {description}"
- Small info/pencil icon next to the key opens a popover for editing the description
- Keeps rows compact — no separate columns for source or description

### Unified UI component — Empty values
- Empty values shown as muted italic "not set" text
- On the Service > Environment resolved view, empty values get an amber warning highlight (proactive signal before deployment)

### Cascade & resolution
- Lock support at Project and Service levels only (Environment is terminal, no effect until deployment vars exist)
- System-injected PTF_* variables (PTF_PROJECT, PTF_SERVICE, PTF_ENVIRONMENT) computed at resolution time, never stored in JSONField
- Existing SERVICE_NAME variable replaced with PTF_SERVICE (no backwards compatibility needed)
- Both environment contexts show resolved views:
  - Project > Environment: resolved view without service-specific vars (System + Project + Environment)
  - Service > Environment: fully resolved cascade (System + Project + Service + Environment)

### Variable shape
- Add `description` field to the variable shape: `{key, value, lock, description}`
- All CRUD operations updated to handle description
- Template manifests seed descriptions from `required_vars` into the description field
- Description inherited from upstream when downstream overrides value, unless downstream provides its own

### Wizard integration
- Same unified component used in the service creation wizard (consistent UX everywhere)
- All PTF_* vars shown in wizard: PTF_PROJECT (from selected project), PTF_SERVICE (from entered name), note that PTF_ENVIRONMENT will be injected per-environment
- Template required_vars seeded as empty-value rows with descriptions from manifest, no special "template" badge
- Info note placement for empty values: Claude's discretion

### Deployment gate
- Implement cascade resolution utility function and empty-value check in this phase
- Actual gate enforcement deferred to when deployments are implemented
- Gate error message should list each empty variable with direct links to the correct level's settings page where the value should be set

### Claude's Discretion
- Info note placement in wizard for empty values (banner vs per-row hint)
- Exact styling/spacing of stacked rows
- Resolution function implementation approach (model method vs standalone utility)
- Whether to build a full gate UI preview or just the resolution function

</decisions>

<specifics>
## Specific Ideas

- Lock icon three-state design is a key UX element — ghost (unlockable), calm red (locked here), grey (locked upstream with tooltip)
- Tooltip combines source and description to save horizontal space: "From: project. PostgreSQL connection string"
- Two distinct environment contexts are critical: Project-level env settings (shared) vs Service-level env settings (service-specific cascade)
- Design reference: `docs/env-vars.md` is the authoritative spec

</specifics>

<deferred>
## Deferred Ideas

- Deployment-level variables (5th cascade level) — future phase when deployments are implemented
- Env var encryption (values currently stored unencrypted in JSONField) — separate security concern
- Automatic stale variable detection — design doc explicitly says manual management by operator

</deferred>

---

*Phase: 07-implement-unified-environment-variables-management*
*Context gathered: 2026-02-24*
