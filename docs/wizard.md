# Intake Flow (Service Onboarding "Wizard")

A 4-page wizard for creating new Services. The wizard is **template-driven**: selecting a template determines what options appear throughout the flow.

## Design Principle: Template-First

The Service Template is the "golden path" that defines:
- What type of service this is (container, serverless, static)
- How it's built (CI system, build steps)
- How it's deployed (direct, GitOps, pipeline)
- What configuration options are relevant

By selecting a template early, the wizard can:
1. Show only relevant configuration options
2. Pre-fill sensible defaults for that service type
3. Guide developers without overwhelming them

---

Every page should have a "Back" and "Next" button to go to the previous and next page without losing the wizard data.

### Page 1 - Choose Your Path

**Project Selector** (required)
- Show only projects the user has access to
- Display format: `{name}` with `description` as subtitle
- Spoiler: "Project missing on the list?" → link to request form
- **Selecting a project determines which blueprints are available** (based on Environment connections)

**Service Template Selector** (required)
- Shows blueprints available for the selected project
- Blueprints are available when at least one Environment has a Connection matching `deploy.required_plugins` from the template manifest
- Display format: Card with icon, name, description, tags
- Tags indicate: language, deploy type, cloud provider

**Template Card Example:**
```
┌─────────────────────────────────────────┐
│ 🐍 python-k8s-service                   │
│ Python service deployed to Kubernetes   │
│ [python] [container] [k8s]              │
└─────────────────────────────────────────┘
```

**Service Name** (required)
- Text input with real-time validation
- Rules: lowercase, hyphens only, 1-40 chars
- Show service_handler preview: `{project-name}-{app-name}`
- Show remaining character count
- Validate uniqueness within project on blur

---

### Page 2 - Source Code

**Source Code Provider** (required)
- Dropdown showing healthy SCM connections only
- If template specifies `ci_connection`, pre-select compatible SCM
- Format: `{connection-name} ({plugin})` e.g., "yourdevops (GitHub)"
- Spoiler: "Not seeing your workspace?" → link to request form

**Repository Configuration:**

Checkbox: `[ ] Initialize new repository` (default: false)
- If checked: Creates new repo in selected workspace
  - GitHub: repo name = service_handler
  - BitBucket: project = project-name, repo = app-name
  - Validate repo doesn't exist; block if it does with error message

- If unchecked: Show existing repository selector
  - Dropdown of repos from the selected SCM connection
  - Search/filter capability for large repo lists

**Branch configuration** (only if existing repo was selected):
- Branch name: `{prefix}/` + text input
- Branch prefix: configured in Global Settings (e.g., `ssp`, `feature`)
- Base branch selector: list branches from repo, default to `main`
- Validate branch doesn't already exist; show error: "Branch '{name}' already exists. Choose a different name."
- Help text: "SSP will create this branch, commit template contents and open a pull request to the base branch."

**File Handling for Existing Repos:**
When applying template to an existing repository, file handling follows the template's `source.on_copy` configuration. If not specified, all template files overwrite existing files. See [blueprints.md](blueprints.md) for details.

---

### Page 3 - Configuration

Header: "You can skip this step and configure these settings later."

**This page is dynamic based on template.deploy_type:**

#### For `container` deploy type:

**Port Mappings**
- Container port (default from template if specified)
- Protocol selector (TCP/UDP)

**Resource Limits** (all optional)
- CPU request / limit: default from template or 0.5 cores
- Memory request / limit: default from template or 512M

**Health Check** (optional)
- Endpoint: e.g., `/health`
- Interval, timeout, retries

**Volume Mounts**
- Placeholder for future implementation

#### For `serverless` deploy type:

**Function Configuration**
- Handler: e.g., `handler.main` (pre-filled from template)
- Runtime: e.g., `python3.13` (pre-filled from template)
- Timeout: default 30s
- Memory: default 256MB

#### For `static` deploy type:

**Build Output**
- Build directory: e.g., `dist/`, `build/`, `public/`
- Index document: default `index.html`
- Error document: default `404.html`

**CDN Configuration** (optional)
- Enable WAF protection: default false
- Cache TTL: default 1 hour

#### Common to all types:

**Environment Variables** (app-level)
- Table editor with Key | Value | Lock | [X] columns
- These are app-level defaults in the cascade: Project → Environment → **Service** → Deployment
- Locked vars cannot be overridden at deployment time
- Deployment-specific overrides are configured in the Deploy modal (see [services.md](services.md))

---

### Page 4 - Review and Deploy

**Configuration Summary**
- Template selected and its properties
- All selections from previous pages
- Warnings for any issues detected

**Deploy Now** (only shown if "Initialize new repository" is checked)
- Checkbox: `[ ] Deploy to <default environment name> after first successful build`
- Note: "Deployment will be queued and executed automatically once CI completes the first build."
- If checked:
  - Expand deployment-level environment variables section (see [services.md](services.md#environment-variables-in-deploy-modal))
  - Create button: "Create Service" changes to "Create & Deploy Service"

**For existing repositories:**
- "Deploy Now" checkbox is hidden
- Show info: "Deployment will be available after the PR is merged and first build completes."
- This enforces proper PR review workflow before any deployment

**Creation Workflow:**

1. If "Initialize repository" was selected:
   - Create repo via SCM connection API
   - Clone template
   - Commit to `main` branch in a single commit and push
   - If BitBucket: create project if needed

2. If existing repo was selected:
   - Clone repo
   - Create configured branch from base
   - Apply template contents per `on_copy` rules
   - Commit and push
   - Create pull request to base branch

3. Create Service record in Pathfinder database with:
   - Reference to selected template
   - deploy_type from template (for deployment routing)

4. If new repository was created:
   - Register webhook (if supported)
   - Trigger initial build (optional)

5. If "Deploy Now" was selected (new repos only):
   - Queue deployment to run after first successful build
   - Route to matching connection in target environment
   - Execute via connection's mechanism (direct/gitops/pipeline)

**Error Handling:**
- On fails: show error, do not create the service yet, allow retry or cancel
- If PR creation fails: create service anyway, show warning with manual PR link

**Post-Creation:**
- Redirect to service detail page
- For new repos with "Deploy Now": deployment queued as background job
- Track build status, get artifact from CI, then deploy to target Environment
