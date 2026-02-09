# Integrations

Integrations connect Pathfinder to external services like source control, CI systems, artifact registries, and deployment targets.

## Architecture Overview

SSP uses a two-level integration model:

```
IntegrationPlugin (Code)              IntegrationConnection (Database)
────────────────────────              ─────────────────────────────────
GitHub                          →     yourdevops (org: yourdevops)
                                →     company-oss (org: company-oss)

Jenkins                         →     jenkins-subprod (url: jenkins-subprod.internal)
                                →     jenkins-prod (url: jenkins-prod.internal)

Kubernetes                      →     prod-eks (cluster: prod-eks)
                                →     dev-k3s (cluster: team-a-dev)
```

- **Plugin**: Python class defining the integration type, capabilities, and configuration schema. Built into Pathfinder.
- **Connection**: Database record representing a configured instance. Created by admin or operator.

---

## Plugin

Plugins are defined in code and provide the logic for interacting with external services.

### Categories

**SCM** (category: `scm`)
- Plugins: GitHub, BitBucket, GitLab, Gitea
- Capabilities: `list_repos`, `clone`, `create_repo`, `create_branch`, `commit`, `push`, `create_pr`, `webhooks`

**CI** (category: `ci`)
- Plugins: Jenkins, GitHub Actions, GitLab CI
- Capabilities: `trigger_build`, `get_build_status`, `cancel_build`, `get_logs`, `list_workflows`

**Artifact** (category: `artifact`)
- Plugins: ECR, Docker Hub, Nexus, GitHub Packages, S3
- Capabilities: `push_image`, `pull_image`, `list_tags`, `delete_tag`

**Deploy** (category: `deploy`)
- Plugins: ArgoCD GitOps, Docker, Kubernetes, SSH Host
- Capabilities: `deploy`, `get_status`, `rollback`, `get_logs`, `list_resources`

### Multi-Capability Plugins

Some plugins provide multiple capabilities across categories:

| Plugin | Primary | Additional Capabilities |
|--------|---------|------------------------|
| GitHub | scm | ci (Actions), artifact (Packages) |
| GitLab | scm | ci (GitLab CI), artifact (Registry) |
| Jenkins | ci | (none) |
| Kubernetes | deploy | (none) |

When a plugin has multiple capabilities:
- It appears in its primary category in the UI
- Badge shows additional capabilities: "Also provides: CI, Artifacts"
- Connection can be used wherever any of its capabilities are needed

### CI Engine / SCM Compatibility

When a plugin provides both SCM and CI capabilities (GitHub, GitLab), the CI engine is only available for repositories on that SCM connection. CI-only plugins (e.g., Jenkins) are compatible with any SCM connection.

| CI Engine | Compatible SCM |
|-----------|---------------|
| GitHub Actions | GitHub only |
| GitLab CI | GitLab only |
| Bitbucket Pipelines | Bitbucket only |
| Jenkins | Any SCM |

This constraint is enforced when connecting a Steps Repository and when creating a CI Workflow. See [Steps Catalog](ci-workflows/steps-catalog.md) and [Workflow Definition](ci-workflows/workflow-definition.md).

### Plugin Registry

Plugins are discovered at startup by scanning the `integrations/plugins/` package. Any module in that folder can register one or more plugins and (optionally) expose URL patterns under:

`/integrations/<plugin_name>/<connection_name>/...`

## Plugin UI Assets

If a plugin needs custom UI (templates or static files), ship it as a package folder under `integrations/plugins/<plugin_name>/`:

## Connection

Connections are configured instances of plugins, stored in the database.

### Connection Model

```
IntegrationConnection:
  - name: string (unique, DNS-compatible, max 63 chars)
  - description: text
  - plugin_name: string (references IntegrationPlugin.name)
  - config: JSON (non-sensitive configuration fields)
  - config_encrypted: JSON (sensitive fields encrypted with Fernet)
  - enabled_capabilities: array of strings (subset of plugin capabilities)
  - status: enum
      - active: Active and available for use
      - disabled: Configured but not available
      - error: Configuration or connection issue
  - is_production: bool (enables extra safeguards)
  - health_status: enum (healthy, unhealthy, unknown)
  - last_health_check: datetime
  - last_error: text
  - webhook_token: string (auto-generated, for CI webhook authentication)
  - created_by: string (username, denormalized)
  - created_at, updated_at: datetime
```

### Sensitive Field Encryption

Sensitive configuration fields (passwords, tokens, private keys) are encrypted at rest using Fernet symmetric encryption.

**How it works:**
1. Plugin defines sensitive fields via `_get_sensitive_fields()` method
2. On save, `set_config()` separates sensitive from non-sensitive fields
3. Sensitive values are encrypted and stored in `config_encrypted` as base64 strings
4. On read, `get_config()` decrypts and merges all fields transparently

**Default sensitive field patterns:**
- `password`, `token`, `secret`, `private_key`, `api_key`
- `tls_client_key`, `client_secret`, `access_key`, `secret_key`

**Encryption key location:**
- Environment variable: `PTF_ENCRYPTION_KEY`
- Or file: `$BASE_DIR/secrets/encryption.key` (auto-generated if missing)

**Important:** Back up the encryption key. If lost, all encrypted credentials must be re-entered.

## Environment Connections

Environments can have multiple connections, enabling different service types in the same environment.

Connections are bound to Environments with an optional `is_default` flag per plugin type. When deploying an app, Pathfinder uses the environment's connections to determine available deployment targets.

**Default Connection Rules:**
- One connection per plugin type can be marked `is_default` in an Environment
- If no connection of a plugin type is marked `is_default`, the first one added becomes default
- When adding a connection to an Environment, UI shows checkbox: "Make default for [plugin-type]"

See [environments.md](environments.md) for the full Environment model, connection binding rules, and multi-service setup examples.

---

## Blueprints Compatibility

Blueprints declare which plugin types they require for deployment in their `ssp-template.yaml` manifest.

### Template Requirements

```yaml
# In pathfinder-template.yaml
deploy:
  required_plugins:
    - kubernetes
```

See [blueprints.md](blueprints.md) for full manifest documentation.

### Availability Logic

An Service Template is available in a Project if at least one Environment in the Project has a Connection with matching plugin type.

```
Template: python-k8s-service
  deploy.required_plugins: [kubernetes]

Project: team-a
  Environment: dev
    connections: [dev-k3s (kubernetes), jenkins-cd (jenkins)]
  Environment: prod
    connections: [prod-eks (kubernetes)]

Result: python-k8s-service is available in team-a (both envs have kubernetes)
```

### Deployment Connection Selection

When deploying an service to an environment:

1. Get app's template → `required_plugin_types`
2. Find connections in target environment matching those plugin types
3. If exactly one match: use it
4. If multiple matches of same type: use the one marked `is_default`
5. If no connection marked `is_default`: use the first connection of that type (by created_at)
6. Admin/operator can override per Deployment
7. Override is stored and used for future deployments

---

### Access Control

| SystemRole | Connections Page | Plugins Page | Connect/Edit |
|------------|-----------------|--------------|--------------|
| `admin` | Full access | Full access | Yes |
| `operator` | Full access | Full access | Yes |
| `auditor` | View only (with config) | View only | No |
| `user` | View list (no config) | View list | No |

**Notes:**
- All authenticated users can see plugin types and connection names/health (baseline access)
- `operator` SystemRole grants full management access
- `auditor` SystemRole grants read access to configuration details
- Connection cards are clickable only for those with management or audit permissions

See [rbac.md](rbac.md) for full permission model documentation.
