# Phase 7: Implement Unified Environment Variables Management - Research

**Researched:** 2026-02-24
**Domain:** Django models, HTMX inline editing, Alpine.js CSP, cascade resolution logic
**Confidence:** HIGH

## Summary

Phase 7 brings the environment variables system into alignment with `docs/env-vars.md`. The current codebase already stores env vars as JSONField arrays on Project, Service, and Environment models with `{key, value, lock}` shape. The main work involves: (1) adding the `description` field to the variable shape, (2) renaming `SERVICE_NAME` to `PTF_SERVICE` and adding `PTF_PROJECT`/`PTF_ENVIRONMENT` system-injected variables, (3) building a unified stacked-row UI component with inline editing, three-state lock icon, and tooltip-based description/source display, (4) implementing the full cascade resolution function, and (5) wiring the unified component into all four contexts (project settings, service settings, environment detail, wizard).

The project already has established HTMX patterns (click-to-edit via modal, `hx-target`/`hx-swap` on rows), Alpine.js CSP patterns (`Alpine.data()` registration, `alpine:init` event), and Django view patterns (mixin-based views with `ProjectOwnerMixin`). The unified component will use HTMX's "click to edit" row pattern where clicking a display row fetches an edit-mode partial that replaces it, combined with Alpine.js for client-side state (lock toggle, tooltip positioning).

**Primary recommendation:** Build the unified env var component as a Django template include (`_env_var_row.html` for display mode, `_env_var_row_edit.html` for edit mode) driven by HTMX swaps, with a standalone `resolve_env_vars()` utility function in `core/utils.py` for cascade resolution.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Unified UI component -- Layout
- Stacked rows, not a full table. Each variable as a horizontal row with key=value inline, badges/actions on the right
- Inline editing (click to edit in place), not modal dialogs
- Add variable via "Add variable" button that reveals an empty inline editable row at the bottom
- Variables grouped by source level: upstream (read-only) vars shown first with visual separator, then current-level editable vars below

#### Unified UI component -- Lock icon
- Lock icon on the LEFT side of each row, with three visual states:
  - **Ghost/missing** (not locked) -- clickable, switches to locked on this level
  - **Calm red** (locked on this level) -- clickable, removes lock
  - **Grey** (locked on upstream level) -- not clickable, hover tooltip: "Locked on {source} level"

#### Unified UI component -- Description & Source
- Description shown as tooltip on hover over the key (not always visible)
- Source level (System, Project, Service, Environment) included in the tooltip alongside description: "From: {source}. {description}"
- Small info/pencil icon next to the key opens a popover for editing the description
- Keeps rows compact -- no separate columns for source or description

#### Unified UI component -- Empty values
- Empty values shown as muted italic "not set" text
- On the Service > Environment resolved view, empty values get an amber warning highlight (proactive signal before deployment)

#### Cascade & resolution
- Lock support at Project and Service levels only (Environment is terminal, no effect until deployment vars exist)
- System-injected PTF_* variables (PTF_PROJECT, PTF_SERVICE, PTF_ENVIRONMENT) computed at resolution time, never stored in JSONField
- Existing SERVICE_NAME variable replaced with PTF_SERVICE (no backwards compatibility needed)
- Both environment contexts show resolved views:
  - Project > Environment: resolved view without service-specific vars (System + Project + Environment)
  - Service > Environment: fully resolved cascade (System + Project + Service + Environment)

#### Variable shape
- Add `description` field to the variable shape: `{key, value, lock, description}`
- All CRUD operations updated to handle description
- Template manifests seed descriptions from `required_vars` into the description field
- Description inherited from upstream when downstream overrides value, unless downstream provides its own

#### Wizard integration
- Same unified component used in the service creation wizard (consistent UX everywhere)
- All PTF_* vars shown in wizard: PTF_PROJECT (from selected project), PTF_SERVICE (from entered name), note that PTF_ENVIRONMENT will be injected per-environment
- Template required_vars seeded as empty-value rows with descriptions from manifest, no special "template" badge
- Info note placement for empty values: Claude's discretion

