# Roadmap: DevSSP

## Overview

DevSSP delivers an internal developer platform control plane in 7 phases. Phase 1 establishes secure user management with RBAC and audit logging. Phases 2-3 build the organizational structure (Projects, Environments) and integration infrastructure (GitHub, Docker plugins). Phases 4-5 enable the golden path: Blueprints for templates, Services with wizard-based creation. Phases 6-7 complete the CI/CD loop: Builds from GitHub Actions webhooks, Deployments to Docker containers. The end-to-end flow enables developers to go from "I need a new service" to "it's running" without tickets.

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
- [ ] **Phase 5: Services** - Creation wizard, repository scaffolding, service management
- [ ] **Phase 6: Builds** - Webhook ingestion, build tracking, service activation
- [ ] **Phase 7: Deployments** - Deploy flow, Docker execution, deployment history

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
  3. Wizard Page 3 configures container: port, resources, health check endpoint
  4. Wizard Page 4 shows review summary; clicking Create scaffolds repository from blueprint
  5. Service detail page shows tabs: Overview, Builds, Deployments with HTMX dynamic updates
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

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
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Deployments
**Goal**: Developers can deploy services to environments; Docker plugin runs containers
**Depends on**: Phase 6
**Requirements**: DPLY-01, DPLY-02, DPLY-03, DPLY-04, DPLY-05, DPLY-06, DPLY-07, DPLY-08
**Success Criteria** (what must be TRUE):
  1. Contributor can deploy service to non-production environment; owner required for production
  2. Deploy modal shows environment selector, build selector, and merged environment variables
  3. Deployment triggers Docker plugin to run container with configured settings
  4. Deployment shows status progression: pending -> running -> success/failed
  5. User can view deployment history per environment with artifact reference snapshot
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 3.1 -> 4 -> 4.1 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Security | 6/6 | Complete | 2026-01-22 |
| 2. Core Domain | 4/4 | Complete | 2026-01-22 |
| 3. Integrations | 6/6 | Complete | 2026-01-23 |
| 3.1 Unified Sidebar Navigation (INSERTED) | 3/3 | Complete | 2026-01-26 |
| 4. Blueprints | 3/3 | Complete | 2026-01-26 |
| 4.1 Replace UUID URLs with Slugs (INSERTED) | 4/4 | Complete | 2026-01-26 |
| 5. Services | 0/3 | Not started | - |
| 6. Builds | 0/2 | Not started | - |
| 7. Deployments | 0/2 | Not started | - |

---
*Roadmap created: 2026-01-22*
*Last updated: 2026-01-26 (Phase 4.1 complete - slug URLs for all entities)*
