# Deployments

A Deployment is a tracked operation that places a built artifact into a target environment. Pathfinder controls the full chain: credentials, execution, status, and audit trail. Deployments are triggered automatically on build success (to the project's default environment) or manually via promotion.

## What Deployments Do Not Do

- Manage CI secrets or build pipelines (that is a [CI Workflow](../ci-workflows/README.md) concern)
- Provision infrastructure (databases, networks, queues)
- Manage DNS or load balancer configuration
- Provide a container runtime or compute plane
- Replace existing CD systems (CI-managed deployments coexist)
- Auto-rollback on failure (user decides next action)
- Manage service secrets (secrets come from external sources)

## Documentation

| Document | Description |
|----------|-------------|
| [Deployment Methods](deployment-methods.md) | Method types, executor model, artifact matching |
| [Deployment Lifecycle](deployment-lifecycle.md) | Trigger, execution, health check, completion |
| [Promotion](promotion.md) | Auto-deploy, manual promotion, rollback, ordering |
| [Plugin Interface](plugin-interface.md) | Deploy plugin contract, method registration |
| [Environment Binding](environment-binding.md) | Connection selection, env var cascade, snapshots |
| [Logging](logging.md) | Audited entities, deployment operation logs |

---

## Quick Reference

### Deployment Status States

| State | Meaning | Trigger |
|-------|---------|---------|
| **Pending** | Created, waiting for executor | Auto or manual |
| **Running** | Plugin executing deployment | Executor started |
| **Health Check** | Waiting for health verification | Execution complete |
| **Success** | Deployment healthy and serving | Health check passed |
| **Failed** | Execution or health check failed | Error occurred |

### Deployment Authorization

| Role | Non-Production | Production |
|------|----------------|------------|
| Contributor | Deploy | Blocked |
| Owner | Deploy | Deploy |
| Admin | Deploy | Deploy |
