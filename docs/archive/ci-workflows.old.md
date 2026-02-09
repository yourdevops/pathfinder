# CI Workflows

## Core Concept

A CI Workflow is a versioned, composable build definition that produces an artifact. It defines what happens between a code push and a deployable artifact appearing in a registry. Pathfinder tracks the produced artifact for downstream use. A CI Workflow does not define how or where the artifact is deployed -- that is an Environment-level concern.

### CI Workflow Fields

- **SCM**: Which SCM Plugin provides the repository. Most likely a single SCM Connection per org, pre-selected as default. The SCM choice constrains CI Engine selection (GitHub Actions requires GitHub SCM; Jenkins is compatible with any SCM). Can not be modified after creation.
- **CI Engine**: Only shown as an active choice when there are multiple CI Plugins configured. Must be compatible with the selected SCM Plugin. Can not be modified after creation.
- **Runtimes**: Derived from the included steps. Each step declares which runtimes it supports; the workflow's runtimes are the union of all step runtime declarations. Runtimes are immutable within a workflow lineage—adding or removing a runtime requires forking the workflow (see Change Classification).
- **Version Constraints**: For each runtime, the workflow specifies version constraints (e.g., `python: ">=3.11"`), derived from the intersection of all included steps' constraints for that runtime. The workflow author can further narrow these constraints. Concrete version selection (e.g., `3.12`) happens at the Service level.
- **Development Workflow**:
Trunk-based development, GitHub Flow and others. Creates a skeleton structure for visual editor, that represents conditional behaviors for code transition between branches. Not the scope for MVP.
- **CI Steps**: Ordered list of steps from the registry, with per-step config. See CI Steps Registry below.

### Step Ordering Rules

1. **Setup-before-use**: A step for a specific runtime requires a `setup` step for the same runtime anywhere earlier in the workflow. For example, `test-pytest` (python) requires `setup-python` to appear before it. Pathfinder blocks saving a workflow that violates this constraint.
2. **Runtime-agnostic steps**: Steps with `*` as their runtime (e.g., `docker-build` for Containerfiles) have no setup requirement.

The artifact type is declared by the packaging step in the CI Steps Registry metadata (see `produces` in Step Metadata). The CI Workflow's artifact type is derived from the last step in the pipeline whose phase is `package`.

---

## Versioning

A CI Workflow is versioned using semver. Version numbers are chosen by the author at publish time. Each published version produces an immutable manifest with a content hash used for build authorization (see [Manifest Identifier & Build Authorization](builds-manifest-identifier.md)).

Services that use a CI Workflow can auto-update to new patch versions. Upgrading to a Minor/Major version is a manual procedure. Pathfinder compares the newly published version against each Service's current version using semver to determine whether the update falls within the Service's auto-update policy.

On upgrade, Pathfinder pushes the updated pipeline manifest to the Service repo. According to the configured option in the Service Settings, Pathfinder either opens a PR against the main branch or pushes directly. If an open PR with the same scope/author exists (autoupdate CI manifest), Pathfinder reuses it as a Digest PR for all CI manifest changes.

Pathfinder's commit can be optionally marked with a skip-CI comment so it does not trigger CI execution.

A user can fork an existing CI Workflow with a new name/description. Versioning starts from a Draft with no version number. The version is chosen at publish time. Forking is required when changing the set of supported runtimes (see Change Classification).

### Change Classification

- **Runtime changes require forking.** Adding or removing a runtime (by adding/removing steps that introduce or drop a runtime) triggers a fork prompt. This keeps workflow names meaningful (e.g., `python-uv` CI Workflow stays Python-only) and preserves version lineage for existing services.
- CI Engine change is not possible. Pathfinder by itself can not guarantee the Steps compatibility between CI Engines.
- Step additions/removals within the same runtime set, step version updates, and config changes are normal version bumps (Minor or Patch as appropriate).

### Deprecation and Deletion

Pathfinder tracks CI Workflows and their usage across Services and Builds.

A CI Workflow can be marked as Deprecated, which prevents onboarding new Services but does not block existing service builds or updates to the workflow.

A CI Workflow can be deleted only if no Service uses it and no Build in history references it.

### Draft and Publish

Each CI Workflow has at most **one draft** at a time. The draft has no version number; the author chooses the version when publishing.

