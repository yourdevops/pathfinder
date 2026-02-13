# SOX-Compliant RBAC

Pathfinder's access control model uses granular CRUD permissions organized into predefined role bundles across two scoping tiers: system-wide and project-level. This replaces the original owner/contributor/viewer model ([docs/rbac.md](../rbac.md)) with fine-grained control suitable for regulated industries. Production-specific behavior (approval workflow, attestation verification) is triggered by `Environment.is_production`, not by per-environment role assignments. The model enforces segregation of duties (SOX compliance) through an explicit approval workflow for production deployments.

## Permission Model

The atomic permission unit is:

```
Permission = (resource_type, action)
```

### Resource Types

| Resource Type | Description | Example Actions |
|---------------|-------------|-----------------|
| `service` | Services within a project | create, read, update, delete |
| `deployment` | Deployment operations | create, read, deploy, approve |
| `ci_workflow` | CI Workflow definitions | create, read, update, delete |
| `secret` | Secret values | create, read (names only), update, delete |
| `connection` | Integration connections | create, read, update, delete |
| `environment` | Project environments | create, read, update, delete |
| `project` | Projects | create, read, update, delete |
| `user` | User accounts | create, read, update, delete |
| `group` | Groups and memberships | create, read, update, delete |
| `audit_log` | Audit trail | read, export |
| `steps_repo` | CI Steps repositories | create, read, update, delete |

**Standard actions:** `create`, `read`, `update`, `delete`.

**Special actions:** `deploy` (trigger deployment), `approve` (approve production deployment), `export` (generate reports).

Permissions are data-driven (defined in Django settings/fixtures), not hardcoded in view logic. This enables future Config-as-Code without code changes.

## Predefined Role Bundles

Pathfinder ships with 7 predefined role bundles across two tiers. Custom roles can be defined via Django settings/fixtures (Config-as-Code designed in a future phase).

### System Roles (Platform-Wide)

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `platform-admin` | Full system access | All permissions on all resource types |
| `platform-operator` | Manage integrations and infrastructure | CRUD on connection, steps_repo, environment; read on all other types |
| `security-auditor` | Read-only compliance view | Read on all resource types; read + export on audit_log |
| `secrets-admin` | Manage secrets across projects | CRUD on secret (system-wide scope); read on project, environment |

### Project Roles (Single Project Scope)

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `maintainer` | Project administration (non-destructive) | Update project settings; manage members (CRUD on group membership within project); update environment settings; read on all project resources |
| `release-manager` | Approve production deployments | Approve on deployment (production); deploy on deployment (all environments); read on all project resources |
| `developer` | Build and deploy non-production | CRUD on service, ci_workflow; deploy on deployment (non-prod only); create + update on secret; read on all project resources |
| `viewer` | Read-only project access | Read on all project resource types |

**Design rationale:** Destructive operations (create/delete project, create/delete environment) are platform concerns handled by system roles (`platform-operator`, `platform-admin`). Project roles govern work *within* an existing project structure. The `maintainer` manages members and settings; the `release-manager` approves releases; neither can alter the project's infrastructure.

## Two-Tier Scoping

Resolution order (highest priority first):

1. **System role** (highest priority) -- overrides all. If a user has `platform-admin`, they can do anything regardless of project roles. If a user has `security-auditor`, they can read all resources system-wide.
2. **Project role** -- base project access. Assigned via GroupMembership -> ProjectMembership. Highest project role wins when a user is in multiple groups with different roles (same behavior as the current model).
3. **Implicit authenticated user** -- baseline read access to plugins list, own project memberships.

**Production behavior:** When `Environment.is_production` is true, deployments require approval from a user with `release-manager` role (who is not the requester). No per-environment role assignments -- the `is_production` flag drives the behavior.

### Example Scenario

```
User: alice
  System roles: (none)
  Groups: [team-a-devs, senior-devs]

Group: team-a-devs
  Project "frontend": developer

Group: senior-devs
  Project "frontend": maintainer
  Project "backend": developer

Alice's effective permissions:
  frontend: maintainer (highest of developer, maintainer)
    -> can manage members and project settings; cannot approve production deployments
  backend: developer
    -> can deploy to non-prod only; cannot approve production deployments

User: bob
  Groups: [release-team]

Group: release-team
  Project "frontend": release-manager

Bob's effective permissions:
  frontend: release-manager
    -> can approve production deployments; cannot manage members or settings
```

