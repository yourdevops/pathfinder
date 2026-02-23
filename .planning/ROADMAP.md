# Roadmap: Pathfinder

## Overview

Pathfinder delivers an internal developer platform control plane in 7 phases. Phase 1 establishes secure user management with RBAC and audit logging. Phases 2-3 build the organizational structure (Projects, Environments) and integration infrastructure (GitHub, Docker plugins). Phases 4-5 enable the golden path: Blueprints for templates, Services with wizard-based creation. Phases 6-7 complete the CI/CD loop: Builds from GitHub Actions webhooks, Deployments to Docker containers. The end-to-end flow enables developers to go from "I need a new service" to "it's running" without tickets.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Security** - User authentication, RBAC, groups, audit logging, base UI
- [x] **Phase 2: Core Domain** - Projects with membership, Environments with deploy targets
- [x] **Phase 3: Integrations** - Plugin framework, GitHub and Docker connections
- [x] **Phase 3.1: Unified Sidebar Navigation** (INSERTED) - Expandable sidebar with Home, Service Catalog, Blueprints, Integrations, Settings
- [x] **Phase 4: Blueprints** - Template registration, versioning, availability filtering
- [x] **Phase 4.1: Replace UUID URLs with Slugs** (INSERTED) - Use name-based slugs in URLs instead of UUIDs
- [x] **Phase 5: Services** - Creation wizard, repository scaffolding, service management
- [x] **Phase 5.1: CI Workflows Builder** (INSERTED) - Steps catalog, workflow composer, GitHub Actions manifest preview
- [x] **Phase 5.2: CI Workflows — Project & Service Pairing** (INSERTED) - Assign workflows to services, push manifests to repos
- [x] **Phase 5.3: CI Steps Redesign** (INSERTED) - Plugin-based CI capabilities, engine-agnostic step discovery, clean core/git_utils.py
- [x] **Phase 6: Builds** - Webhook ingestion, build tracking, service activation
- [x] **Phase 6.1: Fix CI Workflows Design-Implementation Gap** (INSERTED) - Workflow versioning, build verification, manifest management
- [x] **Phase 6.2: Deployment Design Documentation** (INSERTED) - RFC-style design docs for Deployments
- [x] **Phase 6.3: Security & Compliance Design — Secrets, SLSA L3, SOX RBAC** (INSERTED) - Secrets management, artifact provenance signing, SLSA Level 3, SOX-compliant RBAC
- [x] **Phase 6.4: CI Step Identity and Change Tracking** (INSERTED) - Step slugs, per-file SHA versioning, change detection, archival
- [x] **Phase 6.5: Workflow and Build Model Hardening** (INSERTED) - CIWorkflow engine field, step ordering validation, archived status, engine-agnostic Build model, revoked verification status
- [x] **Phase 6.6: Sync Operations and Logging** (INSERTED) - Webhook and scheduled sync triggers, sync operation logging, branch protection validation
- [x] **Phase 6.7: Version Lifecycle Automation** (INSERTED) - Auto-update manifests on patch publish, retention cleanup for old versions
- [ ] **Phase 6.8: Manifest and Plugin Interface** (INSERTED) - Artifact discovery via CI plugin, CI variables, step validation API, runtime derivation from steps
- [ ] **Phase 6.9: Step Output Wiring** (INSERTED) - Steps declare outputs, composer wires outputs to inputs, engine-native references
- [ ] **Phase 6.10: Pluggable Webhook Routing Framework** (INSERTED) - Core webhook dispatcher with plugin-supplied route registration
- [ ] **Phase 6.11: Templates Documentation Folder** (INSERTED) - Design docs for the unified pathfinder.yaml Templates system end-to-end

## Phase Details

### Phase 1: Foundation & Security
**Goal**: Platform engineers can securely administer users and groups; all authenticated users have baseline platform access
**Depends on**: Nothing (first phase)
**Requirements**: FNDN-01, FNDN-02, FNDN-03, FNDN-04, FNDN-05, FNDN-06, FNDN-07, FNDN-08, FNDN-09, FNDN-10, FNDN-11, FNDN-12, FNDN-13, FNDN-14, UIUX-01, UIUX-05
**Success Criteria** (what must be TRUE):
  1. Fresh install shows unlock page; entering correct token allows admin account creation
  2. Admin can create users, create groups, assign users to groups, and assign SystemRoles to groups
  3. User can log in, session persists across browser refresh, user can log out from any page
  4. Authenticated user sees navigation with Blueprints and Connections (even if empty lists)
  5. All entity changes (user, group, role assignment) appear in audit log with actor and timestamp
