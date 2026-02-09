# Manifest Identifier & Build Authorization

## Problem

Current build categorization parses workflow `name` field with "CI - " prefix stripping. This is fragile, GitHub-specific, and can't distinguish Pathfinder-managed manifests from developer-added ones. There is no mechanism to verify that a build was produced by an authorized workflow, leaving the deployment path open to artifacts from tampered or unauthorized pipelines.

## Goals

1. Reliably identify Pathfinder-managed manifests across CI engines.
2. Ensure only artifacts produced by authorized workflows are deployable.
3. Maintain an auditable version history of every workflow manifest.

---

## Manifest Identification

### Entity Prefix Mapping

| Entity | Prefix | Example Filename |
|--------|--------|------------------|
| CIWorkflow | `ci-` | `ci-python-uv.yml` |
| DeploymentMethod | `cd-` | `cd-helm.yml` |

Entity names stay clean (`python-uv`), system derives prefixed filename (`ci-python-uv.yml`).

### Manifest Header

```yaml
# ==================================================
# Managed by Pathfinder - DO NOT EDIT MANUALLY
# Manual changes will be overwritten on next sync.
# Workflow: python-uv
# Workflow ID: 550e8400-e29b-41d4-a716-446655440000
# Version: 1.2.3
# ==================================================
name: ci-python-uv
on:
  push:
    branches: [main]
```

The version string is embedded in the header. It is part of the file content and therefore part of the hash. Each version produces a unique hash.

### Manifest Generation

Manifest generation must be **deterministic**: the same workflow definition + version number always produces identical bytes. No timestamps, no non-deterministic ordering, no trailing whitespace variance. This is required for hash verification to work reliably.

---

## Build Authorization Model

Pathfinder is the authority on what constitutes a valid build pipeline. An artifact is deployable only if it was produced by a manifest that Pathfinder authorized. Everything else is blocked at deployment time.

### Authorization Chain

```
Pathfinder generates manifest → manifest pushed to repo → CI runs manifest →
artifact produced → Pathfinder verifies manifest hash → artifact authorized for deployment
```

Breaking any link in this chain makes the artifact non-deployable.

### Build Verification States

| State | Meaning | Deploy to non-production? | Deploy to production? |
|-------|---------|---------------------------|----------------------|
| **Verified** | Manifest hash matches a non-revoked authorized version | Yes | Yes |
| **Verified (revoked)** | Hash matches a version that was later revoked | Yes, with warning | Yes, with warning |
| **Unauthorized** | Hash doesn't match any authorized/revoked version | No | No |
| **Draft** | Hash matches a draft version (mutable) | Yes | No |

External builds (not from a Pathfinder-managed manifest) are categorized as "Other" and are always **unauthorized**. They are never valid sources of artifacts for deployments.

### Verification Flow

On every build completion (CI-engine-native webhook triggers the flow):

1. Pathfinder calls the CI engine API to fetch authoritative build data (status, commit SHA, metadata). Webhook payloads are treated as notification signals only.
2. Pathfinder resolves the Service's assigned CIWorkflow and its `manifest_id`.
3. Pathfinder calls the CI plugin's `fetch_manifest_content(repo, manifest_id, commit_sha)` to fetch the exact manifest file present when the build ran.
4. Pathfinder computes the SHA-256 hash of the fetched content.
5. Pathfinder looks up the hash in `CIWorkflowVersion` for that workflow:
   - Match found + `status=authorized` -> **Verified**
   - Match found + `status=revoked` -> **Unauthorized** (version was revoked before this build completed)
   - Match found + `status=draft` -> **Draft** (pipeline testing, not production-deployable)
   - No match -> **Unauthorized**
6. Artifact references (image ref, digest) are fetched from the CI engine API or registry — not trusted from webhook payloads.
7. The result is stored on the Build record and never recomputed.

For builds that were already recorded as **Verified** before a version is revoked: the verification status remains **Verified**, but the UI overlays a warning by checking the linked version's current status ("Built with revoked workflow version 1.2.3").

### Compute Cost