#### Deployment gate
- Implement cascade resolution utility function and empty-value check in this phase
- Actual gate enforcement deferred to when deployments are implemented
- Gate error message should list each empty variable with direct links to the correct level's settings page where the value should be set

### Claude's Discretion
- Info note placement in wizard for empty values (banner vs per-row hint)
- Exact styling/spacing of stacked rows
- Resolution function implementation approach (model method vs standalone utility)
- Whether to build a full gate UI preview or just the resolution function

### Deferred Ideas (OUT OF SCOPE)
- Deployment-level variables (5th cascade level) -- future phase when deployments are implemented
- Env var encryption (values currently stored unencrypted in JSONField) -- separate security concern
- Automatic stale variable detection -- design doc explicitly says manual management by operator
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DPLY-01 | Contributor can deploy service to non-production environment | Cascade resolution function provides the merged env vars needed for deployment. Gate check (empty values) is prerequisite. Actual deploy trigger deferred. |
| DPLY-02 | Project owner can deploy service to production environment | Same as DPLY-01; RBAC already exists in models. Gate function checks readiness. |
| DPLY-03 | Deploy modal shows environment selector and build selector | Out of scope for Phase 7 per CONTEXT.md -- deployment UI deferred. Resolution function prepares the data the modal will consume. |
| DPLY-04 | Deploy modal shows merged environment variables | The cascade resolution function (`resolve_env_vars()`) directly enables this. Phase 7 builds the function; deploy modal consumes it later. |
| DPLY-05 | Deployment calls Docker plugin to run container | Out of scope for Phase 7. |
| DPLY-06 | Deployment tracks status (pending, running, success, failed) | Out of scope for Phase 7. |
| DPLY-07 | User can view deployment history per environment | Out of scope for Phase 7. |
| DPLY-08 | Deployment stores artifact ref snapshot | Out of scope for Phase 7. |

**Note:** Phase 7 as scoped in CONTEXT.md focuses on the env vars system that *enables* DPLY-01 through DPLY-04. The actual deployment execution (DPLY-05 through DPLY-08) is deferred to a future deployment phase. This phase delivers the prerequisite infrastructure: unified env var management, cascade resolution, and deployment gate logic.
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 6.x | Web framework, models, views, templates | Project stack (CLAUDE.md) |
| HTMX | (vendored) | Inline editing via partial swaps | Already used throughout the project for dynamic UI |
| Alpine.js CSP | (vendored) | Client-side interactivity (tooltips, popovers, lock toggle) | Already used for all interactive components |
| Tailwind CSS | (vendored) | Styling for stacked rows, badges, tooltips | Already used for all styling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Django JSONField | built-in | Storage for env_vars arrays | Already in use on Project, Service, Environment models |
| django-auditlog | (installed) | Audit trail for env var changes | Already registered on all relevant models |

### Alternatives Considered
None -- all decisions are locked and use the existing stack.

## Architecture Patterns

### Current Codebase State

**Models (from `core/models.py`):**
- `Project.env_vars` -- JSONField, `default=list`, stores `[{"key": "X", "value": "Y", "lock": false}]`
- `Service.env_vars` -- JSONField, `default=list`, same shape
- `Environment.env_vars` -- JSONField, `default=list`, same shape
- `Service.get_merged_env_vars()` -- existing method that merges project + service vars with lock checking

**Current env var shape:** `{key, value, lock}` -- missing `description` field

**Current UI patterns:**
- Project settings: table-based display with modal for add/edit (`core/templates/core/projects/_settings_env_vars.html`)
- Environment detail: table-based display with modal for add/edit, shows merged view with "Inherited" badges
- Service settings: stacked display (read-only) using `get_merged_env_vars()`
- Wizard step 4: vanilla JS-driven dynamic rows with key/value inputs, no lock toggle, no description

**Current views:**
- `ProjectEnvVarModalView`, `ProjectEnvVarSaveView`, `ProjectEnvVarDeleteView` -- HTMX modal-based CRUD
- `EnvVarModalView`, `EnvVarSaveView`, `EnvVarDeleteView` -- environment-level CRUD
- `ServiceWizardView` -- wizard step for configuration uses `env_vars_json` hidden field

