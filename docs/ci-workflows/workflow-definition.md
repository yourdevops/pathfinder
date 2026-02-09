# Workflow Definition

A CI Workflow is a versioned, composable build definition that, when run on CI, produces an artifact. It defines what happens between a code push and a deployable artifact appearing in a registry. Pathfinder tracks the produced artifact for downstream use.

A CI Workflow does not define how or where the artifact is deployed — that is an Environment-level concern.

## CI Workflow Fields

- **SCM**: Which SCM Plugin provides the repository. Most likely a single SCM Connection per org, pre-selected as default. The SCM choice constrains CI Engine selection per [SCM compatibility](../integrations.md#ci-engine--scm-compatibility). Cannot be modified after creation.

- **CI Engine**: Choice of available CI Engines is derived from the CI Engines of connected Steps Repositories. Only shown as an active choice when more than one CI Engine is available. Must be compatible with the selected SCM Plugin. Cannot be modified after creation.

- **Runtimes**: Derived from the CI Steps included into a Workflow. Each Step declares which runtimes it supports; the Workflow's runtimes are the union of all Step runtime declarations. Runtimes are immutable within a workflow lineage—adding or removing a runtime requires forking the Workflow (see [Versioning](versioning.md#change-classification)).

- **Version Constraints**: For each Runtime, the Workflow specifies version constraints (e.g., `python: ">=3.11"`), derived from the intersection of all included Steps' constraints for that runtime. The Workflow author can further narrow these constraints. Concrete version selection (e.g., `3.12`) happens at the Service level.

- **Development Workflow**: Trunk-based development, GitHub Flow, and others. Creates a skeleton structure for visual editor that represents conditional behaviors for code transition between branches. Not in scope for MVP.

- **CI Steps**: Ordered list of steps from the Catalog, with per-step config. See [Steps Catalog](steps-catalog.md).

## Step Ordering Rules

1. **Setup-before-use**: A step for a specific runtime requires a `setup` step for the same runtime anywhere earlier in the workflow. For example, `test-pytest` (python) requires `setup-python` to appear before it. Pathfinder blocks saving a workflow that violates this constraint.

2. **Runtime-agnostic steps**: Steps with `*` as their runtime (e.g., `docker-build` for Containerfiles) have no setup requirement.

The artifact type is declared by the packaging step in the CI Steps Catalog metadata (see `produces` in [Step Metadata](steps-catalog.md#step-metadata)). The CI Workflow's artifact type is derived from the last step in the pipeline whose phase is `package`.

## Monorepo Support

Monorepo support may be implemented via custom CI Steps that scope builds to a subdirectory.

## Multi-Artifact Builds

A CI Workflow produces exactly one artifact. When a single repository needs multiple deployable artifacts (e.g., an API server and a background worker), each artifact is a separate Service with its own CI Workflow. The Services may share a repository.

Multi-architecture builds (e.g., `linux/amd64` + `linux/arm64`) are a CI engine concern handled via step configuration, not a workflow-level concept.