Each build completion requires API calls to the CI engine (build status, manifest content) and potentially the artifact registry. Mitigations:

- Verify only on build completion, not on every status update
- Background verification (non-blocking)
- Caching manifest content with TTL for repos with high build volume

---

## Workflow Version Lifecycle

### CIWorkflowVersion Model

```python
class CIWorkflowVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        AUTHORIZED = "authorized"
        REVOKED = "revoked"

    workflow = models.ForeignKey(CIWorkflow, on_delete=models.PROTECT, related_name="versions")
    version = models.CharField(max_length=32, blank=True)  # semver, blank while draft
    status = models.CharField(max_length=16, choices=Status.choices)
    manifest_hash = models.CharField(max_length=64)  # SHA-256
    manifest_content = models.TextField()  # full manifest text
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
```

**Constraints**:
- At most one row with `status=draft` per workflow.
- `version` is unique within a workflow (enforced on publish).
- `manifest_hash` is immutable once `status=authorized`.

### State Machine

```
DRAFT (mutable hash, no version number)
  |
  |-- publish --> AUTHORIZED (immutable hash, version assigned)
  |                   |
  |                   |-- revoke --> REVOKED (hash retained, content cleared)
  |                   |                  |
  |                   |                  +-- cleanup --> DELETED (record removed)
  |                   |
  |                   +-- cleanup --> DELETED (record removed)
  |
  +-- discard --> (record removed, no version was claimed)
```

### Draft Lifecycle

1. Author creates a draft (claims the single draft slot for this workflow).
2. Author edits the workflow definition. Manifest regenerates, hash updates. Hash and content are **mutable** while in draft.
3. Another author with sufficient permissions can **take over** the draft.
4. Author clicks **Publish**:
   - Author chooses a version number at this point. Pathfinder suggests next patch version for convenience.
   - Pathfinder validates: version is valid semver, doesn't already exist, is greater than the current latest authorized version.
   - Status transitions to `authorized`, hash becomes immutable, `published_at` is set.
5. Or author **discards**: record deleted, no version was ever claimed.

Draft builds (builds that run against a draft manifest) are recorded but marked as **Draft**. They are deployable to non-production environments but **blocked from production environments**.

### Publishing

On publish, the author selects a version number. The version must be strictly greater than the current latest version. Out-of-order or backport versions are not supported; the version history is linear.

The version number determines auto-update behavior for Services. Pathfinder compares the new version against each Service's current version using semver to decide whether the update falls within the Service's auto-update policy (e.g., auto-update patches only).

### Revocation

An admin can revoke a specific workflow version:

- **New builds**: Any build that completes after revocation and matches the revoked version's hash is marked **Unauthorized**.
- **Existing builds**: Builds recorded as **Verified** before revocation retain their status. The UI shows a warning: "Built with revoked workflow version X.Y.Z." Deployments from these builds are allowed with the warning.
- **Manifest content**: Cleared on revocation to free storage. The hash is retained for verification.

### Cleanup and Retention

**Manifest content cleanup**:
- Cleared immediately on revocation.
- For authorized versions: subject to per-workflow "cleanup unused versions older than X days" setting. Content is cleared, hash is retained.

**Version record deletion** (full removal):
- Allowed when ALL conditions are met:
  1. No Build record references this version.
  2. It is not the latest version of the workflow.
  3. It is older than "cleanup unused versions older than X days"
- The **latest version** of a workflow is never auto-deleted. Manual deletion only.

**Workflow deletion**:
- Blocked while any Build record references any version of the workflow.

**Build retention**:
- Global setting with per-project overrides.
- Default intent: 1 year (configurable).

---

## Model Changes

### Build Model

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

Replaces `workflow_name` field.

---

## Plugin Interface