### Recommended Project Structure

```
core/
  templates/
    core/
      env_vars/                     # NEW - Unified env var component templates
        _env_var_container.html     # Container with grouping (upstream/current)
        _env_var_row.html           # Display mode row
        _env_var_row_edit.html      # Edit mode row (inline)
        _env_var_add_row.html       # Empty editable row for adding new var
  views/
    env_vars.py                     # NEW - Unified env var HTMX endpoints
  utils.py                          # Existing - add resolve_env_vars() function
```

### Pattern 1: HTMX Click-to-Edit Row

**What:** Each env var row is a self-contained HTMX unit. Clicking a row (or its edit action) swaps the display row for an edit row. Saving swaps back.

**When to use:** All env var display/edit contexts except the wizard (which needs a different approach since it operates on unsaved state).

**Example flow:**
```
Display row:  [lock] KEY = value [badges] [edit] [delete]
                 |
                 | click edit
                 v
Edit row:     [lock] [key input] = [value input] [save] [cancel]
                 |
                 | POST save
                 v
Display row:  [lock] KEY = new_value [badges]
```

**HTMX attributes on display row:**
```html
<div hx-target="this" hx-swap="outerHTML">
  <!-- display content -->
  <button hx-get="/projects/{name}/env-vars/{key}/edit-row/">Edit</button>
</div>
```

**HTMX attributes on edit row:**
```html
<form hx-put="/projects/{name}/env-vars/{key}/" hx-target="this" hx-swap="outerHTML">
  <!-- input fields -->
  <button type="submit">Save</button>
  <button hx-get="/projects/{name}/env-vars/{key}/row/">Cancel</button>
</form>
```

### Pattern 2: Cascade Resolution Utility

**What:** A standalone function that computes the fully resolved env vars for any context.

**Implementation approach (recommended: standalone utility in `core/utils.py`):**

```python
def resolve_env_vars(project, service=None, environment=None):
    """
    Resolve the full env var cascade for a given context.

    Contexts:
    - Project only: System(PTF_PROJECT) + Project vars
    - Project + Environment: System(PTF_PROJECT, PTF_ENVIRONMENT) + Project + Environment
    - Service only: System(PTF_PROJECT, PTF_SERVICE) + Project + Service
    - Full cascade: System(all PTF_*) + Project + Service + Environment

    Returns: list of {key, value, lock, description, source, locked_by}
    """
```

**Why standalone over model method:** The resolution crosses multiple models (Project, Service, Environment) and injects synthetic system vars. A standalone function keeps models focused on their own data while the resolution logic is centralized and testable.

### Pattern 3: Wizard Client-Side Env Vars

**What:** The wizard operates on unsaved state in the session. Env vars in the wizard use Alpine.js for client-side management (add/remove/edit rows) serialized to a hidden JSON field.

**Current implementation:** Vanilla JS with `renderEnvVars()` function that rebuilds the DOM. Needs to be rewritten to match the unified component's visual design while remaining client-side-driven.

**Approach:** Register an `Alpine.data('envVarWizard', ...)` component that manages the array of vars, renders rows matching the unified component design, and serializes to the hidden `env_vars_json` field on form submit. The wizard context gets PTF_* vars injected as read-only rows at the top.

### Pattern 4: Tooltip via Alpine.js

**What:** Description and source shown as tooltip on hover. Uses Alpine.js for positioning.

**CSP-compatible approach:**
```html
<span x-data="{ show: false }"
      @mouseenter="show = true"
      @mouseleave="show = false">
  <code>{{ var.key }}</code>
  <div x-show="show" x-cloak class="absolute ...">
    From: {{ var.source }}. {{ var.description }}
  </div>
</span>
```

Note: Each Alpine directive must be a single expression (CSP build constraint). `show = true` and `show = false` are valid single expressions.

