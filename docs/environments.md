# Environments

Status: Stale, need update

Environments are deployment target configurations within a Project. They define where services are deployed and how they connect to external services (integrations).

## Environment Model

```
Environment:
  - name: string (DNS-compatible, max 20 chars, unique within project)
  - description: text (e.g., "Development environment for feature testing")
  - project: FK Project
  - env_vars: array of { key, value, lock, description }
  - is_production: bool
  - is_default: bool (one per project, used for service creation)
  - status: enum (active, inactive)
  - order: int (display ordering: dev=10, staging=20, prod=30)
  - created_at, updated_at: datetime
```

### Default Environment

Each Project must have exactly one default Environment (`is_default=true`).

**Rules:**
- First Environment created in a Project automatically becomes default
- If the default Environment is deleted, the remaining Environment with lowest `order` becomes default
- Project owner can change the default via Environment settings
- **Service creation requires at least one Environment** - the default Environment determines template availability

**Why it matters:**
- Blueprints are filtered by plugin availability in the default Environment
- Provides a consistent "landing zone" for new services
- Ensures services can be built and deployed immediately after creation

---

## Environment Features

### Connections

Environments can have multiple connections, enabling different service types in the same environment.

```
Environment.connections: array of {
  connection: FK IntegrationConnection,
  is_default: bool (one default per plugin type)
}
```

**Connection Rules:**
- Multiple connections allowed, enabling different service types in same environment
- One connection per plugin type can be marked `is_default`
- If no connection of a plugin type is marked `is_default`, the first one added becomes default
- When adding a connection, UI shows checkbox: "Make default for [plugin-type]"
- Cannot remove a connection if any deployed service in that environment uses it

See [integrations.md](integrations.md) for full IntegrationConnection model.

### Environment Variables

Environment sits below Service in the variable cascade, and can override unlocked Project and Service variables. See [Environment Variables](env-vars.md) for variable shape, cascade rules, and override logic.

`PTF_ENVIRONMENT` is system-injected (locked) with the environment name as its value.

---

## Example: Environment Setup

Consider `team-a` Project with a `dev` Environment.

**Step 1: Platform team creates Connections:**
```yaml
IntegrationConnection: dev-k3s
  plugin_name: kubernetes
  config: { kubeconfig: "...", default_namespace: "apps" }

IntegrationConnection: yourdevops-github
  plugin_name: github
  config: { organization: "yourdevops", ... }
```

**Step 2: Platform team configures Environment connections:**
```yaml
Environment: dev
  project: team-a
  connections:
    - connection: dev-k3s
      is_default: true
    - connection: yourdevops-github
      is_default: true
```

**Step 3: Developer creates a service from a template:**
1. Developer starts wizard, selects `team-a` project
2. Picks a registered service template (e.g., `python-fastapi`)
3. Names the service, reviews seeded variables
4. Pathfinder scaffolds the repo via the GitHub connection

Templates are code scaffolding only — they do not declare CI or deployment requirements. Deployment target matching (which environments a service can deploy to) is a separate concern to be designed with the deployment model.

---

## Environment Lifecycle

**States:**
- **active**: Available for deployments
- **inactive**: Preserve deployment history but no new deployments are allowed

**Deletion:**
- Cannot delete environment with active Deployments, must remove them first

---

## Access Control

| Action | admin | owner | contributor | viewer |
|--------|-------|-------|-------------|--------|
| View environments | ✓ | ✓ | ✓ | ✓ |
| Create environments | ✓ | - | - | - |
| Delete environments | ✓ | - | - | - |
| Edit environment settings | ✓ | ✓ | - | - |
| Manage connections | ✓ | ✓ | - | - |
| Deploy to non-prod | ✓ | ✓ | ✓ | - |
| Deploy to production | ✓ | ✓ | - | - |

**Notes:**
- `admin` and `operator` SystemRoles grant full access to all environments across all projects
- Only `admin` and `operator` can create or delete environments
- Project owners can edit environment settings and manage connections
- Contributors can deploy to non-production environments only

See [rbac.md](rbac.md) for full permission model documentation.
