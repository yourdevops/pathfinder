# Templates & Service Onboarding — Design

This document captures the design for how templates work, how services are onboarded (with or without templates), and how environment variables behave across the application.

## Core Principles

1. **Pathfinder is the source of truth.** Service name, description, required variables, and runtime information are stored in Pathfinder's database — not in a manifest file inside the service repository.

2. **`pathfinder.yaml` is a template-only manifest.** It lives in template repositories to declare metadata. It is not carried into scaffolded service repos. After scaffolding, the manifest's data has been seeded into Pathfinder and the file is excluded from the output.

3. **Environment variables have one unified model and UI** across every level of the hierarchy: Project, Service, Environment, and (future) Deployment. The same component, the same interaction patterns, the same inheritance rules.

## pathfinder.yaml

The manifest lives in the root of a template repository. Pathfinder reads it during template registration and when a version (git tag) is selected in the service creation wizard.

```yaml
kind: ServiceTemplate
name: python-fastapi
description: "FastAPI service with async PostgreSQL and Redis"
runtimes:
  - python: ">=3.11"
required_vars:
  DATABASE_URL: "PostgreSQL connection string (asyncpg format)"
  SECRET_KEY: "Application secret key for JWT signing"
  REDIS_URL: "Redis connection string for caching"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `kind` | Yes | Manifest type discriminator. Must be `ServiceTemplate` for service templates. |
| `name` | Yes | DNS-compatible identifier. The template's unique identity in Pathfinder — used as the slug, the display name, and the audit reference on scaffolded services. Immutable for the lifetime of the Template record. |
| `description` | No | Human-readable description shown in the template picker. |
| `runtimes` | No | List of runtime constraints (e.g., `python: ">=3.11"`). Used to pre-filter CI Workflow recommendations during service creation. |
| `required_vars` | No | Map of variable names to description strings. Seeded as service-level variables during onboarding. |

Pathfinder validates `kind` during registration. An unrecognized or missing `kind` is a registration error.

### name as identity

The `name` field is the template's identity — not the repo name, not the git URL. The repo is just a container; the template is what's inside it.

- **Registration** reads `name` from the manifest and creates a Template record keyed on it. If a template with that name already exists, registration fails.
- **Repo URL is mutable.** The repo can move, be renamed, change SCM providers. The operator updates the git URL on the Template record. As long as `pathfinder.yaml` still has the same `name`, it's the same template.
- **Audit trail.** A Service record stores "scaffolded from template `python-fastapi` at version `v2.1.0`" as plain text fields. That reference is meaningful and stable regardless of repo renames, URL changes, or template deregistration.

### What happens to pathfinder.yaml at scaffolding

It is **excluded** from the scaffolded service repository. The template's file tree is copied into the new repo, minus the manifest. The Service record in Pathfinder stores a reference to the template `name` and version, the `description`, and seeds `required_vars` as service-level variables. The `runtimes` field is used transiently for CI Workflow filtering and is not persisted on the Service. The service repo has no `pathfinder.yaml`.

### Runtime detection post-scaffolding

The `runtimes` field in the manifest is used only at scaffolding time for CI Workflow filtering. After scaffolding, Pathfinder can derive runtime information from repo convention files (`.python-version`, `.node-version`, `.tool-versions`, `go.mod`, etc.) if needed in the future. The manifest is not re-read.

### More examples

Node.js Express API with TypeScript:

```yaml
kind: ServiceTemplate
name: node-express-api
description: "Node.js Express REST API with TypeScript"
runtimes:
  - node: ">=20"
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
  JWT_SECRET: "Secret for JWT token signing"
  PORT: "Port the service listens on (e.g., 8080)"
```

Go HTTP service:

```yaml
kind: ServiceTemplate
name: go-http-service
description: "Minimal Go HTTP service with Chi router"
runtimes:
  - go: ">=1.22"
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
```

Minimal valid manifest (only the two required fields):

```yaml
kind: ServiceTemplate
name: static-site
```

React SPA (optional fields, no required vars):

```yaml
kind: ServiceTemplate
name: react-spa
description: "React single-page application with TypeScript and Vite"
runtimes:
  - node: ">=20"
```

Multi-runtime (Django with compiled frontend):

```yaml
kind: ServiceTemplate
name: django-with-frontend
description: "Django web app with compiled React frontend"
runtimes:
  - python: ">=3.11"
  - node: ">=20"
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
  SECRET_KEY: "Django secret key"
  ALLOWED_HOSTS: "Comma-separated list of allowed hostnames"
```

## Service Creation Wizard

The wizard flow, template selection, step-by-step field reference, and scaffolding execution are documented in [Service Creation Wizard](../wizard.md).

## Environment Variables

Variable shape, cascade rules, override logic, the deployment gate, and the unified UI component are defined in [Environment Variables](../env-vars.md).

### Non-scaffolded services

Existing repos onboarded without a template start with no service-level variables (beyond `PTF_SERVICE`). The operator configures variables through the Service settings page using the same unified component. No `pathfinder.yaml` is needed in the repo.

## What pathfinder.yaml Does NOT Do

- **Does not exist in service repos.** Pathfinder's database is the source of truth for service metadata.
- **Does not enforce variables at build time.** Variable enforcement is Pathfinder's job — it compares the resolved variable set against what's needed and gates deployment accordingly. The manifest is not re-read after scaffolding.
- **Does not contain variable values.** Only variable names and descriptions (as helper text for the operator).
- **Does not select CI Workflows.** Runtimes in the manifest inform a recommendation; the operator makes the final choice.
- **Does not define infrastructure or components.** Template scope is service scaffolding only. See Future Considerations below.

## Future Considerations

### Resource Templates

The `kind` field on `pathfinder.yaml` is designed to accommodate additional template types. A future `kind: ResourceTemplate` would cover infrastructure components — Terraform modules (e.g., RDS, S3), Helm charts (e.g., CloudnativePG-managed Postgres, Redis), or other IaC artifacts that services depend on.

Key differences from service templates:

- **No repo scaffolding.** Resource templates are applied/upgraded/destroyed, not cloned into a new repo.
- **Richer variable schema.** Input variables would need types, defaults, and validation — not just name + description.
- **Output references.** A provisioned resource produces outputs (connection strings, endpoints, ARNs) that feed into service environment variables.
- **Lifecycle management.** Resources have ongoing state: provisioned, updating, failed, destroyed. Service templates are fire-and-forget after scaffolding.

What transfers directly from the current design:

- **Registration model.** Git repo + tags + manual registration works for any template type.
- **Environment compatibility.** Deployment target matching via environment connections (`required_plugins`) applies — a Terraform RDS template requires `[aws]` or `[terraform]`, a CNPG Helm chart requires `[kubernetes]`.
- **Monorepo support.** Both service and resource templates would benefit from registering a sub-path within a repo (not yet supported — current design assumes one template per repo root).

This is not yet designed. The deployment model must solidify before resource templates become specifiable.
