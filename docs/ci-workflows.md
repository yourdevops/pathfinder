# CI Workflows

## Core Concept

A CI Workflow is a versioned, composable build definition that produces an artifact. It defines what happens between a code push and a deployable artifact appearing in a registry. A CI Workflow does not define how or where the artifact is deployed -- that is an Environment-level concern.

### Development Workflow

Trunk-based development, non-negotiable. Code on the main branch is treated as production-ready at any point. CI Workflows execute on every push to the main branch.

### CI Workflow Fields

- **SCM**: Which SCM Plugin provides the repository. Most likely a single SCM Connection per org, pre-selected as default. The SCM choice constrains CI Engine selection (GitHub Actions requires GitHub SCM; Jenkins is compatible with any SCM).
- **Runtime**: Execution context (e.g. `node:22`, `python:3.12`). A CI Workflow has exactly one primary runtime. Polyglot repositories must either split into separate Services or use custom CI Steps that internally handle secondary runtimes. The user selects a runtime family from a dropdown, then a concrete version. Both lists are sourced from the `runtimes.yml` manifest in the steps repo (see CI Steps Registry). When CI Steps are selected, DevSSP validates that the chosen runtime satisfies every step's version constraint and highlights incompatible steps with a warning.
- **CI Engine**: Only shown as an active choice when there are multiple CI Plugins configured. Must be compatible with the selected SCM Plugin.
- **CI Steps**: Ordered list of steps from the registry, with per-step config. See CI Steps Registry below.

The artifact type is not selected by the user. It is declared by the packaging step in the CI Steps Registry metadata (see `produces` in Step Metadata). The CI Workflow's artifact type is derived from the last step in the pipeline whose phase is `package`.

---

## Versioning

A CI Workflow is versioned using semver. Patch version updates automatically on edits. Users can optionally mark changes as Major, Minor, or Patch.

Services that use a CI Workflow can auto-update to new patch versions. Upgrading to a Minor/Major version is a manual procedure.

On upgrade, DevSSP pushes the updated pipeline manifest to the Service repo. According to the configured option in the Service Settings, DevSSP either opens a PR against the main branch or pushes directly. If an open PR with the same scope/author exists (autoupdate CI manifest), DevSSP reuses it as a Digest PR for all CI manifest changes.

DevSSP's commit is marked with a skip-CI comment so it does not trigger CI execution. If a build is needed, it can be triggered manually from DevSSP.

A user can fork an existing CI Workflow with a new name/description. Versioning starts from 0.0.1 Draft by default, but the user can set the starting version manually.

### Change Classification

- Runtime changes are not allowed. To change runtime, fork the CI Workflow.
- CI Engine change is at least a Minor change.
- More than one structural change in one edit is a Major change. DevSSP should propose to fork instead.

A CI Engine can only be changed if equivalent CI Steps exist in the registry for that engine. DevSSP raises visual warnings for each missing step and blocks finalization until all steps passing the check.

A Service can change its CI Workflow only to relative workflows (forked or upstream). The runtime may evolve within the same family (e.g. `python:3.12` to `python:3.13`) but not be replaced (e.g. `python` to `node`). For unrelated runtimes, the only option is to create a new Service.

### Deprecation and Deletion

DevSSP tracks CI Workflows and their usage across Services and Builds.

A CI Workflow can be marked as Deprecated, which prevents onboarding new Services but does not block existing service builds or updates to the workflow.

A CI Workflow can be deleted only if no Service uses it and no Build in history references it.

### Draft and Publish

Upon creation or edit, the user can Save as Draft or Publish. To use a Draft workflow, a Project admin must enable "Show Drafts" in the Project's Approved Workflows settings and explicitly add the draft. Once tested, a user can Publish the workflow, making it available globally within DevSSP.

---

## CI Steps Registry

Steps are references to CI-native constructs. Admins populate the registry by pointing DevSSP at a repository. DevSSP scans and imports step definitions:

| CI Platform | Step Unit | Filename |
|-------------|-----------|---------------|
| GitHub Actions | Action | `action.yml` |
| Bitbucket | Pipe | `pipe.yml` |
| GitLab | Component | `template.yml` |
| Jenkins | Shared Library | `vars/*.groovy` (must contain x-pathfinder metadata in comments) |

DevSSP creates a webhook in the repo via the SCM Connection for change notifications. There is also a manual poll button and a daily scheduled task to poll registered repos.

Upon a change, DevSSP rescans step definitions. Each step is versioned by its own file's last-modified commit SHA (not the repo's HEAD).

On a step version update, DevSSP patches the CI Workflow's patch version with a changelog notice: `updated Step [id] to version [commit sha]`.

### Batteries-Included Repo

Ship a template monorepo with common steps. Customers fork, extend, and DevSSP scans to populate their registry.

MVP focus: GitHub Actions for Python >=3.10.