**Draft lifecycle**:
1. Author creates a draft (claims the single draft slot for this workflow).
2. Author edits the workflow definition. The manifest regenerates on each edit with a mutable hash.
3. Another author with sufficient permissions can **take over** the draft.
4. Author clicks **Publish**: chooses a version number (must be valid semver, must not already exist, must be greater than the current latest authorized version). The manifest hash becomes immutable and the version enters the authorized set.
5. Or author **discards** the draft: no version is claimed, the draft is deleted.

**Draft builds**: Builds that run against a draft manifest are recorded but marked as **Draft** verification status. They are deployable to non-production environments but **blocked from production environments**. This allows pipeline testing without compromising the production deployment gate.

To use a Draft workflow on a Service, a Project admin must enable "Allow Drafts" in the Project's Approved Workflows settings and explicitly set the draft workflow in the Service Settings.

---

## CI Steps Registry

Steps are references to CI-native constructs. Admins populate the registry by pointing Pathfinder at a repository. Pathfinder scans and imports step definitions:

| CI Platform | Step Unit | Filename |
|-------------|-----------|---------------|
| GitHub Actions | Action | `action.yml` |
| Bitbucket | Pipe | `pipe.yml` |
| GitLab | Component | `template.yml` |
| Jenkins | Shared Library | `vars/*.groovy` (must contain x-pathfinder metadata in comments) |

Pathfinder creates a webhook in the repo via the SCM Connection for change notifications. There is also a manual poll button and a daily scheduled task to poll registered repos.

### Steps Repository Protection

When adding a Steps Repository, Pathfinder validates branch protection on the default branch via the SCM API:

- **Required reviews**: At least one approving review before merge.
- **No force pushes**: Force push must be disabled.
- **No branch deletion**: Branch deletion must be disabled.

If protection rules are missing, Pathfinder proposes to configure them automatically. If the SCM Connection lacks admin permissions to set protection rules, the repository cannot be added until protection is configured manually. This also incentivizes customers to fork the batteries-included repos into their own SCM (branch protection cannot be set on repos the customer doesn't own), which is the intended workflow.

### Step Versioning

Upon a change, Pathfinder rescans step definitions. Each step is versioned by its own file's last-modified commit SHA (not the repo's HEAD).

On a step version update, Pathfinder displays a badge on affected CI Workflows indicating the step has a newer version available. The admin manually creates a draft, updates the step reference, tests, and publishes a new workflow version. Pathfinder does **not** auto-patch workflow versions on step updates. This keeps version creation always human-initiated.

### Manifest Generation Strategy

The CI Plugin is solely responsible for how steps are represented in the generated manifest. Pathfinder core treats the manifest as opaque bytes that get hashed. Different engines use different strategies:

- **Reference with SHA pinning** (e.g., GitHub Actions, GitLab CI): The manifest contains references to step code at a specific commit SHA. The CI engine fetches step code at build time from the pinned commit. The SHA is part of the manifest content and therefore part of the hash.
- **Inline generation** (e.g., Bitbucket Pipelines, Jenkins): The plugin reads step implementation at the pinned commit SHA and compiles it into the manifest body. The manifest is self-contained with no runtime resolution of external code.

Both strategies produce a deterministic manifest whose hash serves as the authorization boundary. The strategy choice is an implementation detail of each CI plugin.

### Batteries-Included Repos

Ship template step repos, one per CI engine. Customers fork the repos they need into their SCM, extend them, and Pathfinder scans to populate their registry.

Steps are not cross-engine portable. Each CI engine has its own batteries-included repo with engine-native step implementations. Customers fork only the repos for engines they use.

MVP focus: GitHub Actions for Python >=3.10.

```
ci-steps-github/
  setup-python/action.yml
  lint-ruff/action.yml
  test-pytest/action.yml
  security-scan/action.yml
  docker-build/action.yml
```

Build lifecycle reporting (start, completion, status) is handled by CI-engine-native mechanisms (e.g., GitHub `workflow_run` webhooks), not by injected steps. See Build Lifecycle below.

### Step Metadata

Each step includes an `x-pathfinder` block in its metadata file:

```yaml
# Runtime-specific step (requires Python 3.10+)
name: Test with Pytest
x-pathfinder:
  runtimes:
    python: ">=3.10"
  phase: test
  tags: [testing, pytest]
```

