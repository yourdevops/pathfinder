# Deployment Methods

Pathfinder supports multiple deployment methods through the plugin system. Each deploy plugin registers a Connection and one or more Deployment Methods. Methods differ by executor type and depth of Pathfinder control.

## Executor Types

| Executor | Who Does the Work | Pathfinder Role | Example |
|----------|-------------------|-----------------|---------|
| `platform` | Pathfinder worker calls target API | Full control: credentials, execution, status | Docker direct, K8s direct, Helm |
| `gitops` | External controller syncs from repo | Partial control: generates manifests, pushes to repo | K8s gitops, ArgoCD |

The Environment's deploy Connection determines which executor is used. The Connection binds a specific target (which cluster, which Docker host, which git repo for gitops).

## Method Types

### Direct (Platform-Executed)

Pathfinder calls target APIs directly using Connection credentials. The worker manages the full lifecycle: generate configuration, execute deployment, monitor status, report result.

**Docker (MVP):**
- Generate container run configuration from artifact reference and environment variables
- Deploy via Docker socket (local) or TCP (remote) using Connection credentials
- Start/stop/restart controls available in UI
- Health check via container health status or HTTP probe

**Kubernetes (Future):**
- Generate manifests (Deployment, Service, ConfigMap) from artifact reference and environment variables
- Apply via K8s API using kubeconfig from Connection
- Namespace-scoped deployments
- Health check via rollout status

Direct methods give Pathfinder full visibility: real-time status updates, log streaming, and the ability to stop or rollback without external coordination.

### GitOps (Future)

Pathfinder generates manifests and pushes them to a git repository. An external controller (ArgoCD, Flux) reconciles the desired state with the cluster.

- Pathfinder writes to a structured gitops repo (`/{project}/{env}/{service}/`)
- The controller detects the change and syncs
- Status tracked via controller API or webhook callbacks
- Pathfinder needs SCM write access only, not cluster credentials

GitOps splits responsibility: Pathfinder owns the desired state, the controller owns reconciliation. This model suits teams that require git as the source of truth for cluster state.

### CI-Managed (Webhook Observer)

For teams with existing deployment pipelines, Pathfinder does not orchestrate -- it observes. The team's pipeline handles deployment using its own credentials. After deploying, the pipeline notifies Pathfinder via webhook:

```yaml
# In the team's CI pipeline, after their deploy step:
- uses: org/ci-steps/ssp-notify-deploy@main
  with:
    ssp_url: ${{ vars.PTF_URL }}
    ssp_token: ${{ secrets.PTF_WEBHOOK_TOKEN }}
    project: ${{ env.PTF_PROJECT }}
    service: ${{ env.PTF_SERVICE }}
    environment: prod
    artifact_tag: v1.2.3
    status: success
    commit: ${{ github.sha }}
```

Pathfinder records the deployment event but did not cause it. Deployment history, environment status, and promotion tracking still work.

**Why CI-managed exists:** Scoping CI credentials per service requires provisioning per-service IAM roles, which is itself an infrastructure operation needing privileged credentials. Centralizing deployment logic in reusable workflows introduces OIDC trust policy scoping issues. Plugin-based deployments sidestep both problems since Pathfinder already holds credentials for deploy plugins. CI-managed coexists for teams that prefer their existing pipelines.

## Artifact-to-Deployment Matching

When a Build completes successfully, Pathfinder stores the artifact reference (type, registry ref, digest) on the Build record. When a deployment is triggered, Pathfinder matches the artifact type against the Environment's deploy plugin capabilities:

| Artifact Type | Compatible Deploy Plugins | Status |
|---------------|--------------------------|--------|
| `container-image` | Docker direct, Kubernetes | Docker: MVP, K8s: Future |
| `zip` | Lambda, S3 | Future |
| `raw` | SCP/SFTP | Future |

If the artifact type is incompatible with the target Environment's deploy plugin, the deployment is blocked with an explanation.

## MVP Scope

Docker direct is the MVP deployment method (per DPLY-05). The plugin interface and executor model are designed to support all method types, but Phase 7 implementation focuses on:

- Docker `platform` executor with socket/TCP connections
- Container image artifacts from CI builds
- Health checks via container health status

Other methods (Kubernetes, GitOps, CI-managed observation) are documented here at design-contract depth to show how the model extends. Their implementation is deferred to future phases.

See [Plugin Interface](plugin-interface.md) for the deploy plugin contract and method registration.
