# Scaffolding

Scaffolding creates a new service repository from a registered template. Pathfinder walks the operator through a multi-step wizard that collects service details, configures required variables, and produces a service-ready repository with `pathfinder.yaml` transformed from `kind: template` to `kind: service`.

## Wizard Flow

The service creation wizard collects all inputs before any repository changes are made. Each page validates its inputs before the operator can proceed.

```
Wizard Page 1: Template Selection
  - Select template from registered list
  - Select version (git tag) from available tags
  - Enter service name (becomes the "name" in kind: service manifest)
  - Select Project

        |
        v

Wizard Page 2: New Repository Setup
  - Enter repo name and default branch
  - Configure branch protection settings
  Note: Templates scaffold new repos only. Existing repos are onboarded
  separately without scaffolding -- see "Non-Scaffolded Services".

        |
        v

Wizard Page 3: Configure Required Variables
  - Pathfinder reads required_vars from template manifest
    at the selected tag's commit SHA
  - Each variable shown with:
      - Variable name (e.g., DATABASE_URL)
      - Description from manifest as helper text
      - Input field for initial value
  - Operator provides initial value for each variable
  - Variables with no value cannot proceed

        |
        v

Wizard Page 4: CI Workflow Recommendation
  - Pathfinder reads runtimes from template manifest
  - Displays compatible CI Workflows based on runtime match
  - Operator confirms or changes the recommendation
  - Selected CI Workflow is associated with the service

        |
        v

Wizard Page 5: Review & Confirm
  - Summary of all selections
  - Operator confirms to begin scaffolding
```

### Page Details

**Page 1** reads from the template registry. The version list is the set of git tags on the template repository, presented in reverse chronological order. Pathfinder reads `pathfinder.yaml` at the selected tag's commit SHA to extract metadata for subsequent pages.

**Page 2** creates a new repository only. There is no option to select an existing repository. This avoids the complexity of file collision, overwrite, and merge logic. Services backed by existing repos are onboarded through a separate path that does not involve scaffolding.

**Page 3** reads `required_vars` from the template manifest at the selected tag's commit SHA. The description string for each variable is displayed as helper text alongside the input field. If the template declares no `required_vars`, this page is skipped or shown as empty with a note that no variables are required.

**Page 4** uses the `runtimes` field from the template manifest to filter the list of available CI Workflows. Runtimes inform the recommendation but do not automatically assign a workflow -- the operator makes the final selection. If the template declares no `runtimes`, all CI Workflows are shown without filtering.

**Page 5** is a read-only summary. No changes are made until the operator confirms.

## Scaffolding Execution

After the operator confirms on page 5, Pathfinder executes the scaffolding sequence. All steps run as a single operation -- there is no partial scaffolding state.

```
Scaffolding begins (new repo only)
        |
        v
1. Fetch template repository at selected tag's commit SHA
        |
        v
2. Copy file tree to new repository (default branch)
        |
        v
3. Transform pathfinder.yaml:
   - Change kind: "template" to kind: "service"
   - Set name to the service name entered in wizard
   - All other fields (description, runtimes,
     required_vars) are preserved unchanged
        |
        v
4. Push CI Workflow manifest to new repo
   (the CI Workflow selected in wizard page 4)
        |
        v
5. Commit and push scaffolded files to default branch
        |
        v
6. Create Service record in Pathfinder
        |
        v
7. Store initial required_var values entered
   in wizard as env_vars in Pathfinder
   (stored at environment level)
        |
        v
Scaffolding complete
```

### Step Details

**Step 1** fetches the template at the exact commit SHA of the selected tag, not HEAD. This ensures the scaffolded files match the tagged version the operator selected.

**Step 2** copies the entire file tree from the template into the new repository. No files are excluded or transformed beyond the manifest change in step 3.

