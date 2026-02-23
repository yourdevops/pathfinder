# Template Registration

Operators register templates by providing a git URL. Pathfinder fetches the repository and reads `pathfinder.yaml` from the root to extract template metadata. Git tags on the template repository become selectable versions in the service creation wizard.

## Registration Flow

Registration is a manual process. The operator provides a git URL and Pathfinder validates the repository.

```
Operator provides git URL
        |
        v
Pathfinder fetches repository
(shallow clone of default branch HEAD)
        |
        v
Pathfinder reads pathfinder.yaml from repo root
        |
        v
Validation:
  - kind must be "template"
  - name field must be present
  - Schema must be valid
        |
        v
Validation passes?
   |          |
  YES         NO
   |          |
   v          v
Creates      Registration
Template     fails with
record       error message
   |
   v
Fetches all git tags from repository
Each tag becomes a selectable version
   |
   v
Template is available for use in Projects
```

If validation fails, the operator sees the specific error (e.g., "kind is not template", "name field missing", "invalid YAML syntax"). No partial record is created on failure.

## Required Fields

For a git repository to be registerable as a template, `pathfinder.yaml` must contain:

| Field | Required | Value |
|-------|----------|-------|
| `kind` | Yes | Must be `"template"` |
| `name` | Yes | DNS-compatible identifier |
| `description` | No | Human-readable summary |
| `runtimes` | No | List of runtime constraints |
| `required_vars` | No | Map of variable declarations |

A minimal valid template manifest needs only `kind: template` and a `name`. All other fields enhance the template's metadata and the service creation experience.

For the full `pathfinder.yaml` schema, see [Manifest Schema](manifest-schema.md).

## Git Tags as Versions

Git tags on the template repository are the version system. There is no separate version number assigned by Pathfinder -- each tag on the remote is a selectable version entry.

Key behaviors:

- Each git tag on the template repo becomes a selectable version entry in Pathfinder.
- When creating a service, the operator selects a version (git tag) from the available list.
- Pathfinder reads `pathfinder.yaml` at the selected tag's commit SHA (not HEAD). This ensures the manifest matches the tagged code snapshot.
- Scaffolding uses the file tree at the selected tag's commit SHA.
- Tags can follow any naming convention (e.g., `v1.0.0`, `v1`, `2024-01`, `release-candidate`).
- Pathfinder presents tags in reverse chronological order (newest first).

Example of how versions appear:

```
Template: python-fastapi
Available versions:
  v2.1.0   (latest)
  v2.0.0
  v1.3.2
  v1.3.1
  v1.3.0
  v1.2.0
```

A template with no git tags has only HEAD as its version source. Operators are encouraged to tag releases to give users stable, selectable versions.

## Sync

Operators can trigger a manual sync on a registered template to refresh its metadata and version list. There is no automatic sync.

**What sync does:**

1. Re-fetches the repository from the git URL.
2. Reads `pathfinder.yaml` from HEAD of the default branch.
3. Updates the Template record metadata (name, description, runtimes, required_vars) from the manifest.
4. Fetches the current git tag list -- new tags are added as available versions.
5. Tags that no longer exist on the remote are not automatically removed (they remain visible but are flagged as unavailable).

**What sync does NOT do:**

- Does not automatically retrigger scaffolding for existing services.
- Does not push manifest updates to existing service repos.
- Does not auto-update services that were created from earlier versions.

Sync is a metadata refresh only. It brings Pathfinder's view of the template up to date with the remote repository. Services created from earlier versions remain on their original version.

For how `pathfinder.yaml` fields affect template display, see [Manifest Schema](manifest-schema.md).

## Template Availability

Templates are available to all Projects by default once registered. Access scoping (restricting templates to specific Projects or teams) is a future concern and not part of the current design.

A template can be deregistered if no service was ever created from it. Deregistering a template that has been used to create services is blocked to preserve scaffolding history and audit traceability.
