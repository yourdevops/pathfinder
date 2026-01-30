# Services

Services are deployable application configurations within a Project. They represent the full lifecycle from source code to running deployment.

## Overview

SSP follows the **orchestrate, don't rebuild** principle. Services are built and deployed by external CI/CD systems, with Pathfinder acting as the control plane that tracks state and coordinates actions.

**Key Concepts:**
- **Service**: Configuration defining what to build and deploy
- **Build**: Record of a CI build run, produces an artifact
- **Deployment**: Instance of an Service deployed to an Environment
- **Artifact**: Immutable build output (e.g., container image) reusable across environments

---

## Service Model

```
Service:
  - name: string (DNS-compatible, max 40 chars, unique within project)
  - description: text
  - project: FK Project
  - service_handler: computed as {project-name}-{app-name}
  - template: FK Blueprint
  - repository: FK Repository (nullable, set after scaffolding)

  # Current Artifact (updated after each successful build)
  - current_artifact_ref: string (e.g., ghcr.io/org/app:abc123)
  - current_build: FK Build (nullable)

  # Service-level Environment Variables (defaults for all deployments)
  - env_vars: array of { key, value, lock }

  # Status
  - status: enum (draft, active)
  - created_by: string (username, denormalized)
  - created_at, updated_at: datetime
```

### Service Status

| Status | Description |
|--------|-------------|
| `draft` | Service created, no successful builds yet |
| `active` | At least one successful build exists |

**Status Transitions:**
- `draft` → `active`: First successful build completes

Note: Service activation/deactivation is planned for a future release (see [roadmap](roadmap.md)).

---

## Build Model

Each CI build is tracked as an Build record.

```
Build:
  - app: FK Service
  - build_number: int (auto-increment per app)
  - commit_sha: string (git commit, used as version)
  - commit_message: string (first line of commit message)

  # CI Reference
  - ci_connection: FK IntegrationConnection (which CI ran this)
  - ci_job_url: string (link to CI job/run)

  # Result
  - artifact_ref: string (e.g., ghcr.io/org/app:abc123)
  - status: enum (pending, running, success, failed)
  - error_message: text (if failed)

  # Audit
  - created_by: string (username or "ci-webhook", denormalized)

  # Timestamps
  - started_at: datetime
  - completed_at: datetime (nullable)
  - created_at: datetime
```

### Build Status

| Status | Description |
|--------|-------------|
| `pending` | Build webhook received, waiting for start |
| `running` | Build in progress |
| `success` | Build completed, artifact available |
| `failed` | Build failed, see error_message |

---

## Deployment Model

Each deployment of an Service to an Environment is tracked.

```
Deployment:
  - app: FK Service
  - build: FK Build
  - environment: FK Environment

  # Deploy Reference
  - deploy_connection: FK IntegrationConnection
  - deploy_job_url: string (if pipeline mechanism)

  # Deployment-specific Environment Variables
  - env_vars: array of { key, value }

  # Result
  - artifact_ref: string (snapshot of deployed artifact)
  - status: enum (pending, running, success, failed, rolled_back)
  - error_message: text (if failed)

  # Audit
  - created_by: string (username, denormalized)

  # Timestamps
  - started_at: datetime
  - completed_at: datetime (nullable)
  - created_at: datetime
```

### Deployment Status

| Status | Description |
|--------|-------------|
| `pending` | Deployment triggered, waiting to start |
| `running` | Deployment in progress |
| `success` | Deployment completed successfully |
| `failed` | Deployment failed, see error_message |
| `rolled_back` | Deployment was rolled back |

### Deployment History

Multiple Deployments can exist for the same (app, environment) pair. The most recent successful deployment represents the current state. History is preserved for audit and rollback purposes.

### Environment Variables