**Step 3** is the manifest transformation. See [Manifest Transformation](#manifest-transformation) below for the full before/after example.

**Step 4** pushes the CI Workflow manifest file to the new repository. The manifest file is generated from the CI Workflow version assigned to the service. This happens during scaffolding execution, not as a separate operation afterward.

**Step 5** commits all files (the template tree, transformed manifest, and CI Workflow manifest) and pushes to the default branch.

**Step 6** creates the Service record in Pathfinder's database, linked to the selected Project, template, and version.

**Step 7** stores the variable values that the operator entered in wizard page 3 as `env_vars` entries in Pathfinder. These are stored at the environment level, making them available for the deployment gate when the first build completes.

## Manifest Transformation

Scaffolding transforms `pathfinder.yaml` from `kind: template` to `kind: service`. This is the mechanism by which every service repository self-describes its requirements.

The transformation changes exactly two fields:

- `kind` changes from `"template"` to `"service"`
- `name` changes from the template name to the service name entered in the wizard

All other fields are preserved verbatim.

### Before (Template Manifest at Selected Tag)

```yaml
kind: template
name: python-fastapi
description: "FastAPI service with async PostgreSQL"
runtimes:
  - python: ">=3.11"
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
  SECRET_KEY: "Application secret key"
```

### After (Service Manifest in Scaffolded Repo)

```yaml
kind: service
name: order-service          # Set to wizard-entered service name
description: "FastAPI service with async PostgreSQL"
runtimes:
  - python: ">=3.11"         # Preserved -- informational only post-scaffolding
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
  SECRET_KEY: "Application secret key"
```

The `required_vars` section is preserved verbatim from the template. The transformation only changes `kind` and `name`. This ensures the service repo's manifest accurately declares the same variables the template required.

For the `pathfinder.yaml` field format, see [Manifest Schema](manifest-schema.md).

## Post-Scaffolding State

After scaffolding completes, two things exist: the new service repository and the Pathfinder records.

### Service Repository State

- Contains all files from the template at the selected tag
- `pathfinder.yaml` present in repo root with `kind: service`
- `name` field matches the service name in Pathfinder
- CI Workflow manifest already present (pushed during scaffolding step 4)
- Default branch has a single commit with all scaffolded files

Scaffolded repos always have `pathfinder.yaml`. Scaffolding creates it -- it is never optional.

### Pathfinder State

- Service record created and linked to the Project
- Initial `required_var` values stored in `env_vars` (at environment level)
- CI Workflow associated with the service (from wizard selection)
- Template and version recorded (for audit and display purposes)

## First Build

After scaffolding, the service repository is ready for development. The first build webhook triggers the variable lifecycle for the first time.

```
Developer pushes first commit to service repo
        |
        v
Build webhook received
        |
        v
Pathfinder reads pathfinder.yaml at commit SHA
Finds kind: service with required_vars
        |
        v
Compares against stored required_vars
(initial values already in env_vars from wizard)
        |
        v
All vars satisfied (wizard captured initial values)
        |
        v
Deployment gate: allowed
```

Because the scaffolding wizard collected initial values for all required variables, the first build should find all variables satisfied. If the operator skipped or left values empty during the wizard, the first build may find unsatisfied variables and block deployment.

For full variable lifecycle behavior, see [Variable Lifecycle](variable-lifecycle.md).

## Non-Scaffolded Services

Existing service repositories can be onboarded to Pathfinder without scaffolding. These repos do not automatically get a `pathfinder.yaml`. An operator can add `pathfinder.yaml` manually to an existing service repo to enable variable discovery and enforcement. The file must use `kind: service`. Once present, Pathfinder reads it at build time like any scaffolded service.

### CI Workflow Manifest for Non-Scaffolded Services

When a CI Workflow is assigned to a non-scaffolded service, Pathfinder pushes the CI Workflow manifest via Pull Request. This happens after the operator confirms the CI Workflow assignment in service settings -- not during a scaffolding step, because there is no scaffolding step for existing repos.

This differs from scaffolded services, where the CI Workflow manifest is pushed directly to the default branch during scaffolding execution (step 4). For non-scaffolded services, the Pull Request approach gives the service team an opportunity to review the manifest before it is merged.

For how CI Workflow manifests are versioned and pushed, see [CI Workflows -- Versioning](../ci-workflows/versioning.md).
