# Build Lifecycle

## Triggering a Build

A build is triggered by a configured event (usually a push to the main branch) in a Service's repository. The CI engine executes the workflow. Pathfinder is notified of build state changes via CI-engine-native webhooks (e.g., GitHub `workflow_run` events) or plugins (Jenkins). No Pathfinder-specific steps are injected into the pipeline since they may get tampered with.

## Build State and Artifact Discovery

CI engine webhooks are treated as **notification signals only**. On receiving a build state webhook, Pathfinder calls the CI engine API to fetch authoritative data:

- **Build status**: Actual success/failure from the CI engine API, not from the webhook payload.
- **Build metadata**: Commit SHA, author, timing, job details.
- **Artifact reference**: Image ref, digest, or other artifact identifiers. Discovery is CI-engine-specific (e.g., GitHub Packages API, registry query). The CI plugin is responsible for resolving the artifact reference.

The artifact type and reference are used downstream to match against Environment's deploy plugin capabilities. The artifact block is present only on success and only when the workflow includes a packaging step.

## Build Model

```python
class Build(models.Model):
    manifest_id = models.CharField(max_length=255, blank=True, db_index=True)
    # e.g., ".github/workflows/ci-python-uv.yml"

    manifest_hash = models.CharField(max_length=64, blank=True)
    # SHA-256 of manifest fetched at build's commit_sha

    workflow_version = models.ForeignKey(
        "CIWorkflowVersion", on_delete=models.SET_NULL, null=True, blank=True
    )
    # Linked version if hash matched; null if unauthorized or external

    class VerificationStatus(models.TextChoices):
        VERIFIED = "verified"
        REVOKED = "revoked"          # matched a revoked version at completion time
        DRAFT = "draft"              # matched a draft version
        UNAUTHORIZED = "unauthorized"

    verification_status = models.CharField(
        max_length=16, choices=VerificationStatus.choices, blank=True
    )
    # Computed at build completion, stored permanently
```

### Build Record Fields

Each Service maintains a list of Builds. A Build record contains:

- Build ID (from CI engine)
- Commit SHA
- Manifest ID (CI-engine-specific path to the workflow file)
- Manifest hash (SHA-256 of the manifest file at the build's commit SHA)
- Linked CI Workflow version (if hash matched a known version; null otherwise)
- Verification status: `verified`, `revoked`, `draft`, or `unauthorized`
- Status (running, success, failure, cancelled)
- Artifact reference (type, ref, digest) — if exists
- Timestamp

Only builds with `verified` verification status (or `verified` with revoked version warning) produce deployable artifacts. Builds marked `unauthorized` or `draft` (for production environments) are blocked from deployment.

## Compute Cost

Each build completion requires API calls to the CI engine (build status, manifest content) and potentially the artifact registry. Mitigations:

- Verify only on build completion, not on every status update
- Background verification (non-blocking)
- Caching manifest content with TTL for repos with high build volume
