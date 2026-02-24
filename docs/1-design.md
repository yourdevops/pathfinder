# Pathfinder - Self-Service Portal for Developers

Status: Stale, needs review

This document contains the design specification for Pathfinder features. It serves as the source of truth for implementation.

## Design Principles

### Core Insight: Orchestrate, Don't Rebuild

The most successful IDPs (Backstage, Port, Humanitec) follow a pattern: they orchestrate existing tools, not replace them. Pathfinder should be the unified UI and control plane, delegating execution to battle-tested tools.

### Naming Convention

**All entities use a single `name` field as both identifier and display name.**

Rules:
- Format: `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` (lowercase alphanumeric with hyphens)
- Maximum length: 63 characters (DNS label limit)
- No consecutive hyphens (`--`)
- Must start and end with alphanumeric character
- No separate "slug" fields - the name IS the identifier

Rationale:
- Forces clear, consistent naming across all entities
- Names are directly usable in DNS, container names, K8s resources, URLs
- Eliminates confusion between "display name" vs "slug" vs "identifier"
- Description field provides space for human-friendly context

Applies to: Projects, Services, Environments, Integrations, Blueprints
Excludes: User names (follows OS/LDAP standards)

**Composite identifiers** follow the same rules:
- `service_handler`: `{project-name}-{service-name}` (max 63 chars total)
- Deployment name: `{project-name}-{service-name}-{env-name}` (max 63 chars total)

Length budgeting:
- Project name: max 20 chars recommended
- Service name: max 40 chars (leaves room for project prefix)
- Environment name: max 20 chars (leaves room in deployment name)

**Description Field**

Every entity has an optional `description` field (text, no length limit) for:
- Human-friendly labels and context
- Notes about purpose or ownership
- Any customization that doesn't fit the strict name format

---

## Projects

Projects are the primary organizational unit in Pathfinder. They group related Services, Environments, and define shared configuration.

See [projects.md](projects.md) for full documentation including:
- Project model and features
- Membership and roles
- Environment variables with lock control
- UI design

---

## Services

Services are deployable application configurations within a Project. They define WHAT to build and deploy, while Environments define WHERE to deploy.

See [Services.md](Services.md) for full documentation including:
- Service, Build, and Deployment models
- Complete lifecycle with state transitions
- CI/CD integration via webhooks
- Artifact promotion across environments
- UI wireframes

---

## Blueprints

Blueprints are reusable configuration blueprints. Two types exist:

**Service Blueprints**
- Git repositories containing source scaffolding, CI config, and deployment metadata
- Defined by an `ssp-template.yaml` manifest in the repository
- See [service-Blueprints.md](service-Blueprints.md) for full documentation

**Infra Blueprints** (Future)
- Used for automated environment/infrastructure provisioning
- Contains: Terraform modules, Kubernetes manifests or Helm charts
- Applied when creating or updating Environments
- Not in scope for initial implementation

### Template Availability

An Service Template is available in a Project when at least one Environment in that Project has a Connection matching the template's `required_plugins` (from manifest).

```
Project: team-a
  └─ Environments:
      ├─ dev (connections: dev-k3s [kubernetes], jenkins-cd [jenkins])
      └─ prod (connections: prod-eks [kubernetes])

Available Blueprints:
  ├─ python-k8s-service (requires: kubernetes) ✓
  ├─ python-lambda-vpc (requires: jenkins) ✓
  └─ go-ecs-fargate (requires: ecs) ✗ (no ECS connection)
```

---

## Environments

Environments are deployment target configurations within a Project.

See [environments.md](environments.md) for full documentation including:
- Environment model and connections
- Deployment patterns (direct, GitOps, pipeline)
- Production safeguards
- Environment lifecycle
- UI design

---

## Integrations

See [integrations.md](integrations.md) for the complete integration architecture, including:
- IntegrationPlugin (code-defined integration types)
- IntegrationConnection (configured instances)
- Categories and capabilities
- UI design for Connections and Plugins pages

---

## Users & Permissions

See [rbac.md](rbac.md) for the complete permission model, including:
- Users and baseline authenticated access
- Groups and Group Membership
- SystemRoles (predefined: `admin`, `operator`, `auditor`, `user`)
- Project Membership via Groups (project roles: owner, contributor, viewer)
- Permission Matrix and Audit Export

---

## Logging

Three log streams with distinct consumers: audit log (compliance), activity log (platform engineers), system log (ops).

See [logging.md](logging.md) for the complete logging architecture, including:
- Audit log model and audited actions
- Activity logs (Steps Repository sync log, per-step import entries)
- System log format and configuration
- Log export: container-native collection, dual-write to stdout, pull API
- Access control per stream

---

## Repository Model

Repositories are tracked references to SCM repositories used by Services.

```
Repository:
  - id: UUID
  - name: string (DNS-compatible)
  - connection: FK IntegrationConnection (SCM type)
  - external_url: string (e.g., github.com/org/repo)
  - external_id: string (provider's repo ID)
  - created_by: string (username, denormalized)
  - created_at, updated_at: datetime
```

---

## Glossary

| Term | Definition |
|------|------------|
| **Organization** | Pathfinder instance scope. Single-org by default, multi-org achieved by multiple instances. |
| **User** | An authenticated user of the Pathfinder system |
| **Group** | Container for users; can have SystemRoles and be assigned to projects |
| **SystemRole** | Predefined system-wide role: `admin`, `operator`, `auditor`, `user` (baseline) |
| **ProjectRole** | Role within a project context: `owner`, `contributor`, `viewer` |
| **ProjectMembership** | Assignment of a Group to a Project with a project role |
| **Project** | Primary organizational unit grouping Services and Environments |
| **Service** | Deployable application configuration. Belongs to exactly one Project. |
| **Service Handler** | Composite identifier for an Service: `{project-name}-{service-name}` (field: `service_handler`) |
| **Environment** | Logical deployment stage within a Project (dev, staging, prod) |
| **Deployment** | Instance of an Service in an Environment: `{service_handler}-{env-name}` |
| **Repository** | Tracked reference to an SCM repository used by an Service |
| **IntegrationPlugin** | Code class defining an integration type (GitHub, Jenkins, Kubernetes) |
| **IntegrationConnection** | Configured instance of a plugin connecting to an external service |
| **Service Template** | Git repo with `ssp-template.yaml` manifest defining source, CI, and deployment config |
| **Deploy Type** | How an service is packaged/runs: container, serverless, or static |
| **Deploy Mechanism** | How deployment is executed: direct API, GitOps, or pipeline trigger |
| **Infra Template** | Reusable infrastructure provisioning blueprint (future) |
| **Golden Path** | A pre-approved, well-tested application pattern curated by Platform team |
| **Audit Log** | Append-only record of who changed what, when. Stored in database, exported via dual-write to stdout. |
| **Activity Log** | Operation-scoped log of what happened during a batch process (e.g., steps repo sync). Stored in database. |
| **System Log** | Structured JSON to stdout for operational debugging. Collected by container platform. |
