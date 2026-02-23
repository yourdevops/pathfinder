# Template Registration

Operators register templates by providing a git URL. Pathfinder fetches the repository and reads `pathfinder.yaml` from the root to extract template metadata. Git tags on the template repository become selectable versions in the service creation wizard.

## Registration Flow

Registration is a manual process. The operator selects the SCM provider and provides a git URL. Pathfinder validates the repository, registers it, then attempts to configure webhooks and protection rules on the SCM side. Warning is shown in UI if that fails.

```
Operator provides SCM provider + git URL
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
  - name field must be present and DNS-compatible
  - name must not already be registered to another template
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
(keyed on
 name)
   |
   v
Fetches all git tags from repository
Each semver tag becomes a selectable version
   |
   v
Sets up webhooks and protection rules (see below)
   |
   v
Template is available for use in the service creation wizard
```

If validation fails, the operator sees the specific error (e.g., "name field missing", "template `python-fastapi` is already registered", "invalid YAML syntax"). No partial record is created on failure.

### Post-Registration Setup

After creating the Template record, Pathfinder configures the SCM provider via its plugin interface:

**Webhooks** — Two webhook events are registered:
- Push to main branch — triggers a metadata sync.
- Tag push — triggers version list refresh and tag validation.

**Protection rules** (where supported by the provider):
- Branch protection on `main` (prevent force-push, require linear history).
- Tag protection restricting tag names to semver pattern (`v?[0-9]+.[0-9]+.[0-9]+`).

Not all providers support all rules. The plugin interface reports what was applied; Pathfinder logs but does not block registration if a rule cannot be set.

## Required Fields

For a git repository to be registerable as a template, `pathfinder.yaml` must contain:

| Field | Required | Value |
|-------|----------|-------|
| `name` | Yes | DNS-compatible identifier |
| `description` | No | Human-readable summary |
| `runtimes` | No | List of runtime constraints |
| `required_vars` | No | Map of variable declarations |

A minimal valid template manifest needs only a `name`. All other fields enhance the template's metadata and the service creation experience.

### name as unique identity

The `name` field is the template's identity in Pathfinder. It serves as the unique key, the display name, and the audit reference on scaffolded services.

- Two templates cannot share the same `name`. Registration fails if the name is already taken.
- The repo URL is mutable — repos can move or be renamed. The `name` in the manifest is what ties the repo to the Template record.
- For description, runtimes, required_vars -- the repository is a source of truth.

For the full `pathfinder.yaml` field reference, see [Design](design.md#pathfinderyaml).

## Git Tags as Versions

Git tags on the template repository are the version system. There is no separate version number assigned by Pathfinder — only semver tags are accepted as versions.

Key behaviors:

- Only tags matching semver (`1.2.3` or `v1.2.3-test`) are accepted. Non-semver tags are ignored.
- When creating a service, the operator selects a version (git tag) from the available list.
- Pathfinder reads `pathfinder.yaml` at the selected tag's commit SHA (not HEAD). This ensures the manifest matches the tagged code snapshot.
- Scaffolding uses the file tree at the selected tag's commit SHA.
- Pathfinder presents tags in reverse semver order (newest first).

### Tag Validation on Webhook

When a tag-push webhook fires, Pathfinder validates the tag before adding it as a version:

1. **Semver format** — Tag must match semver.org regex. Non-matching tags are ignored.
2. **Main branch ancestry** — The tagged commit must be reachable from main. Verified with `git merge-base --is-ancestor <tagged-sha> origin/main`. Tags pointing to commits not on main are rejected.

This is a generic Git operation that works across all providers without SCM API calls. Provider-side tag protection rules (where available) serve as defense in depth, but the application-side check is the universal source of truth.

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

A template with no semver tags has only HEAD as its version source. Operators are encouraged to tag releases to give users stable, selectable versions.

## Sync

Operators can trigger a manual sync on a registered template to refresh its metadata and version list. Automatic sync happens on webhook event.

**What sync does:**

1. Re-fetches the repository from the git URL.
2. Reads `pathfinder.yaml` from HEAD of the default branch.
3. Updates the Template record metadata (description, runtimes, required_vars) from the manifest.
4. Fetches the current git tag list -- new tags are added as available versions.
5. Tags that no longer exist on the remote are not automatically removed (they remain visible but are flagged as unavailable).

**What sync does NOT do:**

- Does not automatically retrigger scaffolding for existing services.
- Does not push updates to existing service repos.
- Does not auto-update services that were created from earlier versions.

Sync is a metadata refresh only. It brings Pathfinder's view of the template up to date with the remote repository. Services created from earlier versions remain on their original version.

## Template Availability

Templates are available to all Projects by default once registered. Access scoping (restricting templates to specific Projects or teams) is a future concern and not part of the current design.

A template can be deregistered if no service was ever created from it. Deregistering a template that has been used to create services is blocked to preserve scaffolding history and audit traceability.