```yaml
# Runtime-agnostic step (works with any workflow)
name: Docker Build
inputs:
  dockerfile:
    type: string
    default: "Containerfile"

x-pathfinder:
  runtimes:
    "*": "*"
  phase: package
  tags: [container, docker]
  produces:                           # only for steps with phase: package
    type: container-image             # container-image | zip | raw
```

- **`runtimes`**: Declares which runtimes this step supports. Maps runtime names to semver version constraints. Examples:
  - `python: ">=3.10"` — requires Python 3.10 or higher
  - `node: "*"` — works with any Node.js version
  - `"*": "*"` — runtime-agnostic step (e.g., docker-build, artifact upload)
  - Multiple entries indicate the step works with multiple runtimes (rare; typically for polyglot tooling)
- **`phase`**: Organizational category for UI grouping. One of: `setup`, `build`, `test`, `package` (more phases may be added). Does not enforce ordering—ordering is determined by runtime dependencies.
- **`tags`**: Soft metadata for UI organization and search.
- **`produces`**: Declared on packaging steps. Specifies the artifact type produced. Pathfinder uses this to determine what the CI Workflow outputs and to match against environment deploy plugin capabilities at deployment time.

### CI Secrets

CI Secrets are managed at the CI engine level. Steps reference secrets available in that CI. Pathfinder does not manage secrets.

### CI Variables

Pathfinder supplies the following variables to CI when a repo is initialized with a CI Workflow:

```
PTF_PROJECT = <project-name>
PTF_SERVICE = <service-name>
```

CI Steps should expect these variables.

### Monorepo Support

Monorepo support may be implemented via custom CI Steps that scope builds to a subdirectory.

### Multi-Artifact Builds

A CI Workflow produces exactly one artifact. When a single repository needs multiple deployable artifacts (e.g. an API server and a background worker), each artifact is a separate Service with its own CI Workflow. The Services may share a repository. Multi-architecture builds (e.g. `linux/amd64` + `linux/arm64`) are a CI engine concern handled via step configuration, not a workflow-level concept.

---

## Build Lifecycle

### Triggering a Build

A build is triggered by a push to the main branch of a Service's repository. The CI engine executes the workflow. Pathfinder is notified of build state changes via CI-engine-native webhooks (e.g., GitHub `workflow_run` events). No Pathfinder-specific steps are injected into the pipeline.

### Build State and Artifact Discovery

CI engine webhooks are treated as **notification signals only**. On receiving a build state webhook, Pathfinder calls the CI engine API to fetch authoritative data:

- **Build status**: Actual success/failure from the CI engine API, not from the webhook payload.
- **Build metadata**: Commit SHA, author, timing, job details.
- **Artifact reference**: Image ref, digest, or other artifact identifiers. Discovery is CI-engine-specific (e.g., GitHub Packages API, registry query). The CI plugin is responsible for resolving the artifact reference.

The artifact type and reference are used downstream to match against environment deploy plugin capabilities. The artifact block is present only on success and only when the workflow includes a packaging step.

### Build Verification

On every build completion, Pathfinder verifies the manifest that produced the build:

1. Fetch the manifest content from the repo at the build's `commit_sha` via the CI engine API.
2. Compute the SHA-256 hash of the fetched content.
3. Compare the hash against known authorized workflow versions.

The result determines whether the build's artifacts are deployable. See [Manifest Identifier & Build Authorization](builds-manifest-identifier.md) for the full verification model.

### Build Records

Each Service maintains a list of Builds. A Build record contains:
- Build ID (from CI engine)
- Commit SHA
- Manifest ID (CI-engine-specific path to the workflow file)
- Manifest hash (SHA-256 of the manifest file at the build's commit SHA)
- Linked CI Workflow version (if hash matched a known version; null otherwise)
- Verification status: `verified`, `revoked`, `draft`, or `unauthorized`
- Status (running, success, failure)
- Artifact reference (type, ref, digest) -- if exists
- Timestamp

Only builds with `verified` or `revoked` (with warning) verification status produce deployable artifacts. Builds marked `unauthorized` or `draft` (for production environments) are blocked from deployment.

---

## What CI Workflows Do Not Do

- Abstract away CI syntax into a proprietary DSL
- Promise cross-CI portability (a GitHub Actions workflow will not auto-convert to Jenkins)
- Replace existing CI systems
- Define or execute deployments -- that is an Environment and Deploy Plugin concern
- Manage CI secrets
- Manage service secrets