**Plans**: 6 plans

Plans:
- [x] 01-01-PLAN.md - Core models, dependencies, and settings configuration
- [x] 01-02-PLAN.md - Tailwind theme with dark mode and navigation component
- [x] 01-03-PLAN.md - Unlock flow, setup middleware, login/logout authentication
- [x] 01-04-PLAN.md - User management UI (list, create modal, edit)
- [x] 01-05-PLAN.md - Group management and audit log viewer
- [x] 01-06-PLAN.md - Placeholder pages for Blueprints and Connections

### Phase 2: Core Domain
**Goal**: Platform engineers can organize work into Projects; developers have scoped access via group membership
**Depends on**: Phase 1
**Requirements**: PROJ-01, PROJ-02, PROJ-03, PROJ-04, PROJ-06, PROJ-07, ENV-01, ENV-03, ENV-04, ENV-05, ENV-06, UIUX-02
**Deferred to Phase 3**: PROJ-05 (Attach SCM connections to project), ENV-02 (Attach deploy connections to environments) - these require the integration framework from Phase 3
**Success Criteria** (what must be TRUE):
  1. Admin can create a Project and assign groups with owner/contributor/viewer roles
  2. Project owner can edit settings and manage environment variables
  3. Admin can create Environments within a Project; first environment becomes default
  4. Environment settings include is_production flag and env_vars that inherit from Project
  5. Project detail page shows tabs: Services, Environments, Members, Settings
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md - Project, Environment, ProjectMembership models with HTMX setup
- [x] 02-02-PLAN.md - Sidebar restructure and project list with create modal
- [x] 02-03-PLAN.md - Project detail with HTMX tabs and context-replacing sidebar
- [x] 02-04-PLAN.md - Membership management, environment CRUD, and environment variables

### Phase 3: Integrations
**Goal**: Platform engineers can register and health-check GitHub and Docker connections
**Depends on**: Phase 2
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04, INTG-05, INTG-06, INTG-07, INTG-08, INTG-09, PROJ-05, ENV-02
**Success Criteria** (what must be TRUE):
  1. Operator can register a GitHub connection with App credentials; sensitive fields are encrypted
  2. Operator can register a Docker connection with socket path; health check shows container daemon status
  3. GitHub connection can create repositories, create branches/commits, and configure webhook secrets
  4. Docker connection can deploy a container and check its running status
  5. Connection list shows health status (healthy/unhealthy/unknown) for each connection
  6. Projects can have SCM connections attached (PROJ-05)
  7. Environments can have deploy connections attached (ENV-02)
**Plans**: 6 plans

Plans:
- [x] 03-01-PLAN.md - Plugin foundation, encryption utilities, IntegrationConnection model
- [x] 03-02-PLAN.md - GitHub plugin with multi-step wizard and API operations
- [x] 03-03-PLAN.md - Docker plugin with single-page form and container operations
- [x] 03-04-PLAN.md - Connections management UI (list, detail, health status)
- [x] 03-05-PLAN.md - Background health checks with django-tasks
- [x] 03-06-PLAN.md - Connection attachments to projects and environments

### Phase 3.1: Unified Sidebar Navigation (INSERTED)
**Goal**: Developers see a consistent, expandable sidebar with all platform sections; context-switching maintains navigation state
**Depends on**: Phase 3
**Requirements**: UIUX-01, UIUX-02 (navigation restructure)
**Success Criteria** (what must be TRUE):
  1. Home page shows dashboard with welcome message, "+ Create Service" button, and recent activity feed
  2. Service Catalog section expands to show Services and Projects links
  3. Blueprints section expands to show Services (Phase 4 placeholder) and Resources (placeholder)
  4. Integrations section shows Connections and Plugins (existing functionality)
  5. Settings section expands to show General (placeholder), Users & Groups, Audit Log, Notifications (placeholder)
  6. All top-level sections use consistent expandable pattern with remembered state
  7. Project/Service context-switching replaces sidebar with context-specific navigation
  8. No breadcrumbs in the application - sidebar is source of truth for location (per CONTEXT.md)
**Plans**: 3 plans

