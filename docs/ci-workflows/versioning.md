# Versioning

A CI Workflow is versioned using semver. Version numbers are chosen by the author at publish time. Each published version produces an immutable manifest with a content hash used for build authorization (see [Build Authorization](build-authorization.md)).

## Auto-Update Behavior

Services that use a CI Workflow can auto-update to new patch versions. Upgrading to a Minor/Major version is a manual procedure. Pathfinder compares the newly published version against each Service's current version using semver to determine whether the update falls within the Service's auto-update policy.

On upgrade, Pathfinder pushes the updated pipeline manifest to the Service repo. According to the configured option in the Service Settings, Pathfinder either opens a PR against the main branch or pushes directly. If an open PR with the same scope/author exists (autoupdate CI manifest), Pathfinder reuses it as a Digest PR for all CI manifest changes.

Pathfinder's commit can be optionally marked with a skip-CI comment so it does not trigger CI execution.

## CIWorkflowVersion Model

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

## Version State Machine

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

## Draft Lifecycle

1. Author creates a draft (claims the single draft slot for this workflow).
2. Author edits the workflow definition. Manifest regenerates, hash updates. Hash and content are **mutable** while in draft.
3. Another author with sufficient permissions can **take over** the draft.
4. Author clicks **Publish**:
   - Author chooses a version number. Pathfinder suggests next patch version for convenience.
   - Pathfinder validates: version is valid semver, doesn't already exist, is greater than the current latest authorized version.
   - Status transitions to `authorized`, hash becomes immutable, `published_at` is set.
5. Or author **discards**: record deleted, no version was ever claimed.

**Draft builds**: Builds that run against a draft manifest are recorded but marked as **Draft** verification status. They are deployable to non-production environments but **blocked from production environments**. This allows pipeline testing without compromising the production deployment gate.

To use a Draft workflow on a Service, a Project admin must enable "Allow Drafts" in the Project's Approved Workflows settings and explicitly set the draft workflow in the Service Settings.

## Publishing

On publish, the author selects a version number. The version must be strictly greater than the current latest version. Out-of-order or backport versions are not supported; the version history is linear.

The version number determines auto-update behavior for Services. Pathfinder compares the new version against each Service's current version using semver to decide whether the update falls within the Service's auto-update policy (e.g., auto-update patches only).

## Change Classification

- **Runtime changes require forking.** Adding or removing a runtime (by adding/removing steps that introduce or drop a runtime) triggers a fork prompt. This keeps workflow names meaningful (e.g., `python-uv` CI Workflow stays Python-only) and preserves version lineage for existing services.
- CI Engine change is not possible. Pathfinder by itself cannot guarantee the Steps compatibility between CI Engines.
- Step additions/removals within the same runtime set, step version updates, and config changes are normal version bumps (Minor or Patch as appropriate).

A user can fork an existing CI Workflow with a new name/description. Versioning starts from a Draft with no version number. The version is chosen at publish time. Forking is required when changing the set of supported runtimes.

## Revocation

An admin can revoke a specific workflow version:

- **New builds**: Any build that completes after revocation and matches the revoked version's hash is marked **Unauthorized**.
- **Existing builds**: Builds recorded as **Verified** before revocation retain their status. The UI shows a warning: "Built with revoked workflow version X.Y.Z." Deployments from these builds are allowed with the warning.
- **Manifest content**: Cleared on revocation to free storage. The hash is retained for verification.

## Cleanup and Retention

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

## Deprecation and Deletion

Pathfinder tracks CI Workflows and their usage across Services and Builds.

A CI Workflow can be marked as **Archived**, which prevents onboarding new Services but does not block existing service builds or updates to the workflow.

A CI Workflow can be deleted only if no Service uses it and no Build in history references it.
