# Requirements: DevSSP

**Defined:** 2026-01-21
**Core Value:** Developers can deploy production-ready services in minutes through self-service, while platform teams maintain governance and visibility.

## v1 Requirements

Requirements for MVP release. Complete end-to-end flow: Blueprint -> GitHub Actions CI -> Docker deployment.

### Foundation

- [x] **FNDN-01**: Fresh install generates unlock token at `secrets/initialUnlockToken`
- [x] **FNDN-02**: First visitor sees unlock page requiring token
- [x] **FNDN-03**: After unlock, user creates first admin account (username, email, password)
- [x] **FNDN-04**: System auto-creates "admins" group with admin SystemRole
- [x] **FNDN-05**: First user automatically added to admins group
- [x] **FNDN-06**: Unlock token deleted after successful initial setup
- [x] **FNDN-07**: Admin can create additional users with username, email, password
- [x] **FNDN-08**: Admin can create groups and assign users to groups
- [x] **FNDN-09**: Admin can assign SystemRoles (admin, operator, auditor) to groups
- [x] **FNDN-10**: User session persists across browser refresh
- [x] **FNDN-11**: User can log out from any page
- [x] **FNDN-12**: Authenticated users can view blueprints list (cards only)
- [x] **FNDN-13**: Authenticated users can view connections list (cards only)
- [x] **FNDN-14**: All entity changes are logged with actor, action, timestamp

### Projects

- [x] **PROJ-01**: Admin can create projects with name and description
- [x] **PROJ-02**: Admin can assign groups to projects with project role (owner, contributor, viewer)
- [x] **PROJ-03**: Project owner can edit project settings
- [x] **PROJ-04**: Project owner can manage environment variables (key, value, lock)
- [ ] **PROJ-05**: Project owner can attach SCM connections to project (deferred to Phase 3)
- [x] **PROJ-06**: Contributors can view project details and services
- [x] **PROJ-07**: Viewers have read-only access to project

### Environments

- [x] **ENV-01**: Admin can create environments within a project (dev, staging, prod)
- [ ] **ENV-02**: Admin can attach deploy connections to environments (deferred to Phase 3)
- [x] **ENV-03**: Environment has is_production flag for safeguards
- [x] **ENV-04**: Environment has env_vars that inherit from project
- [x] **ENV-05**: Project owner can edit environment settings
- [x] **ENV-06**: First environment becomes default for project

### Integrations

- [ ] **INTG-01**: Operator can register GitHub connection with App credentials
- [ ] **INTG-02**: Operator can register Docker connection with socket path
- [ ] **INTG-03**: Connection stores sensitive fields encrypted (Fernet)
- [ ] **INTG-04**: Connection health check shows status (healthy, unhealthy, unknown)
- [ ] **INTG-05**: GitHub connection can create repositories
- [ ] **INTG-06**: GitHub connection can create branches and commits
- [ ] **INTG-07**: GitHub connection can configure webhook secrets
- [ ] **INTG-08**: Docker connection can deploy containers
- [ ] **INTG-09**: Docker connection can check container status

### Blueprints

- [ ] **BPRT-01**: Operator can register blueprint from git URL
- [ ] **BPRT-02**: Blueprint syncs metadata from ssp-template.yaml manifest
- [ ] **BPRT-03**: Blueprint shows available git tags as versions
- [ ] **BPRT-04**: Blueprint displays name, description, tags, ci.plugin, deploy.plugin
- [ ] **BPRT-05**: Operator can manually sync blueprint to refresh versions
- [ ] **BPRT-06**: Blueprint availability filtered by project's environment connections

### Services

- [ ] **SRVC-01**: Contributor can create service via wizard
- [ ] **SRVC-02**: Wizard Page 1: select project, select blueprint, enter service name
- [ ] **SRVC-03**: Wizard Page 2: select SCM connection, choose new/existing repo, configure branch
- [ ] **SRVC-04**: Wizard Page 3: configure container settings (port, resources, health check)
- [ ] **SRVC-05**: Wizard Page 4: review and create
- [ ] **SRVC-06**: Service creation scaffolds repository from blueprint
- [ ] **SRVC-07**: Service handler computed as {project-name}-{service-name}
- [ ] **SRVC-08**: Service tracks current build and artifact reference
- [ ] **SRVC-09**: Contributor can view service details (overview, builds, deployments)
- [ ] **SRVC-10**: Project owner can delete service

### Builds

- [ ] **BILD-01**: GitHub Actions can call build started webhook
- [ ] **BILD-02**: GitHub Actions can call build complete webhook with artifact ref
- [ ] **BILD-03**: Webhook validates authentication token
- [ ] **BILD-04**: Build record stores commit SHA, status, artifact ref, CI job URL
- [ ] **BILD-05**: Service status transitions from draft to active on first successful build
- [ ] **BILD-06**: User can view build history for a service

### Deployments

- [ ] **DPLY-01**: Contributor can deploy service to non-production environment
- [ ] **DPLY-02**: Project owner can deploy service to production environment
- [ ] **DPLY-03**: Deploy modal shows environment selector and build selector
- [ ] **DPLY-04**: Deploy modal shows merged environment variables
- [ ] **DPLY-05**: Deployment calls Docker plugin to run container
- [ ] **DPLY-06**: Deployment tracks status (pending, running, success, failed)
- [ ] **DPLY-07**: User can view deployment history per environment
- [ ] **DPLY-08**: Deployment stores artifact ref snapshot

### UI/UX

