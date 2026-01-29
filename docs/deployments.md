## Deployment [DRAFT]

Deployments are handled by Pathfinder plugins. Each deploy plugin registers a Connection (credentials and target) and one or more Deployment Methods. Pathfinder controls the full chain: credentials, execution, status, and audit trail.

Plugins that need Connections (Pathfinder calls them directly):
- **Docker** — direct (via Docker socket/TCP)
- **Kubernetes** — direct (via K8s API), helm (via chart), gitops (push manifests to repo)
- **ArgoCD** — direct (via ArgoCD API), gitops (push Application CR to repo)
- **OpenTofu/Terraform** — apply (Pathfinder worker runs tofu/terraform with plugin-managed credentials)

Cloud providers (AWS, GCP, Azure) do not need their own plugins. Infrastructure deployments are handled by the OpenTofu/Terraform plugin, which authenticates to the target cloud via OIDC or stored credentials configured on the plugin Connection.

### Plugin Deployment Methods

Each deploy plugin provides methods that differ by executor type:

| Executor | Who Does the Work | Example |
|----------|-------------------|---------|
| `platform` | Pathfinder worker calls target API directly | Docker direct, K8s direct, Helm, OpenTofu apply |
| `gitops` | Pathfinder pushes manifests to a repo, external controller syncs | K8s gitops, ArgoCD gitops |

The Path selects a plugin and method. The Environment binds a specific Connection (which cluster, which cloud account and role).

### CI-managed Deployments

For teams that already have their own deployment pipelines and manage credentials at the CI level, Pathfinder does not orchestrate the deployment, only observes.

This decision was made due to the complexity of securely orchestrating deployments via CI. Scoping CI credentials per service requires provisioning per-service IAM roles, which is itself an infrastructure operation that needs privileged credentials — creating a chicken-and-egg problem. Centralizing deployment logic in reusable workflows avoids this but introduces OIDC trust policy scoping issues: GitHub Environments are per-repo, while Pathfinder Environments are per-project, making it difficult to map cloud credentials to the correct project-environment boundary. Plugin-based deployments sidestep both problems — Pathfinder already holds credentials for deploy plugins, and adding IaC plugins (OpenTofu, Terraform) is no different from Docker or Kubernetes plugins.

The team's Deployment pipeline handles deployment using its own credentials (org secrets, OIDC federation, etc.). After deploying, the pipeline notifies Pathfinder via webhook using the `ssp-notify-deploy` action from the CI Steps repo:

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

Pathfinder records the deployment event but did not cause it. The team owns their pipeline end-to-end. Pathfinder provides visibility: deployment history, environment status, and promotion tracking still work.

When selecting a Deployment method for a Path, the option "CI-managed" means Pathfinder will not attempt to deploy. It will only track deployments reported via webhook. This is suitable for teams that have existing CI/CD pipelines they do not want to replace.

---

**Workflow & Promotions:**
- Trunk-based development, non-negotiable. Code on main is treated as production-ready.
- Deployed to a Project's default Environment automatically on merge to main.
- Promotions to other Environments are manual via Pathfinder UI/API and use reusable artifacts from the original build.
- A tag with release/version is pushed on the original commit that produced the artifact.
- If an Artifact is not reusable and has to be rebuilt from scratch, the commit gets rebuilt for the target environment.


## Artifact-to-Deployment Matching

When a Build completes successfully, Pathfinder stores the artifact reference (type, registry ref, digest) on the Service's Build record. When a user triggers a deployment to an Environment, Pathfinder matches the artifact type against the Environment's Deploy Plugin capabilities:

| Artifact Type | Compatible Deploy Plugins |
|---------------|--------------------------|
| `container-image` | Direct Docker, Kubernetes (future) |
| `zip` | Lambda (future), S3 (future) |
| `raw` | SCP/SFTP (future) |

If the artifact type is incompatible with the target Environment's Deploy Plugin, the deployment is blocked with an explanation.
