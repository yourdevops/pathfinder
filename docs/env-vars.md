# Variable Lifecycle

Environment variables in Pathfinder follow a cascade model. Variables are defined at multiple levels and merged at resolution time, with lower levels overriding higher levels — unless the higher level locked the variable.

## The Cascade

```
System (PTF_* variables, always locked)
  └── Project
    └── Service
      └── Environment
        └── Deployment (future)
```

At resolution time (build authorization, deployment gate), variables merge top-down. Each level can add new variables or override values from the level above — unless the upstream variable is locked.

## Variable Shape

Every variable at every level has the same structure:

```json
{"key": "DATABASE_URL", "value": "postgres://...", "lock": false, "description": "PostgreSQL connection string"}
```

- `key` — required. The variable name. Must match `^[A-Z][A-Z0-9_]*$` (uppercase letters, digits, underscores; must start with a letter).
- `value` — required (may be empty string). The variable value.
- `lock` — required. Boolean, prevents downstream override when true.
- `description` — optional. Human-readable explanation of what the variable is for. Shown as helper text in the UI. When a template declares `required_vars`, the description strings from the manifest are carried into this field. Description is stored per-level alongside the variable — when a downstream level overrides a variable's value, it inherits the upstream description unless the downstream level provides its own.

Three valid states for a variable:

| State | Meaning | Example |
|-------|---------|---------|
| Key + Value | Default value, overridable downstream | `DATABASE_URL=postgres://localhost/dev` |
| Key + Value + Lock | Fixed value, not overridable downstream | `LOG_FORMAT=json` (locked) |
| Key only (empty value) | Variable is needed — must be provided at a lower level | `DATABASE_URL=` |

An empty-string value means "not yet provided." This keeps the model simple with no extra `required` boolean.

## System-Injected Variables

Pathfinder injects variables with the `PTF_` prefix. These are always locked and cannot be removed or overridden.

| Variable | Scope | Value |
|----------|-------|-------|
| `PTF_PROJECT` | Project | Project name |
| `PTF_SERVICE` | Service | The Service's name |
| `PTF_ENVIRONMENT` | Environment | Environment name |

## Where Variables Come From

### At service creation (wizard)

1. Project-level variables are shown for awareness (read-only in the wizard, on top).
2. `PTF_SERVICE` is injected automatically (locked).
3. If a template was selected and declares `required_vars`, those are seeded as service-level variables with keys pre-filled and values empty. Info note - "You can leave values empty now -- operator will be asked to fill these values on specific Deployment Environment level".
4. The operator fills in values if needed, adjusts lock state, removes unneeded vars, or adds new ones.

After the wizard completes, all variable data lives in Pathfinder's database. There is no manifest file in the service repository.

### After service creation

Variables are managed through the Pathfinder UI at the appropriate level:

- **Project settings** — variables shared across all services and environments in the project.
- **Service settings** — variables specific to a service (override project-level unless locked).
- **Environment detail** — variables specific to an environment (override project/service-level unless locked).

## Override Rules

When resolving the full variable set for a given context:

1. Start with system-injected variables (always locked).
2. Layer in Project variables.
3. Layer in Service variables (override Project, unless upstream locked the variable).
4. Layer in Environment variables (override Project/Service, unless upstream locked).
5. (Future) Layer in Deployment variables.

A **locked** variable cannot be overridden by any downstream level. The downstream level sees it (read-only) but cannot change the value.

### Example

```
Project defines:
  PTF_PROJECT=acme                     (system, locked)
  LOG_FORMAT=json                      (locked)
  DATABASE_URL=postgres://dev-shared   (unlocked)

Service "order-service" defines:
  PTF_SERVICE=order-service            (system, locked)
  REDIS_URL=redis://cache:6379         (unlocked)

Environment "staging" defines:
  PTF_ENVIRONMENT=staging              (system, locked)
  DATABASE_URL=postgres://staging-db   (unlocked)
  LOG_LEVEL=info

Resolved for order-service in staging:
  PTF_PROJECT=acme                     ← system (locked)
  PTF_SERVICE=order-service            ← system (locked)
  PTF_ENVIRONMENT=staging              ← system (locked)
  LOG_FORMAT=json                      ← project (locked, cannot override)
  LOG_LEVEL=info
  DATABASE_URL=postgres://staging-db   ← environment overrides project
  REDIS_URL=redis://cache:6379         ← service
```

## Deployment Gate

Before deployment, Pathfinder resolves the full variable set for the target context and checks for unsatisfied variables — keys with empty values that were never filled at any level.

```
Resolve full variable set for deployment context
        |
        v
Any variables with empty values?
   |             |
  NO             YES
   |             |
   v             v
Deployment    Deployment BLOCKED
allowed       UI shows list of
              variables that
              need values
```

The deployment gate is hard — there is no override or bypass. The operator must configure values for all empty variables before deployment can proceed.

The gate applies at deploy time, not at build time. Builds always complete. This means a developer can add new service variables, have the build succeed, and the operator resolves missing values before deploying.

## Adding and Removing Variables

### Adding a variable

An operator adds a variable at any level through the Pathfinder UI. If the variable has no value (key-only), it signals that a downstream level must provide the value before deployment.

### Removing a variable

An operator removes a variable through the Pathfinder UI at the level where it was defined. Removing a variable at one level does not affect the same key at other levels.

### Stale variables

When a variable is no longer needed by a service (e.g., after a code change removes usage of `REDIS_URL`), the operator removes it from the service's variable list in Pathfinder. There is no automatic detection of stale variables — the operator manages the variable list as part of service maintenance.
