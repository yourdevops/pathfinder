
## Deployment Patterns

SSP supports multiple deployment patterns based on the target integration:

### 1. Direct Deploy
- DevSSP orchestrates deployment directly via integration API
- Used with: Docker, Kubernetes (direct), SSH Host
- DevSSP manages container lifecycle: create, start, stop, remove
- Real-time status via integration health checks

### 2. GitOps
- DevSSP commits manifests to a git repository
- CD tool (ArgoCD, Flux) syncs and deploys
- DevSSP tracks deployment via CD tool API

### 3. Pipeline Trigger
- DevSSP triggers a CD pipeline that handles deployment
- Used with: Jenkins, GitHub Actions
- DevSSP monitors pipeline status for deployment result (via polling or webhook)
- Decouples DevSSP from direct infrastructure access

---

## Production Safeguards

When `is_production=True`:

**Required:**
- Elevated permissions to deploy (Admin/Operator or explicit grant)
- Audit log entry for all deployment actions
- Confirmation dialog before destructive actions

**Optional (configurable per environment):**
- Approval workflow: require second user to approve
- Deployment windows: only allow deployments during specified times
