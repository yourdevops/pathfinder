# Environment Binding

When a deployment is triggered, Pathfinder resolves the target environment's deploy connection and builds a configuration snapshot. This document covers how connections are selected and how environment variables cascade into the deploy-time snapshot.

## Connection Selection

Pathfinder determines which deploy connection to use based on the target environment and the artifact type:

1. The environment has connections grouped by plugin type (see [Environments](../environments.md)).
2. Each plugin type has one default connection within the environment.
3. The deploy method's plugin type determines which connection is used.
4. If multiple connections of the same plugin type exist, the one marked `is_default` is selected.
5. If no compatible connection exists for the artifact type, the deployment is blocked with an explanation.

Admins and operators can override the connection for a specific deployment. The override is stored and reused for future deployments of the same (service, environment) pair.

See [Integrations](../integrations.md) for the full connection model and default selection rules.

## Environment Variable Cascade

Deployment env vars follow the cascade defined in [Environments](../environments.md) and [Services](../services.md):

**Cascade order:** Project -> Environment -> Service -> (deployment snapshot)

Per locked decision: env vars are **snapshot at deploy time**. The full merged result is frozen when the deployment is created and stored on the Deployment record as `env_vars_snapshot`. Changing variables after deployment creation has no effect on running or completed deployments -- changes require a new deployment.

**Snapshot rules:**

- The snapshot is the FULL merged result of the cascade at the moment of deployment creation.
- Locked vars from upstream levels (Project, Environment) are included as-is and cannot be overridden at deploy time.
- The snapshot is immutable -- it represents exactly what was deployed.

**Edge cases:**

- If a project-level locked var changes between deployments, the new deployment gets the new value. Old deployments retain their snapshot. The diff is visible in deployment history.
- If an environment var is deleted between deployments, new deployments will not have it. Old deployments retain their snapshot.
- If two deployments to the same environment occur seconds apart, each gets its own snapshot reflecting the cascade state at its creation time.

## Secrets

Pathfinder stores configuration values, not secrets.

- Secrets must come from external sources (Vault, K8s Secrets, cloud secret managers).
- Deploy plugins may resolve secret references at execution time (e.g., Docker plugin reads from Vault, K8s plugin creates ExternalSecret CR).
- The `env_vars_snapshot` contains configuration values only. Secret references (e.g., `vault:secret/data/myapp#DB_PASSWORD`) may appear as values but are resolved by the deploy plugin, not by Pathfinder.
- Designing a secrets management system is out of scope for MVP.

## Resources

Environment resources (databases, caches, queues) are a future concern.

- Current model: resources are provisioned externally, their connection details registered as environment variables.
- No resource provisioning or binding system in MVP.
- See [Environments](../environments.md) for how external resource outputs are captured as env vars.