Plans:
- [x] 03.1-01-PLAN.md — Expandable sidebar sections with Alpine.js Persist
- [x] 03.1-02-PLAN.md — Home dashboard with stats and activity feed
- [x] 03.1-03-PLAN.md — Project sidebar refinements (Details first, back button)

### Phase 4: Blueprints
**Goal**: Platform engineers can publish service templates; developers can browse available blueprints
**Depends on**: Phase 3
**Requirements**: BPRT-01, BPRT-02, BPRT-03, BPRT-04, BPRT-05, BPRT-06
**Success Criteria** (what must be TRUE):
  1. Operator can register a Blueprint from a git URL; system syncs metadata from ssp-template.yaml
  2. Blueprint displays name, description, tags, ci.plugin, deploy.plugin from manifest
  3. Blueprint shows available git tags as selectable versions
  4. Operator can manually trigger sync to refresh versions
  5. Blueprint availability is filtered based on project environment connections (matching deploy.plugin)
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Blueprint and BlueprintVersion models with sync task
- [x] 04-02-PLAN.md — Blueprint views, URLs, and templates (list, register, detail)
- [x] 04-03-PLAN.md — Availability filtering and HTMX sync updates

### Phase 4.1: Replace UUID URLs with Slugs (INSERTED)
**Goal**: All URLs use human-readable name-based slugs instead of UUIDs; naming uniqueness enforced at model level
**Depends on**: Phase 4
**Requirements**: None (architectural refactoring)
**Success Criteria** (what must be TRUE):
  1. Project URLs use slug: `/projects/my-project/` instead of `/projects/<uuid>/`
  2. Environment URLs use nested slugs: `/projects/my-project/environments/production/`
  3. Blueprint URLs use slug: `/blueprints/python-fastapi/`
  4. Group URLs use slug: `/groups/platform-team/`
  5. Connection URLs use slug: `/connections/github-main/`
  6. User URLs keep UUID (privacy): `/users/<uuid>/edit/`
  7. All name fields have proper slug generation and uniqueness constraints
  8. Existing data migrated to have valid slugs
**Plans**: 4 plans

Plans:
- [x] 04.1-01-PLAN.md — DNS label validator, URL path converter, model validators
- [x] 04.1-02-PLAN.md — Project and Environment URL refactoring
- [x] 04.1-03-PLAN.md — Group and Blueprint URL refactoring
- [x] 04.1-04-PLAN.md — Connection URL refactoring and plugin redirects

### Phase 5: Services
**Goal**: Developers can create services via wizard and see repositories scaffolded from blueprints
**Depends on**: Phase 4
**Requirements**: SRVC-01, SRVC-02, SRVC-03, SRVC-04, SRVC-05, SRVC-06, SRVC-07, SRVC-08, SRVC-09, SRVC-10, UIUX-03, UIUX-04, UIUX-06
**Success Criteria** (what must be TRUE):
  1. Contributor can start service creation wizard; Page 1 selects project, blueprint, and service name
  2. Wizard Page 2 configures SCM: select connection, choose new/existing repo, configure branch
  3. Wizard Page 3 configures service-level environment variables (port/resources deferred)
  4. Wizard Page 4 shows review summary; clicking Create scaffolds repository from blueprint
  5. Service detail page shows tabs: Details, Builds, Environments with HTMX dynamic updates
**Plans**: 4 plans

Plans:
- [x] 05-01-PLAN.md — Service model with handler property and migrations
- [x] 05-02-PLAN.md — Service creation wizard (SessionWizardView, 4 steps)
- [x] 05-03-PLAN.md — Repository scaffolding background task
- [x] 05-04-PLAN.md — Service list and detail pages with sidebar

### Phase 5.1: CI Workflows Builder (INSERTED)
**Goal**: Platform engineers can scan a CI steps repository, browse a steps catalog, compose CI Workflows from compatible steps, and preview the generated GitHub Actions manifest
**Depends on**: Phase 5
**Requirements**: None (replaces Blueprints concept with CI Workflows per docs/ci-workflows.md)
**Scope Notes**:
  - Replaces existing Blueprints functionality with CI Workflows
  - No deployment capabilities in this phase
  - No Service integration yet (next phase will connect Services to CI Workflows)
  - No versioning (save only, no semver lifecycle)
  - GitHub Actions manifest preview (read-only, no push to repo)
  - Recommendations for CI library repo structure at completion
