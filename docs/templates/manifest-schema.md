# Manifest Schema

`pathfinder.yaml` is a single file that identifies a repository as either a reusable template or a running service. Pathfinder reads it from the repository root. The `kind` field determines which fields apply and how Pathfinder behaves toward the repository.

## Overview

One file serves two purposes. In a template repository, `pathfinder.yaml` with `kind: template` declares metadata that Pathfinder reads during registration and version discovery. In a service repository, `pathfinder.yaml` with `kind: service` declares the variables and runtimes that Pathfinder reads at every build to enforce deployment requirements.

Scaffolding transforms the file: when a service is created from a template, `kind: template` becomes `kind: service` and `name` is set to the service handler name. After that point, the manifest travels with the service repository and is re-read on every build webhook at the commit SHA of that build.

## Top-Level Fields

| Field | Required | Applies To | Description |
|-------|----------|------------|-------------|
| `kind` | Yes | All | Identifies the repo type: `"template"` or `"service"`. Extensible for future kinds. |
| `name` | Yes | All | DNS-compatible identifier. For `kind: service`, matches the service name in Pathfinder and is used for correlation at build time. |
| `description` | No | All | Human-readable description shown in the Pathfinder UI. |
| `runtimes` | No | All | List of runtime constraints used to recommend compatible CI Workflows. See [Runtimes](#runtimes). |
| `required_vars` | No | All | Map of variable declarations required for deployment. See [Required Variables](#required-variables). |

### Field Rules

- `kind` accepts only `"template"` or `"service"` in the current schema version.
- `name` must be a valid DNS label: lowercase alphanumeric characters and hyphens, starting with a letter or digit, maximum 63 characters.
- All other fields are optional. A minimal valid manifest needs only `kind` and `name`.

## kind: template

A manifest with `kind: template` identifies the repository as a template available for scaffolding. Pathfinder reads this file when an operator registers the template and again at each tagged version to discover metadata.

All top-level fields apply. The `runtimes` field is used during scaffolding to recommend compatible CI Workflows. The `required_vars` field tells Pathfinder which environment variables the scaffolded service will need.

### Example

```yaml
kind: template
name: python-fastapi
description: "FastAPI service with async PostgreSQL and Redis"
runtimes:
  - python: ">=3.11"
required_vars:
  DATABASE_URL: "PostgreSQL connection string (asyncpg format)"
  SECRET_KEY: "Application secret key for JWT signing"
  REDIS_URL: "Redis connection string for caching"
```

## kind: service

A manifest with `kind: service` identifies the repository as a running service managed by Pathfinder. Pathfinder reads this file at every build webhook at the commit SHA of that build to discover required variables and enforce deployment gates.

Scaffolded repos always have `pathfinder.yaml` with `kind: service` -- scaffolding transforms the template's `kind: template` into `kind: service` and sets `name` to the service handler name. See [Scaffolding](scaffolding.md).

The `runtimes` field in `kind: service` is informational only -- runtimes are not re-evaluated after scaffolding. CI Workflow assignment is managed separately in service settings.

### Example

```yaml
kind: service
name: order-service
description: "Order processing microservice"
runtimes:
  - python: ">=3.11"
required_vars:
  DATABASE_URL: "PostgreSQL connection string (asyncpg format)"
  SECRET_KEY: "Application secret key for JWT signing"
  REDIS_URL: "Redis connection string for caching"
```

## Runtimes

The `runtimes` field is a YAML list where each entry is a single-key map of runtime name to semver constraint string.

```yaml
runtimes:
  - python: ">=3.11"
  - node: ">=20"
```

Runtimes are used exclusively to recommend compatible CI Workflows during scaffolding and in the service settings UI. They do not select a CI Workflow -- the CI Workflow is assigned separately by the operator. They do not enforce runtime versions at build time. Concrete runtime version selection (e.g., Python 3.12 specifically) happens at the CI Workflow level via step configuration.

If `runtimes` is absent or empty, no runtime-based filtering applies to CI Workflow recommendations.

### Constraint Format

Each constraint is a semver-style string. Supported operators:

| Operator | Meaning | Example |
|----------|---------|---------|
| `>=` | Minimum version (inclusive) | `">=3.11"` |
| `>=,<` | Range | `">=3.11,<4.0"` |
| (exact) | Exact version | `"3.12"` |

## Required Variables

The `required_vars` field is a map where keys are variable names and values are description strings.

```yaml
required_vars:
  DATABASE_URL: "PostgreSQL connection string (asyncpg format)"
  SECRET_KEY: "Application secret key for JWT signing"
  REDIS_URL: "Redis connection string for caching"
```

### Design Decisions

- `required_vars` contains only declarations: a variable name and its description. It does not contain values.
- No types, no defaults, no required flags. Every declared variable is implicitly required.
- Variable names follow the convention of uppercase letters with underscore separators (e.g., `DATABASE_URL`), though this is a convention, not enforced by the schema.
- If `required_vars` is absent or empty, no variable enforcement applies.

### Two-System Separation

The manifest and Pathfinder's environment variable system serve different purposes:

| Concept | What It Stores | Where It Lives | Who Manages It |
|---------|---------------|----------------|----------------|
| `required_vars` (manifest) | Variable names and their descriptions | `pathfinder.yaml` in the repo | Template author / service developer |
| `env_vars` (Pathfinder) | Variable values for each environment | Pathfinder database | Operator / platform team |

The manifest declares WHAT variables are needed. Pathfinder's `env_vars` system provides the VALUES. These are separate systems -- the manifest never contains values, and `env_vars` entries do not contain requirement declarations.

For how Pathfinder enforces `required_vars` at deployment time, see [Variable Lifecycle](variable-lifecycle.md). For how operators register templates and manage versions, see [Template Registration](template-registration.md).

## Extensibility

The `kind` field is designed to be extensible. A future `kind: component` is planned for IaC component templates (databases, queues, storage, etc.) but is not defined in this version of the schema. Only `kind: template` and `kind: service` are recognized.

Unrecognized `kind` values are treated as an error during manifest parsing.

## File Location and Naming

`pathfinder.yaml` must be in the repository root. The canonical extension is `.yaml`. The `.yml` extension is also accepted. If both `pathfinder.yaml` and `pathfinder.yml` are present, `pathfinder.yaml` takes precedence.

```
repo-root/
  pathfinder.yaml    <-- Pathfinder reads this file
  src/
  tests/
  ...
```
