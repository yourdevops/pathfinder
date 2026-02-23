# Variable Lifecycle

`required_vars` in `pathfinder.yaml` are declarations of what environment variables a service needs to run. Pathfinder reads these declarations at every build and enforces that all required variables have values configured before a deployment can proceed.

## Two Systems

The most common point of confusion is conflating the manifest's declarations with Pathfinder's environment variable values. These are separate systems with different owners and different storage.

| System | What It Contains | Where | Who Manages |
|--------|-----------------|-------|-------------|
| `required_vars` (manifest) | Variable names and descriptions -- no values | `pathfinder.yaml` in the service repo | Service developer |
| `env_vars` (Pathfinder) | Variable values per environment | Pathfinder database | Operator / platform team |

Pathfinder enforces that every name declared in `required_vars` has a corresponding value in `env_vars` before allowing deployment. The manifest never contains values.

See [Manifest Schema](manifest-schema.md) for the `required_vars` field format.

## Build-Time Discovery

Pathfinder reads `pathfinder.yaml` at every build webhook. The file is fetched at the build's commit SHA -- not HEAD, not the latest tag -- ensuring that variable requirements match the exact code being built.

```
Build webhook received
        |
        v
Pathfinder fetches pathfinder.yaml
at build's commit SHA from service repo
        |
        v
File present?
   |          |
  NO         YES
   |          |
   v          v
No variable  Parse required_vars
enforcement  from manifest
for this         |
build            v
           Diff against previously
           known required_vars
                 |
        .--------+--------.
        |        |        |
      added   removed  unchanged
        |        |        |
        v        v        v
     Add to   Mark       No
     required  env_vars  action
     list     as stale
        |
        v
Check each added var:
does a value exist in
env_vars cascade?
   |          |
  YES         NO
   |          |
   v          v
  var       var
satisfied  UNSATISFIED
```

If `pathfinder.yaml` is absent from the repo at the build's commit SHA, no variable enforcement applies for that build -- deployment is not blocked by the manifest mechanism. Builds always complete regardless of variable status; enforcement happens at deploy time.

## Deployment Gate

After the build-time read, if any required variable lacks a value in the `env_vars` cascade (project-level or environment-level), the service's deployment is blocked.

```
All required_vars satisfied?
   |             |
  YES            NO
   |             |
   v             v
Deployment    Deployment BLOCKED
allowed       UI shows list of
              missing variables
```

The deployment gate is hard -- there is no override or bypass. The operator must configure values for all missing variables before deployment can proceed.

The gate applies at deploy time, not at build time. Builds always complete. The block is on the subsequent deployment step. This means a developer can push code that adds a new `required_var`, have the build succeed, and then resolve the missing value before deploying.

## Stale Variables

When a variable is removed from `required_vars` in `pathfinder.yaml`, the next build detects the change through the diff against previously known requirements.

```
required_var removed from pathfinder.yaml
        |
        v
Next build reads manifest at new commit SHA
        |
        v
Diff detects: var no longer in required_vars
        |
        v
Existing env_var value kept in database
(not automatically deleted)
        |
        v
UI marks var as "stale / no longer required"
        |
        v
Operator manually removes from env_vars settings
```

Stale variables do not block deployment. The service continues to function. The stale marker is informational -- it prompts the operator to clean up the now-unused value. Pathfinder does not automatically delete configured values because the operator may want to retain them for rollback scenarios or audit purposes.

## No Manifest

If `pathfinder.yaml` is absent from the service repo (e.g., a pre-existing service repository onboarded without scaffolding), no variable enforcement applies. Deployment is not blocked by the manifest mechanism. Pathfinder treats the absence of a manifest as "no required variables declared." Scaffolded repos always have `pathfinder.yaml` because scaffolding creates it (see [Scaffolding](scaffolding.md)).

## Variable States

A required variable exists in one of three states at any point in time:

| State | Meaning | Deployment |
|-------|---------|------------|
| Satisfied | Declared in manifest; value exists in `env_vars` cascade | Allowed |
| Unsatisfied | Declared in manifest; no value in `env_vars` cascade | Blocked |
| Stale | Previously declared; removed from manifest; value still in `env_vars` | Allowed (no gate) |

A variable transitions from Unsatisfied to Satisfied when an operator configures a value in the `env_vars` settings at the project or environment level. A variable transitions from Satisfied to Stale when it is removed from `required_vars` in `pathfinder.yaml` and a subsequent build picks up the change. A stale variable has no effect on the deployment gate.
