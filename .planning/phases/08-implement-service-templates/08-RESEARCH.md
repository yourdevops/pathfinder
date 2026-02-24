# Phase 8: Implement Service Templates - Research

**Researched:** 2026-02-24
**Domain:** Django models, views, templates, HTMX patterns, git operations for template registration and wizard integration
**Confidence:** HIGH

## Summary

Phase 8 introduces a complete template registration system and integrates templates into the service creation wizard. The implementation touches four areas: (1) new models for Template, TemplateVersion, and ProjectTemplateConfig, (2) CRUD views and templates for template list/detail/register/deregister, (3) wizard integration with a template dropdown selector and version picker on the Repository step, and (4) a rewritten `scaffold_repository` task that fetches template files at a specific tag's commit SHA, copies them excluding `pathfinder.yaml`, applies variable substitution, and optionally includes the CI Workflow manifest.

The codebase already provides extensive infrastructure to build on: `git_utils.py` has `clone_repo_shallow`, `clone_repo_full`, `list_tags_from_repo`, `parse_version_tag`, `apply_template_to_directory`, `build_authenticated_git_url`, and Jinja2-based variable substitution. The `StepsRepository` registration pattern (model + connection FK + webhook setup + scan task) is the direct analog for template registration. The `ciWorkflowSelector` Alpine.js component and its versions-map pattern in the wizard workflow step provide the exact template for building the template selector dropdown with version picker.

**Primary recommendation:** Follow the StepsRepository/CIWorkflow patterns exactly. The models, views, forms, templates, and HTMX patterns are mature and consistent — replicating them for Service Templates minimizes risk and keeps the codebase uniform.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Template list & detail UI
- Table layout for templates list (like Steps/Repos pages), not cards
- Table columns: name, description, runtimes, version count, sync status, last synced
- Template detail is a single scrollable page with sections (not tabbed)
- Version list on detail page shows tag + synced date only — no per-version manifest metadata
- Templates get their own top-level expandable section in the sidebar navigation

#### Wizard template picker UX
- Template selection is a dropdown selector (not visual cards) — same pattern as the CI Workflow selector on the wizard's CI step
- Version dropdown appears below the template dropdown when a template is selected — same pattern as CI Workflow version picker
- No visual indicator that pre-populated vars came from the template — per design doc: "no template origin marker"
- Template filtering in wizard: if Project has a `ProjectTemplateConfig` with allowed templates, use that list; if nothing is pinned, show all registered templates

#### Registration & sync flow
- Single page registration form: SCM connection dropdown + git URL + Register button
- Sync status visible in both list table and detail page
- Webhook registration uses abstract plugin method for setting up webhooks/branch protection rules from the selected SCM connection — consistent with plugin architecture
- Template deregistration is hard delete with guard — blocked if any service references this template
- Tags that disappear from remote on sync are flagged as unavailable but not deleted from Pathfinder

#### Model & data references
- Template model lives in the core app (alongside Service, Project, etc.)
- Service references template via FK to Template + text field for version string
- FK to Template enables deletion guard; version is a historical text reference, not an FK
- Separate `ProjectTemplateConfig` model for project-level template settings (allowed templates M2M, default template FK) — not merged into ProjectCIConfig

#### Scaffolding task
- Replace the existing `scaffold_repository` task entirely — it's a leftover from old Blueprints
- New scaffolding for new repos: fetch template at selected tag's commit SHA, copy file tree excluding `pathfinder.yaml`, apply variable substitution, include CI Workflow manifest if assigned — one atomic operation
- Existing repo onboarding: CI workflow manifest push remains a separate mechanism (existing `push_ci_manifest` task)
- Scaffold status tracking per design doc: pending → success/failed

### Claude's Discretion
- Exact sync status indicators and badge styling
- HTMX patterns for manual sync button refresh
- Form validation UX for registration errors
- Template detail page section ordering and spacing

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 6.x | Web framework, ORM, views | Project foundation |
| django-formtools | >=2.5.1 | SessionWizardView for service creation wizard | Already used for the 5-step wizard |
| PyYAML | >=6.0.3 | Parse `pathfinder.yaml` manifest files | Already used for CI step parsing |
| semver | >=3.0.4 | Parse and validate semver tags | Already used in `parse_version_tag()` |
| Jinja2 | >=3.1.6 | Template variable substitution in scaffolded files | Already used in `apply_template_to_directory()` |
| GitPython | (installed) | Clone repos, list tags, checkout at specific commits | Already used throughout `git_utils.py` |
| Alpine.js CSP | (vendored) | Dropdown selectors, sidebar toggle | Already used for `ciWorkflowSelector`, `repoModeToggle` |
| HTMX | (vendored) | Partial page updates, wizard step swaps, poll refresh | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-auditlog | (installed) | Audit trail for Template model changes | Register Template model like other models |
| django-tasks | (installed) | Background task queue for sync operations | Enqueue `sync_template` like `scan_steps_repository` |

