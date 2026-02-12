# Plugin Interface

Deploy plugins implement the `DeployCapableMixin` to register deployment methods with Pathfinder. This is analogous to `CICapableMixin` for CI engines (see [CI Plugin Interface](../ci-workflows/plugin-interface.md)). Each deploy plugin declares what methods it supports and provides the execution logic for deployments and health checks.

## DeployCapableMixin

```python
class DeployCapableMixin:
    def deploy_methods(self) -> list[DeployMethod]:
        """Return supported deployment methods."""

    def execute_deploy(
        self, config: dict, method: str, artifact_ref: str,
        env_vars: dict, deploy_config: dict
    ) -> DeployResult:
        """Execute a deployment. Returns result with status and metadata."""

    def check_health(self, config: dict, deploy_ref: str) -> HealthResult:
        """Check deployment health. Returns pass/fail with details."""

    def get_deploy_status(self, config: dict, deploy_ref: str) -> str:
        """Poll current deployment status."""
```

## DeployMethod Registration

Each plugin declares what methods it supports via `deploy_methods()`. Pathfinder uses this to match artifact types to compatible deploy connections.

```python
class DeployMethod:
    name: str           # e.g., "docker-direct"
    executor: str       # "platform" or "gitops"
    artifact_types: list[str]  # e.g., ["container-image"]
    config_schema: dict # JSON schema for deploy_config
```

See [Deployment Methods](deployment-methods.md) for executor types and artifact matching.

## Docker Plugin Implementation (MVP)

The Docker plugin implements `DeployCapableMixin` for direct container deployment via Docker socket or TCP.

```python
class DockerPlugin(BasePlugin, DeployCapableMixin):
    def deploy_methods(self):
        return [DeployMethod(
            name="docker-direct",
            executor="platform",
            artifact_types=["container-image"],
            config_schema={"port_mappings": ..., "restart_policy": ...}
        )]

    def execute_deploy(self, config, method, artifact_ref, env_vars, deploy_config):
        # 1. Pull image from registry using artifact_ref
        # 2. Stop existing container for this (service, environment) if running
        # 3. Create new container with env_vars and deploy_config (ports, volumes)
        # 4. Start container
        # 5. Return DeployResult with container ID as deploy_ref

    def check_health(self, config, deploy_ref):
        # 1. Inspect container status (running, exited, etc.)
        # 2. If container defines HEALTHCHECK: read health status
        # 3. If no HEALTHCHECK: probe configured HTTP endpoint
        # 4. Return HealthResult(passed=bool, details=str)
```

## Future Plugin Examples

**Kubernetes (platform executor):** Generates Deployment/Service/ConfigMap manifests from artifact_ref and env_vars. Applies via K8s API using kubeconfig from connection. Health check via rollout status polling.

**GitOps (gitops executor):** Generates manifests and pushes to a structured gitops repo. Status tracked via controller API (ArgoCD) or webhook callback. Health check delegates to the controller's sync status.

**CI-Managed:** Not a deploy plugin -- CI-managed deployments are webhook observations. See [Deployment Methods](deployment-methods.md) for details.