### Anti-Patterns to Avoid
- **Don't use modals for add/edit:** Decision locked to inline editing. Replace the current `env_var_modal.html` pattern.
- **Don't store PTF_* variables in the database:** They are computed at resolution time only.
- **Don't use `x-init` with function bodies in templates:** CSP build only supports single expressions. Multi-step logic goes in `Alpine.data()` registered components.
- **Don't use arrow functions in Alpine.data():** CSP build requires `function()` syntax.
- **Don't create separate JS files for the env var component:** Per CLAUDE.md, page-specific components go in `{% block extra_head %}`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tooltip positioning | Custom positioning logic | CSS-only tooltips or simple Alpine `x-show` with absolute positioning | The tooltips are simple hover-reveal; no complex positioning needed |
| Inline editing | Custom contentEditable handlers | HTMX partial swap pattern (click-to-edit row) | Battle-tested pattern, server-driven, works with CSRF |
| JSON validation | Manual JSON parsing in views | Django form clean methods + Python list/dict operations | Already the pattern used in the codebase |

**Key insight:** The env var UI is a CRUD interface with a twist (cascade resolution). All the building blocks (HTMX swaps, Alpine tooltips, JSONField storage) already exist in the codebase. The main engineering challenge is the unified component design that works across all four contexts with different permission models and data sources.

## Common Pitfalls

