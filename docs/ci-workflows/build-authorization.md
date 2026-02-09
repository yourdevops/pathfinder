# Build Authorization

Pathfinder is the authority on what constitutes a valid build pipeline. An artifact is deployable only if it was produced by a build manifest that Pathfinder authorized. Everything else is blocked at deployment time.

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
# Workflow: python-uv
# Version: 1.2.3
# ==================================================
name: ci-python-uv
on:
  push:
    branches: [main]
```

The version string is embedded in the header. It is part of the file content and therefore part of the hash. Each version produces a unique hash.

### Deterministic Generation

Manifest generation must be **deterministic**: the same workflow definition + version number always produces identical bytes. No timestamps, no non-deterministic ordering, no trailing whitespace variance. This is required for hash verification to work reliably.

## Authorization Chain

```
Pathfinder generates manifest → manifest pushed to repo → CI runs manifest →
artifact produced → Pathfinder verifies manifest hash → artifact authorized for deployment
```

Breaking any link in this chain makes the artifact non-deployable.

## Verification Flow

On every build completion (CI-engine-native webhook triggers the flow):

1. Pathfinder calls the CI engine API to fetch authoritative build data (status, commit SHA, metadata). Webhook payloads are treated as notification signals only.
2. Pathfinder resolves the Service's assigned CIWorkflow and its `manifest_id`.
3. Pathfinder calls the CI plugin's `fetch_manifest_content(repo, manifest_id, commit_sha)` to fetch the exact manifest file present when the build ran.
4. Pathfinder computes the SHA-256 hash of the fetched content.
5. Pathfinder looks up the hash in `CIWorkflowVersion` for that workflow:
   - Match found + `status=authorized` → **Verified**
   - Match found + `status=revoked` → **Unauthorized** (version was revoked before this build completed)
   - Match found + `status=draft` → **Draft** (pipeline testing, not production-deployable)
   - No match → **Unauthorized**
6. Artifact references (image ref, digest) are fetched from the CI engine API or registry—not trusted from webhook payloads.
7. The result is stored on the Build record and never recomputed.

## Verification States

| State | Meaning | Non-Production | Production |
|-------|---------|----------------|------------|
| **Verified** | Manifest hash matches an authorized version | Deploy | Deploy |
| **Draft** | Manifest hash matches a draft version | Deploy | Blocked |
| **Unauthorized** | Hash doesn't match any authorized version, or matched a revoked version | Blocked | Blocked |

External builds (not from a Pathfinder-managed manifest) are categorized as "Other" and are always **Unauthorized**. They are never valid sources of artifacts for deployments.

### Pre-Revocation vs Post-Revocation Builds

This is a critical distinction:

- **Pre-revocation builds**: Builds that completed and were marked **Verified** *before* a version was revoked retain their Verified status. The UI overlays a warning by checking the linked version's current status: "Built with revoked workflow version 1.2.3". Deployments are allowed with the warning.

- **Post-revocation builds**: Builds that complete *after* a version is revoked are marked **Unauthorized** at verification time. They cannot be deployed.

## Security Model

### Filename Prefix = Categorization Only

Anyone can create `ci-exploit.yml`. The prefix identifies Pathfinder-managed files for categorization. It provides no security guarantee.

### Content Hash = Authorization

The hash is the security boundary. It answers: "Is this exact file one that Pathfinder produced?"

| Attack | Result |
|--------|--------|
| Create fake `ci-*.yml` | **Unauthorized** — no matching hash in any CIWorkflowVersion |
| Modify Pathfinder manifest (even a comment) | **Unauthorized** — hash mismatch |
| Replay an old revoked manifest | **Unauthorized** — version is revoked |
| Run a draft manifest | **Draft** — blocked from production environments |
| Forge build status or artifact ref via webhook | **Mitigated** — Pathfinder fetches authoritative data from CI engine API; webhook is a trigger only |
| Compromise steps repo default branch | **Mitigated** — branch protection enforced at registration; existing manifests pin step SHAs |

### Safeguards

1. **Input validation** — `CIWorkflow.name` uses `dns_label_validator` (`[a-z0-9-]`)
2. **Regex validation** — Extracted manifest IDs validated against strict pattern per CI engine
3. **Hash verification** — Content fetched out-of-band from repo and compared against stored authorized hashes. The pipeline cannot falsify its own verification.
4. **Immutability** — Once a version is published, its hash cannot be changed in Pathfinder
5. **API-based verification** — Build status and artifact references are fetched from the CI engine API, not trusted from webhook payloads. Webhooks serve only as notification triggers.
6. **Steps repo branch protection** — Pathfinder validates branch protection rules (required reviews, no force push, no branch deletion) when a Steps Repository is registered. Unprotected repos are rejected.

## Build Categorization

| Build Source | manifest_id | Verification | Tab |
|--------------|-------------|--------------|-----|
| Current CIWorkflow (authorized) | `.github/workflows/ci-python-uv.yml` | Verified | Current Workflow |
| Current CIWorkflow (draft) | `.github/workflows/ci-python-uv.yml` | Draft | Current Workflow |
| Previous CIWorkflow version | `.github/workflows/ci-python-uv.yml` | Verified / Revoked | Current Workflow |
| Previous CIWorkflow (different workflow) | `.github/workflows/ci-python-docker.yml` | Verified / Revoked | Other |
| Developer-added workflow | `""` (no match) | Unauthorized | Other |
