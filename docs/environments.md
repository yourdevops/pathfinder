# Environments

Environments are deployment target configurations within a Project. They define where services are deployed and how they connect to external services (integrations).

## Environment Model

```
Environment:
  - name: string (DNS-compatible, max 20 chars, unique within project)
  - description: text (e.g., "Development environment for feature testing")
  - project: FK Project
  - env_vars: array of { key, value, lock }
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

Environment-level vars in the cascade: Project → **Environment** → Service → Deployment

- Pre-populated: `ENV` = `{env-name}` with lock=true
- Can override unlocked Project vars
- Uses the same Key | Value | Lock | [X] table UI

See [projects.md](projects.md#environment-variables) for merge behavior and lock mechanism.

---

## Example: Multi-Service Environment Setup

Consider `team-a` Project with a `dev` Environment where infrastructure (VPC, k3s cluster) is provisioned externally.

**Step 1: Platform team creates Connections:**
```yaml
IntegrationConnection: dev-k3s
  plugin_name: kubernetes
  config: { kubeconfig: "...", default_namespace: "apps" }

IntegrationConnection: jenkins-cd
  plugin_name: jenkins
  config: { url: "https://jenkins-cd.internal", credentials: "..." }

IntegrationConnection: yourdevops-github
  plugin_name: github
  config: { organization: "yourdevops", ... }
```

**Step 2: Platform team registers Service Blueprints (from git repos with devssp-template.yaml):**
```yaml
# python-k8s-service/ssp-template.yaml
name: python-k8s-service
description: Python service deployed to Kubernetes
ci:
  type: jenkins
deploy:
  type: container
  mechanism: direct
  required_plugins: [kubernetes]
tags: [python, container, k8s]

# python-lambda-vpc/ssp-template.yaml
name: python-lambda-vpc
description: Python Lambda with VPC networking via Terraform
ci:
  type: jenkins
deploy:
  type: serverless
  mechanism: pipeline
  required_plugins: [jenkins]
tags: [python, serverless, lambda, aws]
```

**Step 3: Platform team configures Environment connections:**
```yaml
Environment: dev
  project: team-a
  connections:
    - connection: dev-k3s
      is_default: true
    - connection: jenkins-cd
      is_default: true
      config_override: { job_name: "terraform-lambda-deploy" }
    - connection: yourdevops-github
      is_default: true
```

**Template availability (automatic):**
- `python-k8s-service` requires `kubernetes` → available (dev has `dev-k3s`)
- `python-lambda-vpc` requires `jenkins` → available (dev has `jenkins-cd`)

**Developer experience:**
1. Developer starts wizard, selects `team-a` project
2. Sees two template cards: `python-k8s-service` and `python-lambda-vpc`
3. Selects `python-lambda-vpc`, names service `order-processor`
4. Page 3 shows serverless-specific options (handler, runtime, timeout)
5. Page 4 shows `dev` environment, deployment via "jenkins-cd"
6. On deploy, DevSSP triggers Jenkins with: `PROJECT_NAME=team-a`, `ENV=dev`, `APP_NAME=order-processor`
7. Terraform uses data blocks to find VPC by naming convention, deploys Lambda

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