**Success Criteria** (what must be TRUE):
  1. Operator can register a CI steps repository; Pathfinder scans it and imports step definitions from action.yml files with x-pathfinder metadata
  2. Operator can browse a Steps Catalog showing all imported steps organized by phase (setup, build, test, package) with runtime compatibility info
  3. Operator can view runtimes parsed from runtimes.yml in the steps repository
  4. User can click "+ Create CI Workflow" and select a runtime family/version
  5. Workflow composer shows only steps compatible with the selected runtime; incompatible steps are visually indicated
  6. User can add/reorder/remove steps to compose a workflow, configuring per-step inputs
  7. User can save the CI Workflow with a name and description
  8. User can view the generated GitHub Actions YAML manifest for the saved workflow
  9. Existing Blueprints models/views are removed or replaced
**Plans**: 4 plans

Plans:
- [x] 05.1-01-PLAN.md — Remove Blueprints, add CI Workflow models, update navigation
- [x] 05.1-02-PLAN.md — Repository scanning, steps catalog, and runtimes views
- [x] 05.1-03-PLAN.md — Workflow composer with runtime compatibility filtering
- [x] 05.1-04-PLAN.md — Manifest generation, workflow list and detail views

### Phase 5.2: CI Workflows — Project & Service Pairing (INSERTED)
**Goal**: Services can be paired with CI Workflows; projects gain CI configuration capabilities enabling the build pipeline connection in Phase 6
**Depends on**: Phase 5.1
**Requirements**: None (continuation of CI Workflows integration per docs/ci-workflows.md)
**Scope Notes**:
  - Connect CI Workflows to Services (assign workflow to service)
  - Project-level CI configuration (default workflow, CI settings)
  - Push generated GitHub Actions manifest to service repository
  - Service detail shows assigned CI Workflow with manifest preview
**Success Criteria** (what must be TRUE):
  1. User can assign a CI Workflow to a Service from the service detail page
  2. Assigned workflow's generated GitHub Actions manifest can be pushed to the service's repository
  3. Project settings include CI configuration section for default workflow preferences
  4. Service detail page shows CI Workflow tab with assigned workflow and manifest preview
  5. Changing a service's CI Workflow updates the repository's workflow file
**Plans**: 3 plans

Plans:
- [x] 05.2-01-PLAN.md — Models, migrations, and Project CI Configuration UI
- [x] 05.2-02-PLAN.md — Service CI tab, manifest push task, GitHubPlugin update
- [ ] 05.2-03-PLAN.md — Service creation wizard workflow step + verification (deferred)

### Phase 5.3: CI Steps Redesign (INSERTED)
**Goal**: CI capabilities are delivered through the plugin system; step discovery is engine-agnostic; core/git_utils.py contains only generic git operations; plugin-specific actions (manifest generation, step file parsing, manifest paths) live in plugin implementations
**Depends on**: Phase 5.2
**Requirements**: None (architectural redesign per docs/ci-steps-redesign.md)
**Scope Notes**:
  - One steps repository per CI engine with auto-discovery (no mandatory directory structure)
  - CI capability interface on BasePlugin: engine_file_name, parse_step_file, generate_manifest, manifest_path
  - Move manifest generation from core/ci_manifest.py into CI plugin implementations
  - Move step scanning from core/git_utils.py into core/ci_steps.py (engine-agnostic)
  - Refactor push_ci_manifest task to resolve SCM and CI capabilities separately
  - StepsRepository model gains engine field (not tied to plugin connection)
  - CIStep model gains engine and inputs_schema fields
  - Clean core/git_utils.py to carry only generic git actions
  - Remove top-level Runtimes nav; add filters by Engine, Runtime, Runtime Version on Steps page
  - Steps and Repositories pages use table layout instead of cards
**Success Criteria** (what must be TRUE):
  1. CI-capable plugins define engine_file_name, parse_step_file, generate_manifest, and manifest_path
  2. Step scanning walks repository for engine-native files using plugin-provided filename, not hardcoded patterns
  3. Manifest generation lives in plugin implementations, not in core
  4. core/git_utils.py contains only generic git operations (clone, checkout, commit, push); no CI-specific logic
  5. StepsRepository has an engine string field; scanning works without a CI plugin connection
  6. Steps catalog supports filtering by engine, runtime, and runtime version
  7. push_ci_manifest resolves CI capability (manifest generation) and SCM capability (file push) independently
  8. Steps and Repositories pages use table layout with engine column
