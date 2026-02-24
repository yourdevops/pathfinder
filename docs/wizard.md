# Service Creation Wizard

Status: actual guideline for implementation

A 5-page wizard for creating new Services. Built on `django-formtools` `SessionWizardView` with session-based state. A progress bar with numbered step indicators tracks completion throughout the flow.

Every page has "Back" and "Next" buttons to navigate without losing wizard data.

---

### Page 1 — Service

**Project** (required)
- Select from active projects the user has access to
- If the wizard is launched from a project context (`/projects/<name>/services/create/`), the project is pre-filled and locked

**Service Name** (required)
- DNS-compatible: lowercase letters, numbers, hyphens (RFC 1123 label format, max 63 chars)
- Uniqueness validated within the selected project
- Combined handler `{project-name}-{service-name}` must not exceed 63 chars total

---

### Page 2 — Repository

**SCM Connection** (required)
- Selects a `ProjectConnection` for the chosen project
- The project's default connection is pre-selected automatically

**Repository Mode** (required, radio select)
- **Create new repository** (default) — repo is created via the SCM plugin during scaffolding. Auto-generated repo name: `{project-name}-{service-name}` (shown as preview)
- **Use existing repository** — enter the repository URL directly

**Template Picker** (only when "Create new" is selected)
- Visual cards showing template name, description, and runtime badges
- **"None (empty repository)"** is selected by default
- When a template is selected, a **version dropdown** appears (populated from cached version records, latest selected by default)
- Hidden when "Use existing" is selected — you cannot scaffold a template into an existing repo

The Service Template is a "golden path" that defines what type of service this is, what runtimes it needs, and what configuration is required. By selecting a template during repository setup, the wizard can pre-populate environment variables and recommend compatible CI Workflows. Templates are an enhancement, not a gate — services can be created without one.

For template manifest format and lifecycle, see [Template Design](templates/design.md).

**Branch** (required, default: `main`)
- For new repos: the default branch name
- For existing repos: the base branch for the feature PR (label changes to "Base Branch")

---

### Page 3 — CI Workflow

**CI Workflow** (optional)
- Visual card selector listing all CI Workflows approved for the project
- Each workflow shows: name, runtime constraint badges, artifact type badge, and description
- The project's `default_workflow` (from `ProjectCIConfig`) is pre-selected if configured

**Version** (appears when a workflow is selected)
- Dropdown of `AUTHORIZED` versions, with `DRAFT` versions included only if `project.ci_config.allow_draft_workflows` is enabled
- "Not pinned" means latest authorized version is used

**No Workflow** is a valid choice — selecting it shows a warning: *"Service will be saved in Draft status — A CI Workflow is required to transition the service to Active status."*

If a template was selected on Page 2 and declares `runtimes`, compatible workflows are shown first. All workflows remain accessible.

---

### Page 4 — Configuration

Environment variables for the new service, using the unified env vars model (see [Environment Variables](env-vars.md)).

**System variables** (read-only, locked)
- `SERVICE_NAME` = `{service-name}` — injected automatically, cannot be removed or changed

**Inherited from Project** (read-only, collapsible section)
- Project-level variables with their values and lock state
- Each variable shows either a "Locked" or "Inherited" badge
- Shown for awareness — edit them in Project settings, not here

**Service variables** (editable)
- If a template was selected on Page 2 and declares `required_vars`, those are **pre-populated** as rows: key filled from the manifest, description shown as helper text, value empty, lock off. After creation, these are plain service-level variables — no "template origin" marker
- Keys are auto-uppercased and sanitized to `[A-Z][A-Z0-9_]*` format
- The operator can fill in values, toggle lock, remove variables, or add new ones via "+ Add Variable"
- If no template was selected, this section starts empty

Info note: *"You can leave values empty now — operator will be asked to fill these values on specific Deployment Environment level."*

---

### Page 5 — Review & Confirm

Read-only summary of all selections:
- Project name, service name, service handler (shown in monospace)
- Repository mode ("New repository" or "Existing repository") and branch
- Existing repository URL (if applicable)
- CI Workflow name and pinned version (or "None" / "Not pinned")
- Service-level environment variables (if any)
- A "What happens next" info box (different text for new vs existing repo)

**Confirmation checkbox** (required): *"I confirm the service configuration is correct"*

No changes are made until the operator confirms.

---

## Scaffolding Execution

After confirmation, Pathfinder executes the following. The `scaffold_repository` task runs as a background job (queue: `repository_scaffolding`). The service detail page polls scaffold status via HTMX every 3 seconds while the task is running.

**Scaffold status** is set to `"pending"` if scaffolding is needed, otherwise `"not_required"`:
- Scaffolding is needed when: `repo_is_new == True` OR a CI Workflow is assigned
- Existing repo with no workflow: no scaffolding needed

### New repository

1. Create repository via the SCM plugin
2. If a template was selected: fetch template at the selected tag's commit SHA, copy file tree to the new repo **excluding `pathfinder.yaml`**
3. Apply variable substitution (`service_name`, `project_name`, `service_handler`) to template files
4. If a CI Workflow was selected: push CI Workflow manifest to the repo (`ci_manifest_status` → `"synced"`)
5. Commit and push to the default branch
6. Create the Service record with `status="draft"` and all collected data. The record stores the template name and version as plain text fields (`template_name`, `template_version`) for audit trail — not as a foreign key
7. Register webhook (if supported by SCM plugin)

### Existing repository

1. Create a feature branch `feature/{service-name}` from the base branch
2. If a CI Workflow was selected: include CI manifest in the branch (`ci_manifest_status` → `"pending_pr"`)
3. Commit, push, and open a pull request to the base branch
4. Create the Service record, store env vars

### Post-creation

- On completion: `scaffold_status` updated to `"success"` or `"failed"`, `repo_url` filled in for new repos
- Success message varies by new/existing/CI workflow combination
- User is redirected to project detail page

### Error handling

- On failure: show error, allow retry or cancel
- If PR creation fails: create service anyway, show warning with manual PR link
