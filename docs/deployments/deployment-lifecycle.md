# Deployment Lifecycle

A deployment is triggered by a successful build (auto-deploy to the project's default environment) or by a user action (manual promotion to another environment). Pathfinder creates a Deployment record, resolves the target environment's deploy connection, snapshots configuration, and delegates execution to the deploy plugin.

## Triggering a Deployment

Two trigger paths exist:

**1. Auto-deploy (build success):** When a build completes with status `success` and verification_status `verified` (or `draft` for non-production with "Allow Drafts" enabled), Pathfinder automatically creates a deployment to the project's default environment. No human in the loop. Merge to main, build succeeds, deploy starts immediately.

- Edge case: If the default environment has no compatible deploy connection for the artifact type, auto-deploy is skipped with a warning logged to the deployment audit trail.
- Edge case: If a deployment to the same (service, default-environment) is already running, the new deployment enters `pending` and waits for the current deployment to reach a terminal state.
- Edge case: Builds with `unauthorized` verification_status never trigger auto-deploy. Builds with `draft` verification_status auto-deploy only when the project has "Allow Drafts" enabled AND the default environment is non-production.

**2. Manual deploy (promotion):** A user triggers deployment from the UI, selecting a target environment and a build. See [Promotion](promotion.md) for the full promotion workflow, role-based authorization, and rollback strategy.

## Deployment Status State Machine

```
PENDING (deployment created, queued)
  |
  |-- start --> RUNNING (plugin executing deployment)
  |                |
  |                |-- health_check --> HEALTH_CHECK (waiting for health verification)
  |                |                      |
  |                |                      |-- pass --> SUCCESS (deployment complete)
  |                |                      |
  |                |                      +-- fail --> FAILED (health check failed)
  |                |
  |                +-- error --> FAILED (execution error)
  |
  +-- cancel --> CANCELLED (before execution started)
```

Real-time status progression is displayed in the UI (pending, running, health check, success/failed), following the same live-tracking pattern used for builds. The `health_check` state provides meaningful feedback: the container is running but Pathfinder is verifying that it is healthy and serving traffic.

## Deployment Record Model

```python
class Deployment:
    service = FK(Service)
    build = FK(Build)
    environment = FK(Environment)
    deploy_connection = FK(EnvironmentConnection)

    class Status(TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        HEALTH_CHECK = "health_check"
        SUCCESS = "success"
        FAILED = "failed"
        CANCELLED = "cancelled"

    status = CharField(choices=Status.choices)
    artifact_ref = CharField()        # snapshot from build
    env_vars_snapshot = JSONField()    # frozen at deploy time
    error_message = TextField()

    triggered_by = CharField()        # "auto" or username
    created_at = DateTimeField()
    started_at = DateTimeField()
    completed_at = DateTimeField()
```

**`env_vars_snapshot`:** The full merged environment variable cascade (Project → Service → Environment) is resolved and frozen at deployment creation time. The snapshot is stored on the Deployment record for auditability and reproducibility. Subsequent changes to upstream variables do not affect running or completed deployments. Changing variables requires a new deployment. See [Environment Variables](../env-vars.md) for cascade rules.

**`artifact_ref`:** Copied from the Build record at deployment creation. The same artifact is reused for promotions across environments without rebuilding.

## Concurrent Deployment Rules

Services are independent -- concurrent deploys to different services in the same environment proceed without interference.

- Only one non-terminal deployment (`pending`, `running`, `health_check`) per (service, environment) pair at any time.
- Concurrent deployments to different services in the same environment are allowed.
- If a deployment is pending or running and a new deployment is requested for the same (service, environment), the request is rejected until the current deployment reaches a terminal state (`success`, `failed`, `cancelled`).

## Failure Handling

On failure, the deployment status transitions to `FAILED` and `error_message` is populated with details from the deploy plugin. The user is notified via the UI.

- No automatic retry or rollback. The user decides whether to rollback (re-deploy a previous known-good build), fix-forward (push a new commit, wait for build, deploy), or investigate.
- Rollback is a manual promotion of a previous successful build to the same environment. See [Promotion](promotion.md) for details.
- Failed deployments remain in history for audit purposes. They are never auto-deleted or hidden.

See [Deployment Methods](deployment-methods.md) for method-specific failure modes. See [Environment Binding](environment-binding.md) for env var cascade details.