## Production Approval Workflow

The four-eyes principle requires that the person requesting a production deployment cannot approve their own request.

### Approval Model

```
DeploymentApproval:
  - deployment: FK Deployment (OneToOne)
  - requested_by: FK User
  - requested_at: datetime
  - approved_by: FK User (nullable -- null until approved)
  - approved_at: datetime (nullable)
  - rejected_by: FK User (nullable)
  - rejected_at: datetime (nullable)
  - expires_at: datetime
  - status: enum (pending, approved, rejected, expired)
  - reason: text (required for rejection)
  - emergency_override: bool (default false)
  - override_justification: text (required if emergency_override is true)
```

**Constraint:** `approved_by != requested_by` (enforced at model validation level). This is the core of the four-eyes principle -- the person requesting deployment cannot approve their own request.

### Workflow Steps

1. User with `deploy` permission requests deployment to a production environment (any environment where `is_production = true`)
2. Pathfinder creates Deployment with status `pending_approval` and DeploymentApproval with status `pending`
3. Approval expiry set to `now + 4 hours` (default, configurable per environment)
4. Users with `release-manager` project role receive notification
5. Approver (must be different user) reviews deployment details: artifact, build verification status, env var snapshot, secret refs
6. **Approve:** DeploymentApproval status -> `approved`, Deployment status -> `pending` (enters normal deployment flow)
7. **Reject:** DeploymentApproval status -> `rejected`, Deployment status -> `cancelled`, reason recorded
8. **Expire:** Background task checks pending approvals past `expires_at`, transitions to `expired`, Deployment -> `cancelled`

**Non-production environments:** No approval required. Deployment goes directly to `pending` status. This is the current behavior and remains unchanged.

**Configurable per environment:** The approval requirement is tied to `Environment.is_production`. Environments can opt in to approval even if not marked as production (future enhancement -- not in initial design).

## Emergency Override

For urgent situations, `platform-admin` users can bypass the approval workflow:

- Only users with `platform-admin` system role can trigger an emergency override
- Emergency override requires:
  1. Mandatory justification text field (minimum 20 characters)
  2. `emergency_override = true` on DeploymentApproval record
  3. Audit log entry at CRITICAL level with justification
  4. Visual indicator in deployment history: red "Emergency Override" badge
  5. Weekly compliance report includes all emergency overrides for review
- Self-approval IS allowed during emergency override (platform-admin can both request and approve). This is acceptable from a compliance standpoint because the emergency override substitutes a compensating control: mandatory written justification, CRITICAL-level audit entry, and inclusion in the weekly compliance report. Auditors can verify that every override was warranted after the fact.
- **Post-incident review required:** Within 48 hours of an emergency override, a user with `security-auditor`, `platform-admin`, or `release-manager` role (who is not the person who invoked the override) must mark it as "reviewed" with a brief assessment. This restores the second-pair-of-eyes principle in a post-hoc fashion. The `DeploymentApproval` model extends with `reviewed_by` (FK User, nullable), `reviewed_at` (datetime, nullable), and `review_notes` (text). Unreviewed overrides past the 48-hour window raize additional alerts and are surfaced in the compliance report as findings.
- Emergency overrides are expected to be rare; override frequency is tracked as an operational health metric (see [DORA Metrics](../dora-metrics.md))

## Deployment Lifecycle Extension

The approval workflow extends the deployment lifecycle defined in [deployment-lifecycle.md](../deployments/deployment-lifecycle.md):

**New status:** `pending_approval` inserted before `pending` for production deployments.

**Status flow for production:**
```
pending_approval -> pending -> running -> health_check -> success/failed
```

**Status flow for non-production (unchanged):**
```
pending -> running -> health_check -> success/failed
```

The `triggered_by` field remains on the Deployment record. The `approved_by` attribution is added via the DeploymentApproval model, providing full dual-user attribution for production deployments.

## Migration from Current Model

Mapping from old roles to new roles:

| Old Role | New Role | Notes |
|----------|----------|-------|
| System: `admin` | `platform-admin` | Full system access preserved |
| System: `operator` | `platform-operator` | Scope unchanged |
| System: `auditor` | `security-auditor` | Gains export permission |
| System: `user` (implicit) | Implicit authenticated | Baseline read unchanged |
| Project: `owner` | `maintainer` | Non-destructive project admin; create/delete operations move to system roles |
| Project: `contributor` | `developer` | Deploy permission now non-prod only |
| Project: `viewer` | `viewer` | Read-only unchanged |