```python
class CICapableMixin:
    def manifest_id(self, workflow: CIWorkflow) -> str:
        """Return manifest identifier (e.g., .github/workflows/ci-python-uv.yml)"""

    def extract_manifest_id(self, run_data: dict) -> str | None:
        """Extract identifier from CI run data. Returns None if not Pathfinder-managed."""

    def get_manifest_id_pattern(self) -> re.Pattern:
        """Regex pattern for validation."""

    def fetch_manifest_content(
        self, config: dict, repo_name: str, manifest_id: str, commit_sha: str
    ) -> str | None:
        """Fetch manifest file content from repo at a specific commit.
        Returns None if file not found at that commit."""
```

### GitHub Implementation

```python
MANIFEST_ID_PATTERN = re.compile(r'^\.github/workflows/ci-[a-z0-9][a-z0-9-]*\.yml$')

def manifest_id(self, workflow: CIWorkflow) -> str:
    return f".github/workflows/ci-{workflow.name}.yml"
```

### Jenkins Implementation

```python
MANIFEST_ID_PATTERN = re.compile(r'^ci-[a-z0-9][a-z0-9-]*\.jenkinsfile$')

def manifest_id(self, workflow: CIWorkflow) -> str:
    return f"ci-{workflow.name}.jenkinsfile"
```

---

## Security

### Filename Prefix = Categorization Only

Anyone can create `ci-exploit.yml`. The prefix identifies Pathfinder-managed files for categorization. It provides no security guarantee.

### Content Hash = Authorization

The hash is the security boundary. It answers: "Is this exact file one that Pathfinder produced?"

| Attack | Result |
|--------|--------|
| Create fake `ci-*.yml` | **Unauthorized** -- no matching hash in any CIWorkflowVersion |
| Modify Pathfinder manifest (even a comment) | **Unauthorized** -- hash mismatch |
| Replay an old revoked manifest | **Unauthorized** -- version is revoked |
| Run a draft manifest | **Draft** -- blocked from production environments |
| Forge build status or artifact ref via webhook | **Mitigated** -- Pathfinder fetches authoritative data from CI engine API; webhook is a trigger only |
| Compromise steps repo default branch | **Mitigated** -- branch protection enforced at registration; existing manifests pin step SHAs |

### Safeguards

1. **Input validation** -- `CIWorkflow.name` uses `dns_label_validator` (`[a-z0-9-]`)
2. **Regex validation** -- Extracted manifest IDs validated against strict pattern per CI engine
3. **Hash verification** -- Content fetched out-of-band from repo and compared against stored authorized hashes. The pipeline cannot falsify its own verification.
4. **Immutability** -- Once a version is published, its hash cannot be changed in Pathfinder
5. **API-based verification** -- Build status and artifact references are fetched from the CI engine API, not trusted from webhook payloads. Webhooks serve only as notification triggers.
6. **Steps repo branch protection** -- Pathfinder validates branch protection rules (required reviews, no force push, no branch deletion) when a Steps Repository is registered. Unprotected repos are rejected.

---

## Build Categorization

| Build Source | manifest_id | Verification | Tab |
|--------------|-------------|-------------|-----|
| Current CIWorkflow (authorized) | `.github/workflows/ci-python-uv.yml` | Verified | Current Workflow |
| Current CIWorkflow (draft) | `.github/workflows/ci-python-uv.yml` | Draft | Current Workflow |
| Previous CIWorkflow version | `.github/workflows/ci-python-uv.yml` | Verified / Revoked | Current Workflow |
| Previous CIWorkflow (different workflow) | `.github/workflows/ci-python-docker.yml` | Verified / Revoked | Other |
| Developer-added workflow | `""` (no match) | Unauthorized | Other |

---

## Step Update Notifications

When a CI Step in the registry updates to a new version, Pathfinder does **not** auto-patch workflow versions. Instead:

- Affected workflows display a badge/notification: "Step X updated to version Y."
- The admin manually creates a draft, updates the step reference, tests, and publishes a new version.

This keeps version creation always human-initiated.

---

## Future: CD Support

DeploymentMethod (when CI-engine-based) follows the same pattern:

```
ci-{workflow.name}.yml      -> CIWorkflow (Build records)
cd-{method.name}.yml        -> DeploymentMethod (Deployment records)
```

Same `manifest_id` field, plugin methods, and authorization model. Different entity types.