### No New Dependencies Required
All required capabilities exist in the current dependency set. No new packages needed.

## Architecture Patterns

### Recommended File Structure
```
core/
├── models.py                    # Add: Template, TemplateVersion, ProjectTemplateConfig
├── forms/
│   └── templates.py             # NEW: TemplateRegisterForm
├── views/
│   └── templates.py             # NEW: TemplateListView, TemplateDetailView, etc.
├── tasks.py                     # Modify: rewrite scaffold_repository, add sync_template
├── git_utils.py                 # Modify: replace old manifest reader, add pathfinder.yaml parser
├── urls.py                      # Add: templates_patterns
├── templates/core/
│   ├── templates/               # NEW directory for template CRUD templates
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── register.html
│   └── services/wizard/
│       └── _fields_repository.html  # Modify: add template picker section
theme/templates/
├── base.html                    # Modify: add Alpine.data('templateSelector') component
└── core/components/
    └── nav.html                 # Modify: add Templates expandable section
```

### Pattern 1: Model Design — Template + TemplateVersion
**What:** Two models: `Template` (registration record keyed on manifest `name`) and `TemplateVersion` (one per semver git tag)
**When to use:** Template registration and version tracking
**How it maps to existing patterns:**
- `Template` parallels `StepsRepository` — both have `name`, `git_url`, `connection` FK, `sync_status`, `last_synced_at`
- `TemplateVersion` parallels `CIWorkflowVersion` in concept but is much simpler — just `tag_name`, `commit_sha`, `synced_at`, `available` boolean
- `ProjectTemplateConfig` parallels `ProjectCIConfig` — `OneToOneField(Project)`, `default_template` FK, `allowed_templates` M2M

**Key fields for Template:**
```python
class Template(models.Model):
    name = models.CharField(max_length=63, unique=True, validators=[dns_label_validator])
    description = models.TextField(blank=True)
    git_url = models.URLField(max_length=500)
    connection = models.ForeignKey(IntegrationConnection, on_delete=models.SET_NULL, null=True, blank=True)
    runtimes = models.JSONField(default=list)        # e.g., [{"python": ">=3.11"}]
    required_vars = models.JSONField(default=dict)   # e.g., {"DATABASE_URL": "description"}
    sync_status = models.CharField(...)              # pending/syncing/synced/error
    sync_error = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True)
    last_synced_sha = models.CharField(max_length=40, blank=True)
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Key fields for TemplateVersion:**
```python
class TemplateVersion(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='versions')
    tag_name = models.CharField(max_length=100)      # e.g., "v2.1.0"
    commit_sha = models.CharField(max_length=40)
    available = models.BooleanField(default=True)     # False if tag disappeared from remote
    synced_at = models.DateTimeField(auto_now_add=True)
    sort_key = models.CharField(max_length=100, blank=True)  # for ordering
