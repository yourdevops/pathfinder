# Roadmap: DevSSP

## Overview

DevSSP delivers an internal developer platform control plane in 7 phases. Phase 1 establishes secure user management with RBAC and audit logging. Phases 2-3 build the organizational structure (Projects, Environments) and integration infrastructure (GitHub, Docker plugins). Phases 4-5 enable the golden path: Blueprints for templates, Services with wizard-based creation. Phases 6-7 complete the CI/CD loop: Builds from GitHub Actions webhooks, Deployments to Docker containers. The end-to-end flow enables developers to go from "I need a new service" to "it's running" without tickets.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Security** - User authentication, RBAC, groups, audit logging, base UI
- [ ] **Phase 2: Core Domain** - Projects with membership, Environments with deploy targets
- [ ] **Phase 3: Integrations** - Plugin framework, GitHub and Docker connections
- [ ] **Phase 4: Blueprints** - Template registration, versioning, availability filtering
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
- [ ] 01-01-PLAN.md - Core models, dependencies, and settings configuration
- [ ] 01-02-PLAN.md - Tailwind theme with dark mode and navigation component
- [ ] 01-03-PLAN.md - Unlock flow, setup middleware, login/logout authentication
- [ ] 01-04-PLAN.md - User management UI (list, create modal, edit)
- [ ] 01-05-PLAN.md - Group management and audit log viewer
- [ ] 01-06-PLAN.md - Placeholder pages for Blueprints and Connections

### Phase 2: Core Domain
**Goal**: Platform engineers can organize work into Projects; developers have scoped access via group membership
**Depends on**: Phase 1
**Requirements**: PROJ-01, PROJ-02, PROJ-03, PROJ-04, PROJ-05, PROJ-06, PROJ-07, ENV-01, ENV-02, ENV-03, ENV-04, ENV-05, ENV-06, UIUX-02
**Success Criteria** (what must be TRUE):
  1. Admin can create a Project and assign groups with owner/contributor/viewer roles
  2. Project owner can edit settings, manage environment variables, and attach SCM connections
  3. Admin can create Environments within a Project; first environment becomes default
  4. Environment settings include is_production flag and env_vars that inherit from Project
  5. Project detail page shows tabs: Services, Environments, Members, Settings
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Integrations
**Goal**: Platform engineers can register and health-check GitHub and Docker connections
**Depends on**: Phase 2
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04, INTG-05, INTG-06, INTG-07, INTG-08, INTG-09
**Success Criteria** (what must be TRUE):
  1. Operator can register a GitHub connection with App credentials; sensitive fields are encrypted
  2. Operator can register a Docker connection with socket path; health check shows container daemon status
  3. GitHub connection can create repositories, create branches/commits, and configure webhook secrets
  4. Docker connection can deploy a container and check its running status
  5. Connection list shows health status (healthy/unhealthy/unknown) for each connection
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

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
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

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
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Security | 0/6 | Planned | - |
| 2. Core Domain | 0/2 | Not started | - |
| 3. Integrations | 0/2 | Not started | - |
| 4. Blueprints | 0/2 | Not started | - |
| 5. Services | 0/3 | Not started | - |
| 6. Builds | 0/2 | Not started | - |
| 7. Deployments | 0/2 | Not started | - |

---
*Roadmap created: 2026-01-22*
*Last updated: 2026-01-22*