**Key changes:**
- Old `owner` had full project control including destructive operations. New `maintainer` is non-destructive -- create/delete project and environment operations move to `platform-operator`/`platform-admin` system roles.
- Old `contributor` could not deploy to production (owner-only). New `developer` also cannot. The new `release-manager` role handles production deployment approval as a separate concern.

**New roles without old equivalents:**
- `secrets-admin`: System-wide secret management. Addresses the need for a dedicated role governing secret access across projects (cross-reference [secrets.md](secrets.md)).
- `release-manager`: Production deployment approval separated from project administration. Enables dedicated release engineering teams.
- `maintainer`: Non-destructive project administration (members, settings) without the power to delete projects or environments.

## Addressing "Authorization Insufficient" Finding

The original deployment design allowed a project owner to both write code and deploy to production, which fails SOX audits. This design directly addresses that gap:

- **Four-eyes principle enforced:** DeploymentApproval with `approved_by != requested_by` constraint ensures no single user can both request and approve a production deployment
- **Role separation:** The `release-manager` role separates deployment approval capability from development capability. A developer can request a deployment; a release manager (who is a different person) approves it
- **Emergency override:** Provides the "break glass" mechanism without weakening the default controls. Platform-admin can bypass approval with mandatory justification and full audit trail
- **Audit trail:** Every production deployment records who requested, who approved, when, and whether an emergency override was used

## Access Control Summary

### System Roles -- Permission Matrix

| Resource | Action | platform-admin | platform-operator | security-auditor | secrets-admin |
|----------|--------|:-:|:-:|:-:|:-:|
| user | CRUD | * | - | - | - |
| group | CRUD | * | - | - | - |
| project | create | * | - | - | - |
| project | read | * | * | * | * |
| project | update/delete | * | - | - | - |
| environment | CRUD | * | * | - | - |
| connection | CRUD | * | * | - | - |
| steps_repo | CRUD | * | * | - | - |
| secret | CRUD | * | - | - | * |
| service | read | * | * | * | - |
| deployment | read | * | * | * | - |
| ci_workflow | read | * | * | * | - |
| audit_log | read | * | - | * | - |
| audit_log | export | * | - | * | - |

`*` = granted, `-` = denied

### Project Roles -- Permission Matrix

| Resource | Action | maintainer | release-manager | developer | viewer |
|----------|--------|:-:|:-:|:-:|:-:|
| service | create | - | - | * | - |
| service | read | * | * | * | * |
| service | update | - | - | * | - |
| service | delete | - | - | - | - |
| deployment | read | * | * | * | * |
| deployment | deploy (non-prod) | - | * | * | - |
| deployment | deploy (production) | - | * | - | - |
| deployment | approve | - | * | - | - |
| ci_workflow | CRUD | - | - | * | - |
| ci_workflow | read | * | * | * | * |
| secret | create/update | - | - | * | - |
| secret | read (names) | * | * | * | * |
| secret | delete | - | - | - | - |
| environment | read | * | * | * | * |
| environment | update | * | - | - | - |
| project | update | * | - | - | - |
| group (membership) | CRUD | * | - | - | - |

`*` = granted, `-` = denied

**Notes:**
- System roles override project roles. A `platform-admin` has full access regardless of project membership.
- Project role permissions apply within the scope of the assigned project only.
- `maintainer` administers members and settings, not resources. It has no deploy, service CRUD, or secret write capabilities. This is intentional: the maintainer role governs *who* can work on a project and *how* it is configured, while `developer` governs *what* gets built. Destructive operations (delete project/environment) require `platform-operator` or `platform-admin`.
- `release-manager` can deploy to all environments (including non-prod) and approve production deployments, but cannot modify services, workflows, or project settings. Non-prod deploy access is intentional: release managers need to verify staging before approving production, and restricting them to production-only would create unnecessary friction.
- `deploy (production)` triggers the approval workflow -- the deploying user requests, a different user with `approve` permission approves.
- `secret read (names)` returns secret names and metadata only, never values. Secret values are write-only per [secrets.md](secrets.md).