```
ci-steps/
  setup-python/action.yml
  setup-python/pipe.yml
  src/setupPython.groovy
  lint-ruff/action.yml
  test-pytest/action.yml
  security-scan/action.yml
  docker-build/action.yml
  ssp-notify-start/action.yml
  ssp-notify-complete/action.yml
runtimes.yml
```

The `ssp-notify-start` and `ssp-notify-complete` actions send webhooks to DevSSP to report build start and completion. These are automatically injected as the first and last steps when DevSSP scaffolds a CI manifest.

### Runtime Manifest

The steps repo contains a `runtimes.yml` at the root. It enumerates runtime families and their known versions:

```yaml
# runtimes.yml
python:
  versions: ["3.11", "3.12", "3.13"]
node:
  versions: ["18", "20", "22", "24"]
```

DevSSP scans this file alongside step definitions. Admins add runtimes or versions by editing this file. The same webhook/polling mechanism applies.

### Step Metadata

Each step includes an `x-pathfinder` block in its metadata file:

```yaml
name: Docker Build
inputs:
  dockerfile:
    type: string
    default: "Containerfile"

x-pathfinder:
  runtimes:
    python: ">=3.10"
  phase: package                      # setup | build | test | package
  tags: [container, docker]
  produces:                           # only for steps with phase: package
    type: container-image             # container-image | zip | raw
```

- **`runtimes`**: Hard filter. Maps runtime names to semver version constraints. A step is eligible when the workflow's runtime name matches a key and its version satisfies the constraint. `"*"` matches all versions.
- **`phase`**: Ordering hint. One of: `setup`, `build`, `test`, `package`. Defaults inferred if missing.
- **`tags`**: Soft metadata for UI organization and search.
- **`produces`**: Declared on packaging steps. Specifies the artifact type produced. DevSSP uses this to determine what the CI Workflow outputs and to match against environment deploy plugin capabilities at deployment time.

### CI Secrets

CI Secrets are managed at the CI engine level. Steps reference secrets available in that CI. DevSSP does not manage secrets.

### CI Variables

DevSSP supplies the following variables to CI when a repo is initialized with a CI Workflow:

```
SSP_PROJECT = <project-name>
SSP_SERVICE = <service-name>
```

CI Steps should expect these variables.

### Monorepo Support

Monorepo support may be implemented via custom CI Steps that scope builds to a subdirectory.

### Multi-Artifact Builds

A CI Workflow produces exactly one artifact. When a single repository needs multiple deployable artifacts (e.g. an API server and a background worker), each artifact is a separate Service with its own CI Workflow. The Services may share a repository. Multi-architecture builds (e.g. `linux/amd64` + `linux/arm64`) are a CI engine concern handled via step configuration, not a workflow-level concept.

---

## Build Lifecycle

### Triggering a Build

A build is triggered by a push to the main branch of a Service's repository. The CI engine executes the workflow. DevSSP is notified via the `ssp-notify-start` webhook at the beginning and `ssp-notify-complete` at the end.

### Build Completion Webhook

On completion, the `ssp-notify-complete` step sends a payload to DevSSP:

```json
{
  "service": "<service-name>",
  "project": "<project-name>",
  "build_id": "<ci-engine-build-id>",
  "commit_sha": "<sha>",
  "status": "success | failure",
  "artifact": {
    "type": "container-image",
    "ref": "ghcr.io/org/my-api:sha-7c097f3",
    "digest": "sha256:abc123..."
  }
}
```

DevSSP stores this as a Build record on the Service. The `artifact` block is present only on success and only when the workflow includes a packaging step. The artifact type and reference are used downstream to match against environment deploy plugin capabilities.

### Build Records

Each Service maintains a list of Builds. A Build record contains:
- Build ID (from CI engine)
- Commit SHA
- CI Workflow version used
- Status (running, success, failure)
- Artifact reference (type, ref, digest) -- if successful
- Timestamp

---

## Repository Templates

OPTIONAL. In the same repo where steps are stored, directories under `repo-templates/` with a `template.yaml` file are scanned. DevSSP uses the description and metadata from `template.yaml` to populate a list of available repo templates for Service creation.

---

## Artifact-to-Deployment Matching

When a Build completes successfully, DevSSP stores the artifact reference (type, registry ref, digest) on the Service's Build record. When a user triggers a deployment to an Environment, DevSSP matches the artifact type against the Environment's Deploy Plugin capabilities:

| Artifact Type | Compatible Deploy Plugins |
|---------------|--------------------------|
| `container-image` | Direct Docker, Kubernetes (future) |
| `zip` | Lambda (future), S3 (future) |
| `raw` | SCP/SFTP (future) |

If the artifact type is incompatible with the target Environment's Deploy Plugin, the deployment is blocked with an explanation.

---

## What CI Workflows Do Not Do

- Abstract away CI syntax into a proprietary DSL
- Promise cross-CI portability (a GitHub Actions workflow will not auto-convert to Jenkins)
- Replace existing CI systems
- Define or execute deployments -- that is an Environment and Deploy Plugin concern
- Manage CI secrets
- Manage service secrets
