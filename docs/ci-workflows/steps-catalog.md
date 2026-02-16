# CI Steps Catalog

Steps are references to CI-native constructs. Admins populate the Catalog by connecting a Steps Repository, which Pathfinder scans and imports according to the patterns defined by the selected CI Plugin.

### Step Discovery

The CI Plugin defines a file pattern for step detection (e.g., `**/action.yml` for GitHub Actions). Pathfinder recursively scans the entire repository for matching files, regardless of directory structure. Steps are matched to existing Catalog entries by `x-pathfinder.name`, not by file path. If a step is moved to a different directory, Pathfinder recognizes it as a new version of the same step. The updated path is used when workflows are next updated to reference the new version.

## Steps Repository

When connecting a Steps Repository, the operator selects:
- **SCM Connection**: The source control connection to use.
- **CI Engine**: The target CI engine, chosen from active Pathfinder CI Plugins. The selection is constrained by [SCM compatibility](../integrations.md#ci-engine--scm-compatibility).

Neither field can be modified after creation.

Only one CI Engine is supported per repository. This is intentional—organizations typically use specialized workflows per CI engine and don't need 1:1 step parity across engines.

### Repository Synchronization

Pathfinder tracks repository changes via:
1. **Webhook**: Created automatically via SCM API on registration
2. **Manual poll**: Button in admin UI
3. **Scheduled task**: Daily automatic poll

On sync, Pathfinder resolves the commit SHA on the default branch using native git tools. If the SHA has changed, Pathfinder:
0. Validates Branch Protection rules
1. Fetches the branch contents
2. Parses step definitions according to CI Plugin patterns
3. Updates, adds, or removes steps in the Catalog
4. Logs warnings for any steps that fail to parse (partial imports are allowed)

### Branch Protection Requirements

Before accepting a Steps Repository, Pathfinder validates branch protection on the default branch:

| Rule | Requirement |
|------|-------------|
| Direct push | Disabled (PRs only) |
| Force push | Disabled |
| Required reviews | ≥1 approving review |
| Branch deletion | Disabled |

If protection rules are missing, Pathfinder offers to configure them automatically. Without admin SCM permissions, the repository cannot be added until protection is configured manually.

This encourages customers to fork batteries-included repos into their own SCM, since branch protection cannot be set on repos they don't own.

## Step Identity

A step is uniquely identified by the tuple `(ci_engine, slug)`.

### Name and Slug

The step name is specified in `x-pathfinder.name`. It's human-friendly and may contain spaces and mixed case (e.g., "Test with Pytest").

Pathfinder derives a **slug** from the name: lowercase, spaces/special characters replaced with hyphens, consecutive hyphens collapsed.

| Name | Slug |
|------|------|
| Test with Pytest | `test-with-pytest` |
| Docker Build | `docker-build` |

The slug is used for uniqueness checks, workflow references, and URL paths. The UI displays the human-friendly name.

### Uniqueness Constraint

Slugs must be unique within a CI Engine **across the entire Catalog**. At import time:

1. Pathfinder resolves each step's name and derives the slug
2. If a slug already exists for that CI Engine (from any repository), the step is skipped
3. A warning is attached to the Steps Repository indicating the collision
4. The warning persists until the conflict is resolved

There is no "adoption" mechanism—conflicts must be resolved by renaming or removing one of the conflicting steps.

CI Plugins may provide engine-specific fallbacks for name resolution (e.g., deriving from directory structure), but steps without a resolvable name are skipped with a warning.

## Step Tracking

Pathfinder tracks step definitions to detect changes that may affect dependent workflows.

### Tracked Attributes

| Attribute | Source | Change Impact |
|-----------|--------|---------------|
| `name` | `x-pathfinder.name` | Slug change = new step (old removed) |
| `path` | File location in repo | Manifest reference change on next workflow update |
| `inputs` | Metadata file | Added required input = breaking |
| `outputs` | Metadata file | Removed output = breaking |
| `runtimes` | `x-pathfinder.runtimes` | Constraint narrowing = potentially breaking |
| `phase` | `x-pathfinder.phase` | Organizational only |
| `produces` | `x-pathfinder.produces` | Affects workflow artifact type |

### Change Detection

Change detection is driven by the per-file commit SHA (see [Version Identity via Git](#version-identity-via-git)). On repository sync, for each discovered step file:

1. Compute the per-file commit SHA via `git log -1 --format=%H -- <path>`
2. Compare against the stored `commit_sha` on the Catalog entry
3. **SHA unchanged** → skip, no work needed
4. **SHA changed or new step** → parse the metadata file, upsert the Catalog entry with the new SHA and parsed fields. Compare old and new field values to classify:
   - **Interface change** (inputs/outputs/runtimes/path changed): Workflows using this step receive a warning badge
   - **Metadata change** (tags/description only): Informational, no badge

### Step Removal

Steps can only be removed by deleting the definition file from the Steps Repository — there is no delete action in Pathfinder's UI. On the next sync:

1. The step is marked **archived** in the Catalog and is no longer available for new workflows
2. Workflows referencing it display a warning prompting the author to replace the archived step
3. Existing published workflow versions remain valid — they pin the step at its last commit SHA, which remains retrievable via `git show`
4. The step record is retained in the Catalog as long as any published workflow version references it
5. **Auto-cleanup**: When no workflow version references an archived step, the record is deleted

### Version Identity via Git

Each step is versioned by its own file's last-modified commit SHA (not the repo's HEAD):

- **File identity**: Path within repository (e.g., `test/pytest/action.yml`)
- **Version identity**: `git log -1 --format=%H -- <path>`
- **Content retrieval**: `git show <sha>:<path>`

This ensures step versions remain retrievable even after the file is modified or deleted.

## Step Version Updates

When a step changes, Pathfinder displays a badge on affected CI Workflows indicating a newer version is available. Administrators must manually:
1. Create a draft of the workflow
2. Update the step reference
3. Test the workflow
4. Publish a new workflow version

There is no auto-patching of workflow versions on step updates.

## Step Metadata

Each step includes an `x-pathfinder` block in its metadata file:

```yaml
name: Test with Pytest                # CI-native name
x-pathfinder:
  name: "Test with Pytest"            # Display name → slug: test-with-pytest
  runtimes:
    python: ">=3.10"                  # Runtime constraint
  phase: test                         # UI grouping
  tags: [testing, pytest]             # Search/filter metadata
```

```yaml
name: Docker Build
inputs:
  dockerfile:
    type: string
    default: "Containerfile"

x-pathfinder:
  name: "Docker Build"
  runtimes:
    "*": "*"                          # Runtime-agnostic
  phase: package
  tags: [container, docker]
  produces:
    type: container-image             # container-image | zip | raw
```

### Field Reference

| Field | Description |
|-------|-------------|
| `name` | Human-friendly display name. Must be unique per CI Engine (as slug). |
| `runtimes` | Runtime constraints. Maps runtime names to semver constraints. Use `"*": "*"` for runtime-agnostic steps. |
| `phase` | UI grouping category: `setup`, `build`, `test`, `package`. Does not enforce ordering. |
| `tags` | Soft metadata for search and filtering. |
| `produces` | (Package phase only) Artifact type produced. Used for deployment plugin matching. |

## Manifest Generation

The CI Plugin determines how steps appear in the generated workflow manifest. Two strategies exist:

| Strategy | Used By | Description |
|----------|---------|-------------|
| **Reference with SHA pinning** | GitHub Actions, GitLab CI | Manifest references step code at a pinned commit SHA. CI fetches at build time. |
| **Inline generation** | Bitbucket Pipelines, Jenkins | Plugin compiles step implementation into manifest body. Self-contained. |

Both strategies produce a deterministic manifest whose hash serves as the authorization boundary. See [Build Authorization](build-authorization.md) for verification details.

## Batteries-Included Repositories

Pathfinder ships template step repos, one per CI engine. Customers fork the repos they need, extend them, and configure Pathfinder to scan their fork.

The batteries-included repos organize steps by phase for readability. Customers may reorganize the directory structure after forking — Pathfinder's discovery is structure-agnostic and only cares about the CI-native file patterns within step folders.

```
ci-steps-github/
  setup/
    python/action.yml
    node/action.yml
  test/
    lint-ruff/action.yml
    pytest/action.yml
  security/
    scan/action.yml
  package/
    docker-build/action.yml
```

Steps are not cross-engine portable. Each engine has its own repo with engine-native implementations.

## CI Integration

### Variables

Pathfinder supplies these variables to CI when a workflow is assigned to a Service:

| Variable | Description |
|----------|-------------|
| `PTF_PROJECT` | Project name |
| `PTF_SERVICE` | Service name |
| `PTF_ENVIRONMENT` | Environment name (if artifact is environment-specific) |

Steps should be designed to use these variables for best integration.

### Secrets

CI Secrets are managed at the CI engine level. Steps should reference secrets available in the CI engine or use external secrets providers. Pathfinder does not manage secrets.

## Step Validation API

Pathfinder exposes an internal API endpoint for validating step definitions before they are merged to a Steps Repository. This allows step authors to catch issues during development rather than after sync.

```
POST /api/ci-workflows/steps/validate
Authorization: Token <api-token>
Content-Type: application/json

{
  "ci_engine": "github-actions",
  "content": "<full YAML file content>"
}
```

Response:

```json
{
  "valid": true,
  "step": {
    "name": "Test with Pytest",
    "slug": "test-with-pytest",
    "runtimes": {"python": ">=3.10"},
    "phase": "test",
    "produces": null
  },
  "conflicts": [],
  "warnings": []
}
```

The endpoint runs the same parsing and validation logic used during repository sync: `x-pathfinder` block extraction, slug derivation, conflict detection against the live Catalog, and runtime constraint validation.

This endpoint is intended for authorized access only. It can be integrated into pre-commit hooks or CI checks on the Steps Repository itself.
