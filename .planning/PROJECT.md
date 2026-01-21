# DevSSP

## What This Is

DevSSP is a lightweight internal developer platform that turns existing templates and CI/CD into governed, self-service workflows. It acts as a control plane that orchestrates external tools (SCM, CI, deployment targets) rather than replacing them. Platform engineers define "golden paths" as blueprints; developers use a wizard-based UI to create and deploy services without needing to understand the underlying infrastructure.

## Core Value

**Developers can deploy production-ready services in minutes through self-service, while platform teams maintain governance and visibility.**

If everything else fails, developers must be able to go from "I need a new service" to "it's running" without filing tickets or waiting.

## Requirements

### Validated

Existing codebase and design documentation:

- ✓ Django project structure with settings, URLs, WSGI/ASGI — existing
- ✓ Docker deployment setup (Dockerfile, docker-compose, entrypoint) — existing
- ✓ Comprehensive design documentation in `docs/` — existing
- ✓ Codebase analysis in `.planning/codebase/` — existing

### Active

**RBAC & User Management:**

- [ ] Django AbstractUser extension with `source` and `external_id` fields for SSO
- [ ] Django built-in Group model for user containers
- [ ] django-guardian for object-level permissions
- [ ] SystemRoleAssignment model (group → admin/operator/auditor)
- [ ] ProjectMembership model (group → project with owner/contributor/viewer role)
- [ ] Support both `local` and `external` auth modes
- [ ] Baseline platform discovery for authenticated users (view blueprints, connections, docs)
- [ ] Initial unlock flow with auto-created admin group

**Integration Plugins:**

- [ ] GitHub plugin (SCM + CI + Artifacts): repo management, webhook configuration, workflow status polling
- [ ] Docker plugin (Deploy): container deployment via Docker socket
- [ ] Plugin registry with auto-discovery at startup
- [ ] IntegrationConnection model with encrypted sensitive fields

**Connection Scoping:**

- [ ] SCM connections at Project level
- [ ] Deploy connections at Environment level
- [ ] Simplified routing: template declares `ci.plugin` + `deploy.plugin`, match by type

**Service Blueprints:**

- [ ] Template manifest (`ssp-template.yaml`) with `ci.plugin` and `deploy.plugin`
- [ ] Template versioning via git tags
- [ ] Pin version at service creation, manual upgrade path
- [ ] Service creation wizard (4 pages: path, source, config, review)

**Infrastructure Resources:**

- [ ] Resource model (environment-scoped infrastructure)
- [ ] Infra Blueprints (Terraform, Helm) provisioned by platform engineers
- [ ] Resource bindings from Services to environment Resources

**Core Entities:**

- [ ] Project model with membership, SCM connections, env vars
- [ ] Environment model with deploy connections, Resources
- [ ] Service model with template, version, builds, deployments
- [ ] Build model with artifact tracking, status from webhooks
- [ ] Deployment model with environment-specific config

**Webhook API:**

- [ ] Build started/complete webhooks with authenticated secrets
- [ ] Deploy complete webhooks
- [ ] CI plugin provisions webhook secrets on repo

### Out of Scope

| Feature | Reason |
|---------|--------|
| Custom SystemRoles | Predefined roles sufficient; add complexity only if proven need |
| Multi-tenancy | Single org per instance; deploy multiple instances for isolation |
| Secrets management | Use external stores (Vault, K8s Secrets); DevSSP stores references only |
| Approval workflows | Deferred to future; production deploy requires owner role for now |
| Real-time WebSocket updates | Polling sufficient for MVP; add if UX demands it |
| Mobile-responsive UI | Desktop-first; platform engineers use laptops |

## Context

**Brownfield project:** Django project structure exists with Docker deployment. Comprehensive design docs in `docs/` serve as source of truth and will be updated as features are implemented. Codebase mapping exists in `.planning/codebase/`.

**Target users:**
- Platform Engineers: Manage integrations, blueprints, environments, infrastructure
- Developers: Create services via wizard, deploy to environments
- Auditors: Read-only access to all projects, audit logs

**Design philosophy:** "Orchestrate, don't rebuild." DevSSP is a control plane that coordinates existing tools (GitHub, Jenkins, Kubernetes, Docker) rather than replacing them.

**Documentation approach:** `docs/` contains user-facing documentation for platform engineers. Updated as features are implemented. Eventually served as built-in Docs in the app.

## Constraints

- **Stack**: Django 6.x, SQLite (dev), PostgreSQL (prod), Docker/Podman, Gunicorn
- **No backwards compatibility**: Early development; free to break existing schemas/code for cleaner implementation
- **MVP plugins**: GitHub (SCM + CI) and Docker (deploy) only for initial release
- **Auth library**: django-guardian for object-level permissions
- **Naming convention**: DNS-compatible names for all entities (max 63 chars, lowercase alphanumeric with hyphens)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Django auth + django-guardian | Leverage built-in user/group management, add object permissions | — Pending |
| Support local + external auth | Flexibility for different org sizes; external defers access audit to AD | — Pending |
| Infra Resources on Environment | Shared infrastructure provisioned by platform team, services just bind | — Pending |
| Single plugin type per template | KISS over abstract capability matching; simpler routing | — Pending |
| SCM on Project, Deploy on Environment | SCM is project-wide (same repo for all envs), deploy varies per env | — Pending |
| GitHub provides SCM + CI | No separate CI connection when using GitHub Actions; same plugin | — Pending |
| Template versioning via git tags | Pin at creation, manual upgrade; avoids unexpected changes | — Pending |
| Baseline platform discovery | Authenticated users can browse; standard IDP pattern | — Pending |
| Update docs/ during implementation | User-facing docs evolve with code; eventually built-in | — Pending |

---
*Last updated: 2026-01-21 after initialization*