**Plans**: 3 plans

Plans:
- [x] 05.3-01-PLAN.md — CICapableMixin, GitHubPlugin CI implementation, model migrations, core/ci_steps.py, clean git_utils.py
- [x] 05.3-02-PLAN.md — Refactor tasks, views, forms; remove RuntimesView and Runtimes nav
- [x] 05.3-03-PLAN.md — Table layouts for Steps and Repositories pages, HTMX filter dropdowns

### Phase 6: Builds
**Goal**: GitHub Actions can report build status; services transition from draft to active on first successful build
**Depends on**: Phase 5
**Requirements**: BILD-01, BILD-02, BILD-03, BILD-04, BILD-05, BILD-06
**Success Criteria** (what must be TRUE):
  1. GitHub Actions workflow can call build-started webhook with authenticated token
  2. GitHub Actions workflow can call build-complete webhook with artifact reference
  3. Build record shows commit SHA, status, artifact ref, and CI job URL
  4. Service status transitions from "draft" to "active" after first successful build
  5. User can view build history for a service showing all builds with statuses
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — Build model, webhook endpoint with HMAC auth, poll_build_details task, service activation
- [x] 06-02-PLAN.md — Build history UI with table layout, filtering, pagination, HTMX auto-refresh

### Phase 06.11: Templates documentation folder (INSERTED)

**Goal:** Create docs/templates/ documentation folder (structured like docs/ci-workflows/) that designs the Templates system end-to-end using a unified pathfinder.yaml manifest with kind: template and kind: service
**Depends on:** Phase 6
**Requirements:** BPRT-01, BPRT-02, BPRT-03, BPRT-04, BPRT-05, BPRT-06
**Plans:** 4/4 plans complete

Plans:
- [ ] 06.07-01-PLAN.md — manifest-schema.md: unified pathfinder.yaml field reference for templates and services
- [ ] 06.07-02-PLAN.md — variable-lifecycle.md and template-registration.md: build-time enforcement and operator registration flow
- [ ] 06.07-03-PLAN.md — scaffolding.md and examples.md: wizard redesign and copy-paste YAML samples
- [ ] 06.07-04-PLAN.md — README.md: entry point mirroring docs/ci-workflows/README.md structure

### Phase 06.10: Pluggable Webhook Routing Framework (INSERTED)

**Goal:** Refactor webhook handling from hardcoded core endpoints into a pluggable framework where plugins own their webhook handlers. Core provides routing infrastructure; current /webhooks/build/ and /webhooks/steps-repo/ are GitHub-specific and must move into the GitHub plugin.
**Depends on:** Phase 6
**Plans:** 2/2 plans complete

Plans:
- [ ] 06.07-01-PLAN.md -- Move webhook handlers to GitHub plugin, register /integrations/github/webhook/, add get_webhook_url() to plugin interface
- [ ] 06.07-02-PLAN.md -- Update all hardcoded webhook URL references to use plugin-aware resolution

### Phase 06.9: Step Output Wiring (INSERTED)

**Goal:** Steps declare outputs in the catalog (parsed during sync). The workflow composer lets users wire one step's output to another step's input via copy-paste of engine-native references. CI plugins translate these references to engine-native syntax during manifest generation.
**Depends on:** Phase 6
**Gaps Addressed**: GAP-21 from docs/ci-workflows/REMEDIATION.md
**Plans:** 2/2 plans complete

Plans:
- [ ] 06.9-01-PLAN.md -- Model, plugin interface, sync parsing, step detail outputs, manifest step IDs
- [ ] 06.9-02-PLAN.md -- Composer UX: Configure tabs, outputs display, copy buttons, real-time and server-side validation

### Phase 06.8: Manifest and Plugin Interface (INSERTED)

**Goal:** Artifact discovery uses CI plugin API (not webhook payloads), CI variables are injected into manifests, a step validation API exists, dead manifest_path code is removed, and workflow runtimes are derived from steps with version constraints at the workflow level and concrete versions at the service level.
**Depends on:** Phase 6
**Gaps Addressed**: GAP-13, GAP-17, GAP-18, GAP-19, GAP-20 from docs/ci-workflows/REMEDIATION.md
**Plans:** 4/4 plans complete