### Pitfall 1: HTMX Partial Swap ID Conflicts
**What goes wrong:** When multiple env var rows are on the same page, `hx-target="this"` and unique IDs become critical. Duplicate IDs cause HTMX to swap the wrong element.
**Why it happens:** Template includes render multiple rows; if IDs are not parameterized with the variable key, they collide.
**How to avoid:** Use `id="env-var-row-{{ var.key }}"` on each row div. Use `hx-target="this"` (targeting the triggering element's parent) rather than ID-based targeting.
**Warning signs:** Wrong row updates when editing, or edits appearing in the wrong location.

### Pitfall 2: JSONField Race Conditions
**What goes wrong:** Two concurrent edits to the same JSONField can overwrite each other because Django's JSONField doesn't support atomic sub-key updates.
**Why it happens:** User A loads the page, user B saves a change, user A saves -- user B's change is lost.
**How to avoid:** Use `update_fields=["env_vars", "updated_at"]` on save (already done). For this project's scale (small team, single instance), this is acceptable. Note it in the code as a known limitation.
**Warning signs:** Variables disappearing after saves.

### Pitfall 3: Lock Enforcement on Downstream CRUD
**What goes wrong:** A user at the environment level tries to add/edit a variable with a key that is locked at the project level. The save succeeds but the value is ignored during resolution.
**Why it happens:** CRUD operations don't check upstream locks.
**How to avoid:** The CRUD save endpoint must check if the key is locked upstream. If locked, reject the save with an error message. The UI should also prevent this by showing locked upstream vars as non-editable.
**Warning signs:** Users add overrides that have no effect.

### Pitfall 4: Description Inheritance Complexity
**What goes wrong:** When resolving the cascade, description inheritance logic gets tangled -- especially when a downstream level overrides the value but not the description.
**Why it happens:** The spec says "description inherited from upstream when downstream overrides value, unless downstream provides its own." This requires tracking the upstream description separately.
**How to avoid:** In the resolution function, carry the description from each upstream level. When merging a downstream var, only replace the description if the downstream var has a non-empty description.
**Warning signs:** Empty descriptions on overridden variables, or wrong descriptions showing.

### Pitfall 5: Alpine.js CSP Build and Wizard Complexity
**What goes wrong:** The wizard env var component needs client-side add/remove/edit without server round-trips. Complex logic in Alpine directives fails because CSP build only supports single expressions.
**Why it happens:** The env var array management requires multi-step logic (push to array, serialize to JSON, re-render).
**How to avoid:** Register an `Alpine.data('envVarWizard', function() { ... })` component in the wizard template's `{% block extra_head %}` script block with `alpine:init`. Keep template directives to single expressions like `@click="addVar()"`.
**Warning signs:** Alpine console errors about expression parsing, or `[CSP]` errors in the browser console.

### Pitfall 6: Wizard Session State vs Unified Component
**What goes wrong:** The unified component uses HTMX for server-side CRUD, but the wizard needs client-side-only management since the service doesn't exist yet.
**Why it happens:** Two different interaction models (server-driven vs client-driven) sharing the same visual design.
**How to avoid:** Build the visual template (`_env_var_row.html`) to be reusable, but accept that the wizard will use Alpine.js to render rows client-side while settings pages use HTMX. The visual design is unified; the interaction model differs.
**Warning signs:** Trying to force HTMX into the wizard flow, or the wizard looking different from settings pages.

## Code Examples

### Example 1: Resolve Env Vars Function

```python
# core/utils.py

def resolve_env_vars(project, service=None, environment=None):
    """
    Resolve the full env var cascade for a given context.

    Returns list of dicts with keys:
    {key, value, lock, description, source, locked_by}
    - source: 'system' | 'project' | 'service' | 'environment'
    - locked_by: None or source level name where the lock was set
    """
    merged = {}

    # 1. System-injected PTF_* variables (always locked)
    system_vars = [
        {"key": "PTF_PROJECT", "value": project.name, "lock": True, "description": "Project name (system-injected)"},
    ]
    if service:
        system_vars.append(
            {"key": "PTF_SERVICE", "value": service.name, "lock": True, "description": "Service name (system-injected)"}
        )
    if environment:
        system_vars.append(
            {"key": "PTF_ENVIRONMENT", "value": environment.name, "lock": True, "description": "Environment name (system-injected)"}
        )

    for var in system_vars:
        merged[var["key"]] = {
            "key": var["key"],
            "value": var["value"],
            "lock": True,
            "description": var["description"],
            "source": "system",
            "locked_by": "system",
        }

    # 2. Project variables
    for var in project.env_vars or []:
        key = var["key"]
        merged[key] = {
            "key": key,
            "value": var.get("value", ""),
            "lock": var.get("lock", False),
            "description": var.get("description", ""),
            "source": "project",
            "locked_by": "project" if var.get("lock", False) else None,
        }

    # 3. Service variables (if provided)
    if service:
        for var in service.env_vars or []:
            key = var["key"]
            if key in merged and merged[key]["locked_by"]:
                continue  # Skip locked upstream vars
            desc = var.get("description", "") or merged.get(key, {}).get("description", "")
            merged[key] = {
                "key": key,
                "value": var.get("value", ""),
                "lock": var.get("lock", False),
                "description": desc,
                "source": "service",
                "locked_by": "service" if var.get("lock", False) else merged.get(key, {}).get("locked_by"),
            }

    # 4. Environment variables (if provided)
    if environment:
        for var in environment.env_vars or []:
            key = var["key"]
            if key in merged and merged[key]["locked_by"]:
                continue  # Skip locked upstream vars
            desc = var.get("description", "") or merged.get(key, {}).get("description", "")
            merged[key] = {
                "key": key,
                "value": var.get("value", ""),
                "lock": var.get("lock", False),
                "description": desc,
                "source": "environment",
                "locked_by": None,  # Environment is terminal, lock has no downstream effect
            }

    return sorted(merged.values(), key=lambda v: v["key"])


def check_deployment_gate(resolved_vars):
    """
    Check if all variables have values (deployment readiness).

    Returns:
    - (True, []) if all vars have values
    - (False, [list of empty vars with context]) if any are empty
    """
    empty_vars = [
        v for v in resolved_vars
        if v["value"] == "" and v["source"] != "system"
    ]
    return (len(empty_vars) == 0, empty_vars)
```

### Example 2: HTMX Inline Edit Row (Display Mode)

```html
<!-- _env_var_row.html -->
<div id="env-var-row-{{ var.key }}"
     class="flex items-center gap-3 px-4 py-3 rounded-lg {% if var.value == '' and show_empty_warning %}bg-amber-900/10 border border-amber-500/30{% else %}bg-dark-bg{% endif %}"
     hx-target="this" hx-swap="outerHTML">

    <!-- Lock icon (left side) -->
    {% if var.locked_by == var.source %}
    <!-- Locked on THIS level - calm red, clickable to unlock -->
    <button hx-post="{% url 'env_vars:toggle_lock' %}"
            hx-vals='{"key": "{{ var.key }}", "target": "{{ target }}", "target_id": "{{ target_id }}"}'
            class="text-red-400 hover:text-red-300" title="Locked on this level. Click to unlock.">
        <!-- lock SVG -->
    </button>
    {% elif var.locked_by %}
    <!-- Locked on UPSTREAM level - grey, not clickable -->
    <span class="text-gray-500 cursor-default" title="Locked on {{ var.locked_by }} level">
        <!-- lock SVG -->
    </span>
    {% else %}
    <!-- Not locked - ghost, clickable to lock -->
    <button hx-post="{% url 'env_vars:toggle_lock' %}"
            hx-vals='{"key": "{{ var.key }}", "target": "{{ target }}", "target_id": "{{ target_id }}"}'
            class="text-gray-700 hover:text-gray-500" title="Click to lock">
        <!-- unlock SVG -->
    </button>
    {% endif %}

    <!-- Key with tooltip -->
    <span x-data="{ tip: false }" @mouseenter="tip = true" @mouseleave="tip = false" class="relative">
        <code class="font-mono text-dark-text">{{ var.key }}</code>
        <div x-show="tip" x-cloak class="absolute left-0 bottom-full mb-1 ...">
            From: {{ var.source }}{% if var.description %}. {{ var.description }}{% endif %}
        </div>
    </span>

    <span class="text-dark-muted">=</span>

    <!-- Value -->
    {% if var.value %}
    <span class="text-dark-muted font-mono text-sm truncate">{{ var.value|truncatechars:50 }}</span>
    {% else %}
    <span class="text-dark-muted italic text-sm">not set</span>
    {% endif %}

    <!-- Actions (right side) -->
    <div class="ml-auto flex items-center gap-2">
        {% if is_editable %}
        <button hx-get="{% url 'env_vars:edit_row' %}?key={{ var.key }}&target={{ target }}&target_id={{ target_id }}"
                class="text-dark-muted hover:text-dark-accent">
            <!-- edit SVG -->
        </button>
        <button hx-delete="{% url 'env_vars:delete' %}?key={{ var.key }}&target={{ target }}&target_id={{ target_id }}"
                hx-confirm="Delete variable {{ var.key }}?"
                class="text-dark-muted hover:text-red-400">
            <!-- delete SVG -->
        </button>
        {% endif %}
    </div>
</div>
```

### Example 3: Alpine.js Wizard Env Var Component

```javascript
// In wizard template {% block extra_head %} or {% block scripts %}
document.addEventListener('alpine:init', function() {
    Alpine.data('envVarWizard', function() {
        return {
            vars: [],
            ptfVars: [],
            hiddenFieldId: '',

            init: function() {
                // Parse initial data from hidden field
                var el = document.getElementById(this.hiddenFieldId);
                if (el && el.value) {
                    try { this.vars = JSON.parse(el.value); } catch(e) {}
                }
            },

            addVar: function() {
                this.vars.push({ key: '', value: '', lock: false, description: '' });
                this.serialize();
            },

            removeVar: function(index) {
                this.vars.splice(index, 1);
                this.serialize();
            },

            updateKey: function(index, val) {
                this.vars[index].key = val.toUpperCase().replace(/[^A-Z0-9_]/g, '_');
                this.serialize();
            },

            updateValue: function(index, val) {
                this.vars[index].value = val;
                this.serialize();
            },

            toggleLock: function(index) {
                this.vars[index].lock = !this.vars[index].lock;
                this.serialize();
            },

            serialize: function() {
                var el = document.getElementById(this.hiddenFieldId);
                if (el) { el.value = JSON.stringify(this.vars); }
            }
        };
    });
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `SERVICE_NAME` system var | `PTF_SERVICE` | Phase 7 | Rename throughout codebase; no backwards compat needed |
| `{key, value, lock}` shape | `{key, value, lock, description}` | Phase 7 | Add description field; existing data gets empty descriptions |
| Modal-based env var editing | Inline editing with HTMX row swaps | Phase 7 | Replace `env_var_modal.html` pattern |
| Separate UI per context | Unified component across all contexts | Phase 7 | Single template include, parameterized by context |

**Deprecated/outdated:**
- `core/templates/core/projects/env_var_modal.html`: Will be replaced by inline editing rows
- `Service.get_merged_env_vars()`: Will be replaced by standalone `resolve_env_vars()` utility
- `SERVICE_NAME` system variable: Replaced by `PTF_SERVICE`

## Open Questions

1. **Lock toggle on empty values**
   - What we know: Spec says "A variable with an empty value cannot be locked." The lock ghost icon should still appear but clicking it when value is empty should show validation error.
   - What's unclear: Should the ghost icon be hidden entirely for empty-value rows, or shown but disabled?
   - Recommendation: Show ghost icon but disable click with tooltip "Set a value before locking." Keeps the layout consistent.

2. **Wizard component reuse vs duplication**
   - What we know: The wizard needs client-side management (Alpine.js) while settings pages use server-side HTMX. Both should look identical.
   - What's unclear: How much template HTML can be shared between the HTMX row partial and the Alpine-rendered row?
   - Recommendation: Accept some HTML duplication. The wizard Alpine template will mirror the HTMX row template's classes and structure, but the interaction model is fundamentally different. Trying to share templates across HTMX and Alpine patterns adds complexity without proportional benefit.

3. **Environment-level env vars in Service context**
   - What we know: CONTEXT.md says "Service > Environment: fully resolved cascade (System + Project + Service + Environment)." The current Service detail has an "Environments" tab.
   - What's unclear: Does the Service > Environments tab show per-environment resolved views, or just environment links?
   - Recommendation: The Service Environments tab should show links to each environment. Each environment detail page already shows the resolved view. The Service Settings tab shows Service-level vars (Project + Service cascade). No need to embed full per-environment resolution in the Service detail.

4. **URL routing for unified env var endpoints**
   - What we know: Current URLs are split across project-level and environment-level patterns. The unified component needs endpoints that work for any target (project, service, environment).
   - What's unclear: Should there be a single set of URLs with target/id parameters, or separate URL patterns per entity type?
   - Recommendation: Keep entity-specific URL patterns (project, service, environment) for clarity and permission checking, but have all of them render the same template partials. The URLs encode the permission context; the templates are shared.

## Sources

### Primary (HIGH confidence)
- `/Users/fandruhin/work/yourdevops/pathfinder/docs/env-vars.md` -- Authoritative spec for variable shape, cascade, deployment gate
- `/Users/fandruhin/work/yourdevops/pathfinder/core/models.py` -- Current model definitions for Project, Service, Environment, Build
- `/Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/projects/_settings_env_vars.html` -- Current project env vars UI
- `/Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/projects/env_var_modal.html` -- Current modal-based editing pattern
- `/Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/services/wizard/step_configuration.html` -- Current wizard env vars step
- `/Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/projects/environment_detail.html` -- Current environment detail with merged vars
- `/Users/fandruhin/work/yourdevops/pathfinder/core/views/projects.py` -- Current env var CRUD views
- Context7 `/bigskysoftware/htmx` -- HTMX click-to-edit and edit-row patterns
- Context7 `/spookylukey/django-htmx-patterns` -- Django HTMX inline partial patterns

### Secondary (MEDIUM confidence)
- `/Users/fandruhin/work/yourdevops/pathfinder/docs/wizard.md` -- Wizard step 4 specification
- `/Users/fandruhin/work/yourdevops/pathfinder/docs/services.md` -- Service model and deploy modal wireframe
- `/Users/fandruhin/work/yourdevops/pathfinder/docs/templates/design.md` -- Template manifest `required_vars` format

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- uses existing project stack, no new dependencies
- Architecture: HIGH -- patterns verified against existing codebase, HTMX inline editing documented in official sources
- Pitfalls: HIGH -- derived from direct codebase analysis and known JSONField/HTMX patterns
- Resolution logic: HIGH -- spec is detailed and unambiguous in `docs/env-vars.md`

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable -- internal project with locked decisions)