```

**Service model additions:**
```python
# Add to existing Service model:
template = models.ForeignKey('Template', on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
template_version = models.CharField(max_length=100, blank=True)  # text, not FK — historical reference
```

### Pattern 2: Registration Flow — Mirror StepsRepoRegister
**What:** Single-page form with SCM connection dropdown + git URL, then backend clones repo, reads `pathfinder.yaml`, validates, creates Template + initial versions
**When to use:** Template registration
**Source pattern:** `StepsRepoRegisterView` in `core/views/ci_workflows.py` lines 57-116

The flow:
1. Form: connection dropdown (from `IntegrationConnection` where plugin is SCM type) + git URL
2. POST handler: shallow clone default branch HEAD, read `pathfinder.yaml`, validate `kind: ServiceTemplate` + `name` uniqueness
3. Create `Template` record keyed on manifest `name` (not user-provided name)
4. Full clone to list tags, create `TemplateVersion` records for semver tags
5. Webhook registration via plugin (push + tag events)
6. Redirect to template detail page

### Pattern 3: Sync Task — Mirror scan_steps_repository
**What:** Background task that re-clones template repo, re-reads manifest metadata, refreshes tag list
**When to use:** Manual sync button, webhook trigger
**Source pattern:** `scan_steps_repository` in `core/tasks.py`

Key differences from steps scan:
- No step discovery — just manifest metadata + tag list
- Tags that vanish from remote get `available=False` (not deleted)
- HEAD SHA skip optimization (same as steps scan)

### Pattern 4: Wizard Template Selector — Mirror ciWorkflowSelector
**What:** Alpine.js component with dropdown + version picker, using hidden inputs for form submission
**When to use:** Wizard Page 2 (Repository step)
**Source pattern:** `_fields_workflow.html` and `ciWorkflowSelector` Alpine.data component in `base.html`

Key implementation details:
- Register `Alpine.data('templateSelector', ...)` in `base.html` alongside `ciWorkflowSelector`
- Template dropdown shows all available templates (or project-filtered if `ProjectTemplateConfig.allowed_templates` is set)
- Version dropdown appears when template is selected, populated from a versions-map JSON (same pattern as workflow versions)
- Hidden inputs: `repository-template_id` and `repository-template_version_tag`
- Only visible when repo_mode is "new" (per design doc)
- When template selected: on review step and configuration step, pre-populate required_vars from the selected template version's manifest

### Pattern 5: Scaffolding Rewrite
**What:** Replace the current `scaffold_repository` task with template-aware scaffolding
**When to use:** Service creation with template selected
**Source pattern:** Current `scaffold_repository` + `scaffold_new_repository` in `tasks.py` / `git_utils.py`

New flow for new repos with template:
1. Create empty repo via plugin (existing)
2. Clone template repo at selected tag's commit SHA (new — use `git checkout <sha>` after clone)
3. Copy file tree excluding `pathfinder.yaml` (update `apply_template_to_directory` exclude list)
4. Apply Jinja2 variable substitution (existing)
5. If CI workflow assigned: generate and include manifest (existing)
6. Commit and push (existing)

Key changes to `apply_template_to_directory`:
- Update exclude list: `["pathfinder.yaml", ".git"]` (remove old `ssp-template.yaml`, `pathfinder-template.yaml`)
- The function itself is fine — just the exclude list needs updating

Key changes to `read_manifest_from_repo`:
- Replace entirely: new function reads `pathfinder.yaml`, validates `kind: ServiceTemplate`, returns parsed dict
- Old `ssp-template.yaml` / `pathfinder-template.yaml` references removed

### Pattern 6: Sidebar Navigation
**What:** Add "Templates" as a new expandable section in the sidebar
**Source pattern:** `nav.html` — follows identical structure to "CI Workflows" section

```
Templates (expandable)
  ├── Templates (list view)
```

Uses `$persist` for toggle state, same pattern as other sections.

### Anti-Patterns to Avoid
- **Don't put template logic in plugins.** Template registration, sync, and manifest parsing are core concerns. The plugin is only used for authenticated git clone and webhook registration.
- **Don't create a separate Django app for templates.** The decision says templates live in `core/` alongside Service, Project, etc.
- **Don't use an FK for template_version on Service.** The decision explicitly says text field for version — it's a historical reference that survives template deregistration.
- **Don't auto-delete TemplateVersion records when tags vanish.** Flag as `available=False` instead.
- **Don't add template origin markers to env vars.** The design doc explicitly says "no template origin marker" — vars seeded from template are plain service-level variables after creation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semver parsing | Custom regex | `semver` library + existing `parse_version_tag()` | Edge cases with pre-release, build metadata |
| Git tag listing | API calls | `git.Repo.tags` via existing `list_tags_from_repo()` | Provider-agnostic, already implemented |
| Authenticated git clone | Manual URL building | Existing `build_authenticated_git_url()` | Handles credential scrubbing, plugin abstraction |
| File tree copy with substitution | Custom walker | Existing `apply_template_to_directory()` | Handles binary files, text detection, Jinja2 |
| Dropdown selector component | Custom Alpine | Replicate `ciWorkflowSelector` pattern | Proven pattern, CSP-safe, already working |
| Form wizard state | Custom session handling | `django-formtools SessionWizardView` | Already manages the 5-step wizard |
| YAML parsing | Custom parser | `PyYAML yaml.safe_load` | Already used for CI step files |

**Key insight:** The existing codebase has 95% of the infrastructure needed. The main new code is the Template/TemplateVersion models, the registration view, the sync task, and the wizard template selector component. Everything else is pattern replication.

## Common Pitfalls

### Pitfall 1: Manifest name collision during registration
**What goes wrong:** Two template repos could have `name: python-fastapi` in their manifests
**Why it happens:** Name is the unique identity, not the git URL
**How to avoid:** Validate uniqueness of `name` against existing Template records during registration. Return clear error: "Template 'python-fastapi' is already registered"
**Warning signs:** IntegrityError on Template.name unique constraint

### Pitfall 2: Template version selected in wizard but repo HEAD has changed
**What goes wrong:** Scaffolding uses HEAD instead of the selected tag's commit SHA
**Why it happens:** Shallow clone defaults to HEAD
**How to avoid:** Clone then checkout specific commit: `repo.git.checkout(commit_sha)` after clone. Or use `git clone --branch <tag>` for exact tag checkout
**Warning signs:** Scaffolded files don't match expected template version

### Pitfall 3: pathfinder.yaml excluded from scaffold but Jinja2 variables in it cause errors
**What goes wrong:** Template variable substitution tries to process pathfinder.yaml before exclusion
**Why it happens:** Order of operations — copy then substitute vs exclude then copy
**How to avoid:** The existing `apply_template_to_directory` already excludes files before copy. Just ensure `pathfinder.yaml` is in the exclude list
**Warning signs:** Jinja2 TemplateError on `{{ }}` expressions in the manifest

### Pitfall 4: Wizard form data lost when adding template picker
**What goes wrong:** Adding hidden inputs for template selection breaks SessionWizardView form validation
**Why it happens:** django-formtools validates form data on each step; unrecognized fields cause issues
**How to avoid:** Add `template_id` and `template_version_tag` as proper form fields (CharField, required=False, HiddenInput widget) to `RepositoryStepForm`
**Warning signs:** Form validation errors on step 2, lost data on back navigation

### Pitfall 5: Alpine.js CSP build issues with template selector
**What goes wrong:** Multi-expression handlers fail silently
**Why it happens:** Alpine CSP build only supports single expressions per directive
**How to avoid:** Register `templateSelector` via `Alpine.data()` in `base.html` using `function()` syntax (not arrow functions). All method calls from templates must be single expressions
**Warning signs:** Dropdown doesn't open, version list doesn't update, silent failures

### Pitfall 6: Hard delete guard fails with orphaned FK references
**What goes wrong:** Template deregistration blocked even after services are deleted
**Why it happens:** Soft-deleted or archived services still hold FK references
**How to avoid:** Use `Template.services.exists()` to check if any Service references this template. `on_delete=models.SET_NULL` on the FK means deleting a template won't cascade, but the guard prevents deletion when references exist
**Warning signs:** "Cannot delete template — services reference it" when no visible services exist

### Pitfall 7: Tag ancestry check fails on shallow clones
**What goes wrong:** `git merge-base --is-ancestor` needs full history to work
**Why it happens:** Shallow clone doesn't have the commit graph
**How to avoid:** Use full clone for tag validation, or use `git fetch --unshallow` before ancestry check. For initial registration, a full clone is already needed to get all tags
**Warning signs:** Valid tags rejected as "not on main branch"

## Code Examples

### Reading pathfinder.yaml manifest
```python
# Source: design docs + existing read_manifest_from_repo pattern
import yaml

def read_pathfinder_manifest(repo_path: str) -> dict:
    """Read and validate pathfinder.yaml from template repo root."""
    manifest_path = os.path.join(repo_path, "pathfinder.yaml")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("pathfinder.yaml not found in repository root")

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("pathfinder.yaml must be a YAML mapping")
    if data.get("kind") != "ServiceTemplate":
        raise ValueError(f"Expected kind: ServiceTemplate, got: {data.get('kind')}")
    if not data.get("name"):
        raise ValueError("name field is required in pathfinder.yaml")

    # Validate name is DNS-compatible
    name = data["name"]
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        raise ValueError(f"name '{name}' must be DNS-compatible")

    return data
```

### Filtering semver tags from repo
```python
# Source: existing list_tags_from_repo + parse_version_tag patterns
import semver as semver_lib

def get_semver_tags(repo):
    """Return list of semver tags sorted newest-first."""
    tags = list_tags_from_repo(repo)
    semver_tags = []
    for tag_info in tags:
        tag_name = tag_info["name"]
        # Strip leading v/V
        version_str = tag_name.lstrip("vV")
        try:
            semver_lib.Version.parse(version_str)
            parsed = parse_version_tag(tag_name)
            semver_tags.append({**tag_info, **parsed})
        except ValueError:
            continue  # Skip non-semver tags
    # Sort by sort_key descending (newest first)
    semver_tags.sort(key=lambda t: t["sort_key"], reverse=True)
    return semver_tags
```

### Alpine.js templateSelector component (CSP-safe)
```javascript
// Source: ciWorkflowSelector pattern in base.html
Alpine.data('templateSelector', function(initialTpl, initialVer, versionsMap) {
    return {
        tplVal: String(initialTpl),
        tplOpen: false,
        verVal: String(initialVer),
        verOpen: false,
        versions: [],
        init: function() {
            this.versions = versionsMap[this.tplVal] || [];
        },
        pickTpl: function(id) {
            this.tplVal = id;
            this.tplOpen = false;
            this.versions = versionsMap[id] || [];
            this.verVal = this.versions.length > 0 ? this.versions[0].tag : '';
            this.verOpen = false;
        },
        pickVer: function(tag) {
            this.verVal = tag;
            this.verOpen = false;
        }
    };
});
```

### Checkout at specific tag commit SHA
```python
# Source: GitPython docs + existing clone patterns
def clone_at_tag(git_url, tag_commit_sha, auth_url=None):
    """Clone repo and checkout specific commit for template scaffolding."""
    repo, temp_dir = clone_repo_full(git_url, auth_url=auth_url)
    repo.git.checkout(tag_commit_sha)
    return repo, temp_dir
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ssp-template.yaml` / `pathfinder-template.yaml` | `pathfinder.yaml` with `kind: ServiceTemplate` | Phase 8 (now) | Old manifest filenames removed, new `pathfinder.yaml` is the standard |
| Blueprints (Phase 4 BPRT-01..06) | Service Templates | Phase 8 (now) | Complete replacement — different model, different UX, different scaffolding |
| `scaffold_repository` passes `template_temp_dir=None` | Template-aware scaffolding with tag-specific checkout | Phase 8 (now) | Scaffolding actually uses templates now |

**Deprecated/outdated:**
- `read_manifest_from_repo()` in `git_utils.py` — reads old `ssp-template.yaml` / `pathfinder-template.yaml`. Replace with `pathfinder.yaml` reader
- `apply_template_to_directory()` exclude list includes old manifest names. Update to `["pathfinder.yaml", ".git"]`
- The `scaffold_repository` task currently passes `template_temp_dir=None` unconditionally — the entire scaffolding flow needs rewriting

## Open Questions

1. **Tag ancestry validation timing**
   - What we know: Design doc says validate that tagged commit is reachable from main via `git merge-base --is-ancestor`
   - What's unclear: Should this happen at registration (for all initial tags) or only on webhook-triggered tag push? Validating all tags at registration could be slow for repos with many tags
   - Recommendation: Validate on tag-push webhook only. At registration, accept all semver tags. Add ancestry check as a future enhancement if needed

2. **Webhook payload handling for template repos**
   - What we know: Webhooks for push and tag events need to trigger sync. The existing GitHub webhook handler at `plugins/github/webhooks.py` handles `workflow_run` events for builds
   - What's unclear: Whether to extend the existing webhook handler or create a separate endpoint for template webhooks
   - Recommendation: Extend the existing webhook handler to detect template-repo events by matching the repository URL against registered templates. This keeps a single webhook URL per plugin

3. **Template selection persistence across wizard back-navigation**
   - What we know: The CI workflow selector restores previous selection via `get_cleaned_data_for_step('workflow')`
   - What's unclear: Since template selection is on step 2 (repository), and step 2 data is already managed by SessionWizardView, this should work automatically
   - Recommendation: Add template_id and template_version_tag fields to RepositoryStepForm. SessionWizardView handles persistence. Test back-navigation carefully

## Sources

### Primary (HIGH confidence)
- **Codebase exploration** — `core/models.py`, `core/views/services.py`, `core/views/ci_workflows.py`, `core/forms/services.py`, `core/tasks.py`, `core/git_utils.py`, `plugins/base.py`, `plugins/github/plugin.py`
- **Design documents** — `docs/templates/design.md`, `docs/templates/template-registration.md`, `docs/templates/README.md`, `docs/wizard.md`, `docs/env-vars.md`
- **Template files** — `core/templates/core/services/wizard/_fields_workflow.html`, `core/templates/core/services/wizard/_fields_repository.html`, `core/templates/core/components/nav.html`, `theme/templates/base.html`

### Secondary (MEDIUM confidence)
- Django `on_delete=SET_NULL` vs `PROTECT` behavior for FK guard pattern — verified via Django docs knowledge

### Tertiary (LOW confidence)
- None — all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all tools already in project
- Architecture: HIGH — all patterns directly replicate existing codebase patterns
- Pitfalls: HIGH — identified from direct code reading of existing implementations

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable — internal codebase patterns)