Services and Deployments extend the environment variable cascade defined in [projects.md](projects.md#environment-variables).

**Cascade Order:** Project → Environment → Service → Deployment

- Service-level vars are defaults for all deployments of that app
- Deployment-level vars are specific to one (app, environment) pair
- Locked vars (🔒) from upstream levels are read-only
- Unlocked vars can be overridden or removed

See [projects.md](projects.md#environment-variables) for lock behavior and merge rules.

### Pre-populated Defaults

- Service: `APP_NAME` = `{app-name}` with lock=true

**Note:** Only configuration values are supported. Secrets must come from external sources (Vault, K8s Secrets).

---

## Service Lifecycle

### Prerequisites

Before services can be created in a Project:
1. **At least one Environment** must exist with connections configured
2. **CI auto-discovery** must be configured (e.g., Jenkins Multibranch Pipeline scanning the SCM org)
3. **Artifact registry** accessible by CI (configured in template)

### Creation Flow

```
1. Developer selects Project and Template
   └─ Pathfinder validates: Project has default Environment
   └─ Pathfinder shows template-specific configuration options

2. Pathfinder creates repository via SCM connection
   └─ Clones template, substitutes variables
   └─ Pushes scaffolding (includes Jenkinsfile/.github/workflows)
   └─ Creates Service record with status: draft

3. CI auto-discovers new repository
   └─ Jenkins Multibranch Pipeline scans org
   └─ Creates job for new repo with Jenkinsfile
   └─ (GitHub Actions: workflow file auto-discovered)

4. First build triggers on push
   └─ CI calls Pathfinder webhook: build started
   └─ CI builds, pushes artifact to registry
   └─ CI calls Pathfinder webhook: build complete + artifact_ref
   └─ Service status transitions: draft → active
```

### Build Flow

```
1. Developer pushes code to repository

2. SCM triggers CI (via webhook or polling)

3. CI starts build
   └─ Calls Pathfinder webhook: POST /api/webhooks/builds/{service_handler}/started
   └─ Pathfinder creates Build record, status: running

4. CI completes build
   └─ Pushes artifact to registry (e.g., ghcr.io/org/app:abc123)
   └─ Calls Pathfinder webhook: POST /api/webhooks/builds/{service_handler}/complete
   └─ Pathfinder updates Build: status: success, artifact_ref set
   └─ Pathfinder updates Service: current_artifact_ref, current_build
```

### Deployment Flow

```
1. User clicks "Deploy to [Environment]" in Pathfinder UI
   └─ Selects build (defaults to current/latest)
   └─ Confirms deployment

2. Pathfinder creates Deployment record
   └─ status: pending
   └─ artifact_ref: from selected build

3. Pathfinder triggers deployment via Environment's connection
   └─ Direct: calls deploy plugin API (Kubernetes, Docker)
   └─ Pipeline: triggers CD job (Jenkins, GitHub Actions)

4. Deployment completes
   └─ CD calls Pathfinder webhook: POST /api/webhooks/deploys/{service_handler}/{env}/complete
   └─ Pathfinder updates Deployment: status: success/failed
```

---

## Artifact Promotion

MVP scope: Artifacts are immutable and reusable across environments. The same container image can be deployed to dev, staging, and production without rebuilding.

```
Build #42 (commit abc123)
  └─ artifact_ref: ghcr.io/org/my-app:abc123
      ├─ Deployed to dev ✓
      ├─ Deployed to staging ✓
      └─ Deployed to prod ✓
```

**Benefits:**
- What you test is what you deploy
- No environment-specific build differences
- Faster promotions (no rebuild time)

**Environment Differences:**
- Configuration via environment variables (Project → Environment → Service)
- Secrets injected at deploy time
- Resource limits per environment

---

## Webhook API

SSP exposes webhook endpoints for CI/CD systems to report build and deployment status.

### Build Webhooks

**Build Started:**
```
POST /api/webhooks/builds/{service_handler}/started
Content-Type: application/json
Authorization: Bearer {webhook_token}

{
  "commit_sha": "abc123def456",
  "commit_message": "Fix login validation bug",
  "ci_job_url": "https://jenkins.internal/job/my-app/42"
}
```

**Build Complete:**
```
POST /api/webhooks/builds/{service_handler}/complete
Content-Type: application/json
Authorization: Bearer {webhook_token}

{
  "commit_sha": "abc123def456",
  "status": "success",
  "artifact_ref": "ghcr.io/org/my-app:abc123def456",
  "ci_job_url": "https://jenkins.internal/job/my-app/42"
}
```

**Build Failed:**
```
POST /api/webhooks/builds/{service_handler}/complete
Content-Type: application/json
Authorization: Bearer {webhook_token}

{
  "commit_sha": "abc123def456",
  "status": "failed",
  "error_message": "Unit tests failed: 3 failures",
  "ci_job_url": "https://jenkins.internal/job/my-app/42"
}
```

### Deploy Webhooks

**Deploy Complete:**
```
POST /api/webhooks/deploys/{service_handler}/{env_name}/complete
Content-Type: application/json
Authorization: Bearer {webhook_token}

{
  "status": "success",
  "deploy_job_url": "https://jenkins.internal/job/deploy-my-app/15"
}
```

**Deploy Failed:**
```
POST /api/webhooks/deploys/{service_handler}/{env_name}/complete
Content-Type: application/json
Authorization: Bearer {webhook_token}

{
  "status": "failed",
  "error_message": "Health check failed after deployment",
  "deploy_job_url": "https://jenkins.internal/job/deploy-my-app/15"
}
```

### Webhook Security

Webhooks are authenticated using one of:
- **Bearer token**: Shared secret configured per IntegrationConnection (CI type)
- **Signature verification**: HMAC signature in request header (for GitHub-style webhooks)

Token is configured when creating the IntegrationConnection and stored securely.

---

## Template Integration

Service Blueprints define how CI/CD is configured. The template's Jenkinsfile or GitHub Actions workflow must include Pathfinder webhook calls.

### Example: Jenkinsfile

```groovy
pipeline {
  environment {
    PTF_WEBHOOK = "https://ssp.example.com/api/webhooks/builds/{{ service_handler }}"
    PTF_TOKEN = credentials('ssp-webhook-token')
    IMAGE_TAG = "ghcr.io/{{ project_name }}/{{ app_name }}:${GIT_COMMIT}"
  }

  stages {
    stage('Notify Start') {
      steps {
        sh '''
          curl -X POST ${PTF_WEBHOOK}/started \
            -H "Authorization: Bearer ${PTF_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{"commit_sha": "'${GIT_COMMIT}'", "commit_message": "'${GIT_COMMIT_MSG}'", "ci_job_url": "'${BUILD_URL}'"}'
        '''
      }
    }

    stage('Build') {
      steps {
        sh 'docker build -t ${IMAGE_TAG} .'
      }
    }

    stage('Push') {
      steps {
        sh 'docker push ${IMAGE_TAG}'
      }
    }

    stage('Notify Complete') {
      steps {
        sh '''
          curl -X POST ${PTF_WEBHOOK}/complete \
            -H "Authorization: Bearer ${PTF_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{"commit_sha": "'${GIT_COMMIT}'", "status": "success", "artifact_ref": "'${IMAGE_TAG}'", "ci_job_url": "'${BUILD_URL}'"}'
        '''
      }
    }
  }

  post {
    failure {
      sh '''
        curl -X POST ${PTF_WEBHOOK}/complete \
          -H "Authorization: Bearer ${PTF_TOKEN}" \
          -H "Content-Type: application/json" \
          -d '{"commit_sha": "'${GIT_COMMIT}'", "status": "failed", "error_message": "Build failed", "ci_job_url": "'${BUILD_URL}'"}'
      '''
    }
  }
}
```

### Example: GitHub Actions

```yaml
name: Build and Push

on:
  push:
    branches: [main]

env:
  PTF_WEBHOOK: https://ssp.example.com/api/webhooks/builds/{{ service_handler }}
  IMAGE_TAG: ghcr.io/{{ project_name }}/{{ app_name }}:${{ github.sha }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Notify Pathfinder - Build Started
        run: |
          curl -X POST $PTF_WEBHOOK/started \
            -H "Authorization: Bearer ${{ secrets.PTF_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"commit_sha": "${{ github.sha }}", "commit_message": "${{ github.event.head_commit.message }}", "ci_job_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"}'

      - name: Build and Push
        run: |
          docker build -t $IMAGE_TAG .
          docker push $IMAGE_TAG

      - name: Notify Pathfinder - Build Complete
        if: success()
        run: |
          curl -X POST $PTF_WEBHOOK/complete \
            -H "Authorization: Bearer ${{ secrets.PTF_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"commit_sha": "${{ github.sha }}", "status": "success", "artifact_ref": "'$IMAGE_TAG'", "ci_job_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"}'

      - name: Notify Pathfinder - Build Failed
        if: failure()
        run: |
          curl -X POST $PTF_WEBHOOK/complete \
            -H "Authorization: Bearer ${{ secrets.PTF_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"commit_sha": "${{ github.sha }}", "status": "failed", "error_message": "Build failed", "ci_job_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"}'
```

---

## Services UI

### Service List (within Project)

Services are displayed in the Project detail page under the Services tab.

```
┌─────────────────────────────────────────────────────────────────────┐
│ ← Projects    team-a                              [Settings]        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌─────────┬──────────────┬─────────┬──────────┐                    │
│ │  Services   │ Environments │ Members │ Settings │                    │
│ └─────────┴──────────────┴─────────┴──────────┘                    │
│                                                                     │
│ Services (4)                                            [+ New Service]     │
│ ┌──────────────────────┐  ┌──────────────────────┐                 │
│ │ order-service        │  │ payment-gateway      │                 │
│ │ Build #42 · abc123   │  │ Build #18 · def456   │                 │
│ │ ● dev ● staging      │  │ ● dev                │                 │
│ │ python-k8s-service   │  │ python-k8s-service   │                 │
│ └──────────────────────┘  └──────────────────────┘                 │
│                                                                     │
│ ┌──────────────────────┐  ┌──────────────────────┐                 │
│ │ notification-svc     │  │ frontend             │                 │
│ │ Build #5 · 789abc    │  │ No builds yet        │                 │
│ │ ● dev                │  │ ○ draft              │                 │
│ │ python-lambda-vpc    │  │ node-static-s3       │                 │
│ └──────────────────────┘  └──────────────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Service Card:**
- Service name
- Latest build number and commit SHA
- Deployment status per environment (dots)
- Template name
- Click → Service detail page

### Service Detail Page

```
┌────────────────────────────────────────────────────────────────────┐
│ ← team-a    order-service                               [Settings] │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ Order processing microservice                                      │
│ Template: python-k8s-service · ● Active                            │
│                                                                    │
│ ┌───────────┬────────────┬─────────────┐                           │
│ │<Overview> │   Builds   │ Deployments │                           │
│ └───────────┴────────────┴─────────────┘                           │
│                                                                    │
│ Last Build                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ ghcr.io/team-a/order-service:abc123def456                       ││
│ │ Build #42 · 2 hours ago · abc123 "Fix validation bug"           ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                    │
│ Deployments                                          [Deploy ▼]    │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ dev        ● Running    Build #42    2 hours ago    [Details]   ││
│ │ staging    ● Running    Build #41    1 day ago      [Details]   ││
│ │ prod       ○ Not deployed                           [Deploy]    ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                    │
│ Repository                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ github.com/yourdevops/order-service                      [Open] ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Builds Tab

```
┌────────────────────────────────────────────────────────────────────┐
│ ← team-a    order-service                               [Settings] │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ ┌───────────┬────────────┬─────────────┐                           │
│ │ Overview  │  <Builds>  │ Deployments │                           │
│ └───────────┴────────────┴─────────────┘                           │
│                                                                    │
│ Build History                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ #42  ● Success   abc123   Fix validation bug       2h ago       ││
│ │      ghcr.io/team-a/order-service:abc123           [Open CI]    ││
│ │─────────────────────────────────────────────────────────────────││
│ │ #41  ● Success   def456   Add rate limiting        1d ago       ││
│ │      ghcr.io/team-a/order-service:def456           [Open CI]    ││
│ │─────────────────────────────────────────────────────────────────││
│ │ #40  ✗ Failed    789abc   Refactor auth module     2d ago       ││
│ │      Unit tests failed: 3 failures                 [Open CI]    ││
│ │─────────────────────────────────────────────────────────────────││
│ │ #39  ● Success   111222   Initial commit           5d ago       ││
│ │      ghcr.io/team-a/order-service:111222           [Open CI]    ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Deployments Tab

```
┌────────────────────────────────────────────────────────────────────┐
│ ← team-a    order-service                               [Settings] │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ ┌───────────┬────────────┬───────────────┐                         │
│ │ Overview  │   Builds   │ <Deployments> │                         │
│ └───────────┴────────────┴───────────────┘                         │
│                                                                    │
│ Environment: [dev ▼]                                               │
│                                                                    │
│ Deployment History                                                 │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ ● Success   Build #42   abc123   Deployed by jdoe    2h ago     ││
│ │             via dev-k3s (kubernetes)                [Open]      ││
│ │─────────────────────────────────────────────────────────────────││
│ │ ● Success   Build #41   def456   Deployed by jdoe    1d ago     ││
│ │             via dev-k3s (kubernetes)                [Open]      ││
│ │─────────────────────────────────────────────────────────────────││
│ │ ✗ Failed    Build #40   789abc   Deployed by admin   2d ago     ││
│ │             Health check timeout                    [Open]      ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Deploy Modal

```
┌────────────────────────────────────────────────────────────────────┐
│ Deploy order-service                                        [X]    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ Environment *                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ staging                                                     ▼   ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                    │
│ Build *                                                            │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ #42 - abc123 - Fix validation bug (latest)                  ▼   ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                    │
│ Artifact                                                           │
│ ghcr.io/team-a/order-service:abc123def456                          │
│                                                                    │
│ Environment Variables                                              │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ Key            │ Value        │ Source      │                   ││
│ │────────────────│──────────────│─────────────│───────────────────││
│ │ PROJECT_NAME   │ team-a       │ Project  🔒 │                   ││
│ │ ENV            │ staging      │ Env      🔒 │                   ││
│ │ APP_NAME       │ order-svc    │ Service      🔒 │                   ││
│ │ LOG_LEVEL      │ debug        │ Service         │ [Reset] [X]       ││
│ │ API_TIMEOUT    │ 30           │ Service         │ [Reset] [X]       ││
│ │ CACHE_TTL      │ 3600         │ Deploy      │ [X]               ││
│ │ [+ Add Variable]                                                ││
│ └─────────────────────────────────────────────────────────────────┘│
│ 🔒 = locked (read-only)   [Reset] = restore inherited value        │
│                                                                    │
│ ⚠ This will replace the current deployment (Build #41)             │
│                                                                    │
│                                        [Cancel]  [Deploy]          │
└────────────────────────────────────────────────────────────────────┘
```

**Environment Variables in Deploy Modal:**
- Locked vars (🔒) are read-only at all levels
- Unlocked vars from Project/Environment/Service are pre-populated but editable
- [Reset] restores the inherited value from the level above
- [X] removes the override (falls back to inherited value, or removes if deployment-only)
- Deployment-specific vars (Source: Deploy) only exist at this level
- Previous deployment's overrides are pre-filled when redeploying

---

## Access Control

| Action | admin | owner | contributor | viewer |
|--------|-------|-------|-------------|--------|
| View services | ✓ | ✓ | ✓ | ✓ |
| Create services | ✓ | ✓ | ✓ | - |
| Edit service settings | ✓ | ✓ | ✓ | - |
| Delete services | ✓ | ✓ | - | - |
| View builds | ✓ | ✓ | ✓ | ✓ |
| View deployments | ✓ | ✓ | ✓ | ✓ |
| Deploy to non-prod | ✓ | ✓ | ✓ | - |
| Deploy to production | ✓ | ✓ | - | - |

**Notes:**
- `admin` SystemRole has full access to all services across all projects
- Contributors can create and modify services, deploy to non-production
- Only owners, operators and admins can deploy to production environments
- Viewers have read-only access
- Service activation/deactivation is a future feature (see roadmap)

See [rbac.md](rbac.md) for full permission model documentation.


# Security Concerns

- When onboarding a new service from an existing repo, user is allowed to list all available repos in the org and select one for scaffolding. Pathfinder will open a PR in that repo, which is harmless (can be reviewed and declined) but still can be merged by mistake. This is this a security risk, so for existing repos, we should make user authenticate to SCM with his credentials to make these actions within his permissions and under his name.