- [x] **UIUX-01**: Navigation shows Projects, Blueprints, Connections based on permissions
- [x] **UIUX-02**: Project detail page has tabs: Services, Environments, Members, Settings
- [ ] **UIUX-03**: Service detail page has tabs: Overview, Builds, Deployments
- [x] **UIUX-04**: HTMX-powered dynamic updates (no full page reloads for actions)
- [x] **UIUX-05**: Dark mode UI theme
- [ ] **UIUX-06**: Form validation with inline error messages

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Authentication

- **AUTH-01**: User can authenticate via OIDC provider (Azure AD, Okta)
- **AUTH-02**: Groups can sync from LDAP/AD
- **AUTH-03**: External group mapping to SystemRoles via configuration

### Deployments

- **DPLY-10**: Service can deploy via GitOps mechanism (ArgoCD)
- **DPLY-11**: Multi-user approval workflow for production deployments
- **DPLY-12**: Deployment can trigger post-deploy hooks (smoke tests)

### Blueprints

- **BPRT-10**: Infra Blueprints for environment-scoped resources (Terraform, Helm)
- **BPRT-11**: Service can bind to environment Resources

### Observability

- **OBSV-01**: Service scorecards for maturity tracking
- **OBSV-02**: Observability tool links (Datadog, Grafana dashboards)
- **OBSV-03**: Real-time WebSocket updates for build/deploy status

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Custom CI system | Orchestrate Jenkins/GitHub Actions, don't replace them |
| Built-in secrets storage | Security liability; use Vault/K8s Secrets externally |
| Custom container runtime | Delegate to Docker/Kubernetes |
| Full PaaS functionality | DevSSP is control plane, not compute plane |
| Multi-tenancy (isolated DBs) | Single org per instance; deploy multiple for isolation |
| Service dependency graphs | High complexity, defer to v2+ |
| AI-assisted features | Emerging tech, not essential for MVP |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FNDN-01 | Phase 1 | Pending |
| FNDN-02 | Phase 1 | Pending |
| FNDN-03 | Phase 1 | Pending |
| FNDN-04 | Phase 1 | Pending |
| FNDN-05 | Phase 1 | Pending |
| FNDN-06 | Phase 1 | Pending |
| FNDN-07 | Phase 1 | Pending |
| FNDN-08 | Phase 1 | Pending |
| FNDN-09 | Phase 1 | Pending |
| FNDN-10 | Phase 1 | Pending |
| FNDN-11 | Phase 1 | Pending |
| FNDN-12 | Phase 1 | Pending |
| FNDN-13 | Phase 1 | Pending |
| FNDN-14 | Phase 1 | Pending |
| UIUX-01 | Phase 1 | Pending |
| UIUX-05 | Phase 1 | Pending |
| PROJ-01 | Phase 2 | Complete |
| PROJ-02 | Phase 2 | Complete |
| PROJ-03 | Phase 2 | Complete |
| PROJ-04 | Phase 2 | Complete |
| PROJ-05 | Phase 3 | Pending |
| PROJ-06 | Phase 2 | Complete |
| PROJ-07 | Phase 2 | Complete |
| ENV-01 | Phase 2 | Complete |
| ENV-02 | Phase 3 | Pending |
| ENV-03 | Phase 2 | Complete |
| ENV-04 | Phase 2 | Complete |
| ENV-05 | Phase 2 | Complete |
| ENV-06 | Phase 2 | Complete |
| UIUX-02 | Phase 2 | Complete |
| UIUX-04 | Phase 2 | Complete |
| INTG-01 | Phase 3 | Pending |
| INTG-02 | Phase 3 | Pending |
| INTG-03 | Phase 3 | Pending |
| INTG-04 | Phase 3 | Pending |
| INTG-05 | Phase 3 | Pending |
| INTG-06 | Phase 3 | Pending |
| INTG-07 | Phase 3 | Pending |
| INTG-08 | Phase 3 | Pending |
| INTG-09 | Phase 3 | Pending |
| BPRT-01 | Phase 4 | Pending |
| BPRT-02 | Phase 4 | Pending |
| BPRT-03 | Phase 4 | Pending |
| BPRT-04 | Phase 4 | Pending |
| BPRT-05 | Phase 4 | Pending |
| BPRT-06 | Phase 4 | Pending |
| SRVC-01 | Phase 5 | Pending |
| SRVC-02 | Phase 5 | Pending |
| SRVC-03 | Phase 5 | Pending |
| SRVC-04 | Phase 5 | Pending |
| SRVC-05 | Phase 5 | Pending |
| SRVC-06 | Phase 5 | Pending |
| SRVC-07 | Phase 5 | Pending |
| SRVC-08 | Phase 5 | Pending |
| SRVC-09 | Phase 5 | Pending |
| SRVC-10 | Phase 5 | Pending |
| UIUX-03 | Phase 5 | Pending |
| UIUX-04 | Phase 5 | Pending |
| UIUX-06 | Phase 5 | Pending |
| BILD-01 | Phase 6 | Pending |
| BILD-02 | Phase 6 | Pending |
| BILD-03 | Phase 6 | Pending |
| BILD-04 | Phase 6 | Pending |
| BILD-05 | Phase 6 | Pending |
| BILD-06 | Phase 6 | Pending |
| DPLY-01 | Phase 7 | Pending |
| DPLY-02 | Phase 7 | Pending |
| DPLY-03 | Phase 7 | Pending |
| DPLY-04 | Phase 7 | Pending |
| DPLY-05 | Phase 7 | Pending |
| DPLY-06 | Phase 7 | Pending |
| DPLY-07 | Phase 7 | Pending |
| DPLY-08 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 72 total
- Mapped to phases: 72
- Unmapped: 0

---
*Requirements defined: 2026-01-21*
*Last updated: 2026-01-22 after roadmap creation*
