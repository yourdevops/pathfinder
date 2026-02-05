# Manifest Identifier System

## Problem

Current build categorization parses workflow `name` field with "CI - " prefix stripping. This is fragile, GitHub-specific, and can't distinguish Pathfinder-managed manifests from developer-added ones.

## Solution

Use **filename prefixes** derived from entity type + **content hash verification** for security.

### Entity → Prefix Mapping

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
# ==================================================
name: ci-python-uv
on:
  push:
    branches: [main]
```

### Content Hash Verification

```python
class CIWorkflow(models.Model):
    name = models.CharField(max_length=63)  # "python-uv"
    manifest_hash = models.CharField(max_length=64, blank=True)  # SHA-256
    manifest_generated_at = models.DateTimeField(null=True)
```

Hash stored in DB, compared against actual file content to detect tampering.

---

## Manifest Control Modes

Global setting (`Settings → General`) controlling how strictly Pathfinder enforces manifest ownership.

### Permissive Mode (default)

For teams with skilled developers who may need to customize workflows.

- Categorization by **filename prefix only** (`ci-*` / `cd-*`)
- Manifest header included as documentation
- Hash stored but **not enforced** — no API calls to verify content
- Developers can freely modify generated manifests
- Tampered manifests still categorized correctly (filename unchanged)

### Strict Mode

For enterprises with compliance requirements.

- Categorization by filename prefix + **hash verification**
- On each build event, fetch manifest content from repo and compare hash
- **Drift detection**: flag builds where manifest content doesn't match stored hash
- UI indicator: "Verified" vs "Modified" vs "Unknown" per build
- Optional: block deployments from modified manifests

### Comparison

| Aspect | Permissive | Strict |
|--------|-----------|--------|
| Categorization | Filename prefix | Filename prefix + hash |
| API calls per build | 0 extra | 1 (fetch manifest content) |
| Developer freedom | Full | View-only on manifests |
| Compliance audit trail | No | Yes |
| Drift detection | No | Yes |
| Build status indicators | Standard | Standard + verification badge |

### Compute Cost (Strict)

Each build event requires one additional API call to fetch the workflow file content for hash comparison. Can be mitigated by:
- Caching manifest content with TTL (file changes infrequently)
- Verifying only on build completion, not on every status update
- Background verification (non-blocking)

---

## Model Changes

### Build Model

```python
class Build(models.Model):
    manifest_id = models.CharField(max_length=255, blank=True, db_index=True)
    # e.g., ".github/workflows/ci-python-uv.yml"

    manifest_verified = models.BooleanField(null=True)
    # None = not checked (permissive), True = hash match, False = drift detected
```

Replaces `workflow_name` field directly.

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

    def fetch_manifest_content(self, config: dict, repo_name: str, manifest_id: str) -> str | None:
        """Fetch manifest file content from repo. Used in strict mode only."""
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

### Filename Prefix Alone = No Security

Anyone can create `ci-exploit.yml`. The prefix is for **categorization**, not security.

### Content Hash = Actual Security (Strict Mode)

| Attack | Permissive | Strict |
|--------|-----------|--------|
| Create fake `ci-*.yml` | Categorized, not verified | ❌ No matching hash in DB |
| Modify Pathfinder manifest | Undetected | ❌ Hash mismatch flagged |

### Safeguards

1. **Input validation** - `CIWorkflow.name` uses `dns_label_validator` (`[a-z0-9-]`)
2. **Regex validation** - Extracted manifest IDs validated against strict pattern
3. **Hash verification** - Content compared against stored hash (strict mode)

---

## Categorization

| Build Source | manifest_id | Tab |
|--------------|-------------|-----|
| Current CIWorkflow | `.github/workflows/ci-python-uv.yml` | Current Workflow |
| Previous CIWorkflow | `.github/workflows/ci-python-docker.yml` | Other |
| Developer-added | `""` (no match) | Other |

---

## Future: CD Support

DeploymentMethod (when CI-engine-based) follows same pattern:

```
ci-{workflow.name}.yml      → CIWorkflow (Build records)
cd-{method.name}.yml        → DeploymentMethod (Deployment records)
```

Same `manifest_id` field and plugin methods, different entity types.