Plans:
- [ ] 06.8-01-PLAN.md — Remove manifest_path dead code, add resolve_artifact_ref to plugin interface (GAP-19, GAP-13)
- [ ] 06.8-02-PLAN.md — Step validation API endpoint with token authentication (GAP-18)
- [ ] 06.8-03-PLAN.md — CI variable provisioning via plugin interface (GAP-17)
- [ ] 06.8-04-PLAN.md — Workflow composer redesign with derived runtime constraints (GAP-20)

### Phase 06.7: Version Lifecycle Automation (INSERTED)

**Goal:** When a CI Workflow version is published, services using that workflow automatically receive updated manifests via PR (patch bumps only). Old versions are cleaned up per retention policy.
**Depends on:** Phase 6
**Gaps Addressed**: GAP-11, GAP-12 from docs/ci-workflows/REMEDIATION.md
**Success Criteria** (what must be TRUE):
  1. Publishing a patch version auto-updates eligible services via digest PR on `pathfinder/ci-manifest` branch
  2. Services have an auto-update toggle (default on) controlling whether patch updates are applied
  3. Old manifest content is cleared after retention period; hash retained for verification
  4. Unreferenced revoked versions are deleted after retention period
  5. CI Configuration settings page allows retention period configuration and manual cleanup
  6. Daily cleanup task runs at 03:00 UTC; management command available for CLI use
**Plans:** 4/4 plans complete

Plans:
- [ ] 06.7-01-PLAN.md -- Models, migration, and service auto-update toggle UI
- [ ] 06.7-02-PLAN.md -- push_ci_manifest refactor, auto-update task, and publish integration
- [ ] 06.7-03-PLAN.md -- Cleanup task, deletion guards, and management command
- [ ] 06.7-04-PLAN.md -- CI Configuration settings page and navigation

### Phase 06.6: Sync Operations and Logging (INSERTED)

**Goal:** Step repository syncs are triggered by webhooks and scheduled tasks (in addition to manual poll), all sync operations are logged with per-step detail, and branch protection is validated on registration and each sync.
**Depends on:** Phase 6 (all R1/R2 prereqs complete via Phase 6.4 and 6.5)
**Gaps Addressed**: GAP-05, GAP-06, GAP-07 from docs/ci-workflows/REMEDIATION.md
**Success Criteria** (what must be TRUE):
  1. Every sync operation creates a StepsRepoSyncLog with status, timing, trigger, and per-step StepSyncEntry records
  2. Push to a steps repository default branch triggers automatic rescan via webhook at /webhooks/steps-repo/
  3. A management command (scan_all_steps_repos) enqueues scans for all repositories for daily cron
  4. Branch protection is validated via plugin interface (CICapableMixin.check_branch_protection) on each sync
  5. Repo detail page shows sync history table with expandable per-step details
  6. Branch protection status displayed on repo detail page
**Plans:** 3 plans

Plans:
- [x] 06.6-01-PLAN.md — Sync logging models, StepsRepository fields, branch protection plugin interface, scan_steps_repository instrumentation
- [x] 06.6-02-PLAN.md — Steps repo webhook handler, management command for scheduled scan, webhook registration on repo creation
- [x] 06.6-03-PLAN.md — Sync history UI on repo detail page with HTMX expandable detail

### Phase 06.5: Workflow and Build Model Hardening (INSERTED)

**Goal:** CIWorkflow has an explicit engine field set at creation, step ordering is validated before save, and an "archived" status allows graceful deprecation. Build model is engine-agnostic with a generic `ci_run_id` and has a distinct "revoked" verification status.
**Depends on:** Phase 6
**Gaps Addressed**: GAP-08, GAP-09, GAP-10, GAP-15, GAP-16 from docs/ci-workflows/REMEDIATION.md
**Success Criteria** (what must be TRUE):
  1. `CIWorkflow.engine` is set at creation and used everywhere instead of step-derived engine
  2. Invalid step orders are rejected with a clear message in the workflow composer
  3. Archived workflows are hidden from new onboarding but remain functional for existing services
  4. `github_run_id` is renamed to `ci_run_id` (engine-agnostic)
  5. Revoked versions produce `"revoked"` verification status with distinct UI badge
**Plans:** 2 plans

Plans:
- [x] 06.5-01-PLAN.md — CIWorkflow engine field, step ordering validation, archived status
- [x] 06.5-02-PLAN.md — Build model engine-agnostic rename, revoked verification status, map_run_status plugin interface

