# DevSSP Roadmap

Features and improvements planned for future releases.

## Permissions & Access Control

### Custom SystemRoles
**Status:** Not planned, requires justification and use cases

### OIDC/LDAP Integration
**Status:** Planned

External identity provider integration with single source of truth model.

**Auth Source Modes:**
- `local` (default): Local users and groups
- `external`: OIDC/LDAP as single source of truth

**Unlock Token Lifecycle:**
- Generated on fresh install at `secrets/initialUnlockToken`
- **Deleted immediately** after initial unlock is completed
- Never reused - single-use security mechanism

**Switching to External IDP (via IaC):**
- Local users and groups are deleted
- Audit log entries preserve user snapshots (name, email at action time)
- Auth mode switches to `external`

**Recovery from External IDP Failure:**

| Scenario | Resolution |
|----------|------------|
| IDP temporarily down | Wait for IDP to recover (SSP login unavailable) |
| IDP permanently lost | Reconfigure IaC to new external IDP |
| Switch back to local | Reconfigure IaC to `local` mode |

**IaC Switch to Local Mode:**
- If local users/groups exist: Reactivate them
- If no local setup exists: Treated as fresh install
  - New unlock token generated
  - Admin completes unlock sequence
  - DevSSP creates new local admin group with `admin` SystemRole

**Data Preservation:**
- Audit entries use denormalized user data (snapshot at action time)
- Projects, services, deployments store creator/modifier as text, not FK
- No dangling references when users are deleted

**IaC Configuration Example:**
```yaml
auth:
  mode: external  # or 'local'
  oidc:
    issuer: https://login.example.com
    client_id: devssp-client
    # ... other OIDC config
  group_mapping:
    "oidc-admins": 
      system_roles: [admin]
    "oidc-platform-team":
      system_roles: [operator]
```

**Supported Providers:**
- Azure AD, Okta, Google Workspace (OIDC)
- LDAP/Active Directory

## Infrastructure

### Infra Blueprints
**Status:** Planned

Blueprints for environment/infrastructure provisioning:
- Terraform modules for common patterns
- Kubernetes manifests or Helm charts
- Applied when creating or updating Environments
- GitOps-style infrastructure management

## Integrations

### Additional Plugins
**Status:** Ongoing

Planned integration plugins:
- GitHub (SCM + CI + Artifacts)
- Jenkins (CI)
- Bitbucket (SCM + CI?)
- ArgoCD (GitOps deploy)
- Docker socket local/remote with TLS (direct deploy)
- Kubernetes (direct deploy)

## Services

### Service Activation/Deactivation
**Status:** Planned

Allow owners to temporarily disable services:
- `inactive` status prevents new builds and deployments
- Existing deployments remain running
- Accessible via Service Settings page
- Audit log entry when status changes

**Use Cases:**
- Deprecating an service before deletion
- Temporarily freezing deployments during incidents
- Archiving services no longer in active development

### Secrets Management
**Status:** Planned

Secure handling of sensitive configuration values:
- Integration with external secret stores (Vault, AWS Secrets Manager)
- K8s Secrets / Docker Secrets support
- Secret references in service environment variables
- Rotation and expiry tracking

**MVP Note:** Currently, secrets must be managed externally and referenced by the deployment target (e.g., K8s Secrets mounted as env vars).

---

## CI/CD Enhancements

### Automatic Quality Gates
**Status:** Planned

Automated checks between build and deployment:
- Security vulnerability scanning (Trivy, Snyk)
- Test coverage thresholds
- Static analysis results
- License compliance checks

### Approval Workflows
**Status:** Planned

Multi-user approval for production deployments:
- Configurable per environment (`is_production` triggers approval)
- Approval groups (e.g., "platform-team must approve")
- Time-limited approvals
- Slack/Teams notifications

### Post-Deploy Hooks
**Status:** Planned

Actions to run after successful deployment:
- Smoke tests (HTTP health checks, synthetic tests)
- Database migrations (as pre-deploy step)
- Notification webhooks (Slack, PagerDuty)
- Custom scripts

### Deploy Manifest Management
**Status:** Planned

SSP-managed deployment manifests:
- Kubernetes: DevSSP generates/updates deployment.yaml with correct image tag
- Docker: DevSSP generates docker-compose or run command
- Eliminates manual manifest updates in CI

### Multi-Artifact Services
**Status:** Planned

Support for services producing multiple artifacts:
- Frontend + Backend as single app
- Sidecar containers
- Linked deployments

### Environment-Specific Build Args
**Status:** Planned

Build-time configuration per environment:
- Feature flags baked into build
- Environment-specific optimizations
- Separate artifact per environment

---

## UI/UX

### Dark Mode
**Status:** Implemented (current default)

### Mobile-Responsive Layout
**Status:** Planned

Optimize UI for tablet/mobile viewing of deployment status.

### Real-time Updates
**Status:** Planned

WebSocket-based real-time updates for:
- Deployment status
- Build progress
- Health check changes

---

## Audit & Compliance

### Comprehensive Audit Trails
**Status:** Planned

Extend audit logging beyond permission changes to cover all system actions:

**Audited Actions:**
- Service lifecycle: creation, deletion, status changes
- Build events: started, completed, failed
- Deployment events: triggered, completed, failed, rolled back
- Environment changes: created, modified, deleted
- Integration changes: connection added, modified, removed, health status changes
- Template changes: registered, synced, deleted

**Audit Entry Fields:**
- timestamp, actor (username), action, target_type, target_id
- details (before/after state as JSON)
- ip_address, user_agent
- correlation_id (for tracing related actions)

**Retention & Export:**
- Configurable retention period (default: 1 year)
- Export to external SIEM systems
- Immutable log storage option

---

## Development Workflows

### Branching Strategies
**Status:** Planned

Currently DevSSP assumes trunk-based development (single main branch for builds). Future support for alternative development workflows:

**Strategies to Support:**
- **Trunk-Based** (current): All builds from main branch
- **GitHub Flow**: Feature branches with PR-based merges, builds from main after merge
- **GitFlow**: develop/release/hotfix branches with environment mapping

**Features:**
- Per-service branching strategy configuration
- Branch-to-environment mapping (e.g., develop → dev, main → staging/prod)
- Build triggers per branch pattern
