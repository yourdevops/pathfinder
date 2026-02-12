# Promotion

Promotion is the process of deploying an artifact that was already deployed to one environment into another environment. Pathfinder follows trunk-based development: code on main is treated as production-ready. The first deployment is always automatic to the project's default environment. Subsequent deployments to other environments are manual promotions.

## Auto-Deploy to Default Environment

When a build completes with status `success` and appropriate verification_status, Pathfinder automatically creates a deployment to the project's default environment (see [environments.md](../environments.md) for default environment rules). The auto-deploy creates a Deployment record with `triggered_by="auto"`.

**Build verification gate:**

| verification_status | Auto-Deploy Behavior |
|---------------------|---------------------|
| `verified` | Always auto-deploys to default environment |
| `draft` | Auto-deploys only if project has "Allow Drafts" enabled AND default environment is non-production |
| `revoked` | Blocked from auto-deploy |
| `unauthorized` | Blocked from auto-deploy |

- Edge case: If the default environment has no compatible deploy connection for the build's artifact type, auto-deploy is skipped with a warning. The build remains available for manual promotion once a connection is configured.
- Edge case: If a deployment is already active for the same (service, default-environment), the auto-deploy enters `pending` and waits. See [Deployment Lifecycle](deployment-lifecycle.md) for concurrent deployment rules.

## Manual Promotion

Anyone with the appropriate project role can promote a build to an environment. No separate approval workflow exists.

**Role-based authorization:**

| Target Environment | Required Role |
|--------------------|---------------|
| Non-production | Contributor, Owner, or Admin |
| Production | Owner or Admin only |

Promotion reuses the artifact from the source build. The artifact is NOT rebuilt. Pathfinder resolves the env var cascade for the target environment, creates a new Deployment record with a fresh `env_vars_snapshot`, and delegates execution to the target environment's deploy plugin.

## Rollback

Rollback is a manual promotion of a previous known-good build to the same environment. There is no special "rollback" action or button.

- The user views deployment history, identifies the last successful build, and promotes it.
- This creates a fresh Deployment record (the failed deployment is not modified).
- The previous artifact is redeployed with a new `env_vars_snapshot` reflecting current environment configuration.
- No git-revert model. Rollback is artifact-focused: re-deploy what was working.

This approach optimizes for mean time to recovery (MTTR). Re-deploying a known-good artifact is faster and more predictable than reverting code and waiting for a new build.

## Environment Ordering

Environments have an `order` field (e.g., dev=10, staging=20, prod=30). The UI presents environments in order, suggesting the natural promotion path.

**Ordering is recommended, not enforced.** A user with the required role can skip staging and promote directly to production. This aligns with the recommendation-only approach used by GitOps platforms (ArgoCD, Flux) rather than the sequential enforcement of tools like Spinnaker.

**Exception:** The first deployment of a service MUST go to the default environment via auto-deploy on build success. After that, any environment in any order.

- Edge case: If a user attempts to promote to an environment before the service has ever been deployed to the default environment, the promotion is blocked with an explanation.
- Edge case: Environment ordering is per-project. Different projects can have different promotion paths based on their environment configuration.

## Promotion Workflow Summary

1. Build succeeds -- auto-deploy to default environment (automatic)
2. User views deployment history, selects a successful build
3. User selects target environment from the promotion UI
4. Pathfinder checks role authorization (contributor for non-prod, owner/admin for prod)
5. Pathfinder creates new Deployment record with env var snapshot for target environment
6. Deploy plugin executes in target environment
7. Deployment status tracked in real-time (see [Deployment Lifecycle](deployment-lifecycle.md) for status state machine)

## Artifact Reuse

Promotion reuses the `artifact_ref` from the source build. The artifact is NOT rebuilt. This guarantees that what was tested in one environment is exactly what gets deployed to the next.

- If the artifact type is incompatible with the target environment's deploy connection, the promotion is blocked with an explanation (see [Deployment Methods](deployment-methods.md) for artifact matching).
- A tag with the release/version is pushed on the original commit that produced the artifact.
- The same container image hash deployed to dev is the same hash deployed to production. Only configuration (env vars) differs between environments.

See [Deployment Lifecycle](deployment-lifecycle.md) for the Deployment record model and trigger details. See [Deployment Methods](deployment-methods.md) for artifact-to-deployment matching.