### Phase 06.4: CI Step Identity and Change Tracking (INSERTED)

**Goal:** Steps have proper identity (globally unique slug per engine), per-file versioning, SHA-based change detection, and soft-delete via archival instead of hard delete
**Depends on:** Phase 6
**Plans:** 3 plans

**Gaps Addressed**: GAP-01, GAP-02, GAP-03, GAP-04 from docs/ci-workflows/REMEDIATION.md

**Success Criteria** (what must be TRUE):
  1. CIStep has slug field with UniqueConstraint on (engine, slug) across entire catalog
  2. scan_steps_repository computes per-file commit SHA via git log (not repo HEAD)
  3. Unchanged steps (same SHA) are skipped during scan
  4. Changed steps are classified as interface or metadata change
  5. Steps removed from repository are archived, not deleted
  6. Archived steps are filtered out of workflow composer step picker
  7. Workflow detail shows warning badges for steps with interface changes or archived status
  8. cleanup_archived_steps task safely removes unreferenced archived steps

Plans:
- [x] 06.4-01-PLAN.md — CIStep model fields (slug, status, file_path, last_change_type), UniqueConstraint, clone_repo_full
- [x] 06.4-02-PLAN.md — Rewrite scan_steps_repository (per-file SHA, slug, collision detection, change detection, archival), cleanup task, ci_manifest filter
- [x] 06.4-03-PLAN.md — Views and templates for archived/changed step badges and warnings

### Phase 06.1: Fix the gap between the CI Workflows design and the actual implementation (INSERTED)

**Goal:** CI Workflows have full version lifecycle (draft/authorized/revoked); builds are verified via manifest hash comparison; plugin interface complete with manifest fetching; deterministic manifest generation with version headers; version management UI enables publishing, revocation, and forking
**Depends on:** Phase 6
**Success Criteria** (what must be TRUE):
  1. CIWorkflowVersion model manages version lifecycle (draft -> authorized -> revoked)
  2. Editing a workflow auto-creates a draft version; publishing assigns semver and immutable hash
  3. Build verification task computes manifest hash at commit SHA and sets verification status (Verified/Draft/Unauthorized)
  4. Plugin interface includes manifest_id, extract_manifest_id, get_manifest_id_pattern, fetch_manifest_content
  5. Generated manifests include deterministic version header ("Managed by Pathfinder")
  6. Workflow detail page has version history tab with publish and revoke actions
  7. Build rows display verification status badge
  8. Workflows can be forked to create new workflows with different runtime sets
  9. Service settings include manifest push method (PR or direct push)
**Plans:** 5 plans

Plans:
- [x] 06.1-01-PLAN.md — CIWorkflowVersion model, Build/Service updates, plugin interface, deterministic manifest
- [x] 06.1-02-PLAN.md — verify_build task, poll_build_details chain, draft auto-creation
- [x] 06.1-03-PLAN.md — Version management UI (publish, version history, revoke)
- [x] 06.1-04-PLAN.md — Build verification badges, fork workflow, service settings
- [x] 06.1-05-PLAN.md — Human verification checkpoint

### Phase 06.2: Deployment Design Documentation (INSERTED)

**Goal:** RFC-style design documentation for Deployments, organized similar to ci-workflows docs; research-driven, abstract from implementation
**Depends on:** Phase 6.1
**Plans:** 3 plans

Plans:
- [x] 06.2-01-PLAN.md — README overview and deployment methods documentation
- [x] 06.2-02-PLAN.md — Deployment lifecycle and promotion documentation
- [x] 06.2-03-PLAN.md — Plugin interface, environment binding, logging, and services.md alignment

### Phase 06.3: Security & Compliance Design — Secrets, SLSA L3, SOX RBAC (INSERTED)

**Goal:** Design documentation for secrets management, artifact provenance signing (SLSA Level 3), and SOX-compliant RBAC changes; incorporate deployment review findings into design docs
**Depends on:** Phase 6.2
**Plans:** 3 plans

Plans:
- [x] 06.3-01-PLAN.md — Security domain README and secrets management documentation
- [x] 06.3-02-PLAN.md — SLSA provenance and artifact signing documentation
- [x] 06.3-03-PLAN.md — SOX-compliant RBAC with granular permissions and approval workflow
