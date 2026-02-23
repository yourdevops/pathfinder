# Templates

A Template is a versioned git repository that defines a reusable service scaffold. Templates carry a `pathfinder.yaml` manifest (`kind: template`) that declares the service's name, required variables, and runtimes. When an operator creates a service from a template, Pathfinder scaffolds a new repository from the template's file tree and transforms the manifest to `kind: service` -- making the service self-describing. Pathfinder re-reads `pathfinder.yaml` at every build to keep variable requirements current.

## What Templates Do Not Do

- Define CI Workflows -- CI pipeline composition is a [CI Workflows](../ci-workflows/README.md) concern
- Inject CI steps, generate CI manifests, or select a CI engine
- Manage runtime version selection for builds -- runtimes in `pathfinder.yaml` are a hint for CI Workflow recommendation only; concrete version selection happens in the CI Workflow
- Auto-discover templates from connected repositories -- registration is manual
- Define component or infrastructure templates (databases, queues, etc.) -- that is a future concern
- Contain variable values -- `pathfinder.yaml` declares what variables a service needs; values are configured in Pathfinder's `env_vars` system

## Documentation

| Document | Description |
|----------|-------------|
| [Manifest Schema](manifest-schema.md) | `pathfinder.yaml` field reference for templates and services |
| [Variable Lifecycle](variable-lifecycle.md) | How `required_vars` are detected, enforced, and cleaned up at build time |
| [Scaffolding](scaffolding.md) | Full wizard flow from template selection to running service repo |
| [Template Registration](template-registration.md) | Registering templates, git tags as versions, and sync |
| [Examples](examples.md) | Complete `pathfinder.yaml` samples for common service stacks |

---

## Quick Reference

### Manifest Kind Values

| Kind | Used In | What Pathfinder Does |
|------|---------|----------------------|
| `template` | Template repositories | Reads on registration and version sync; used in scaffolding wizard |
| `service` | Scaffolded service repos | Reads at every build webhook to discover required variables |

### Variable States

| State | Meaning | Deployment |
|-------|---------|------------|
| Satisfied | Declared in manifest; value exists in `env_vars` | Allowed |
| Unsatisfied | Declared in manifest; no value in `env_vars` | Blocked |
| Stale | Previously declared; removed from manifest; value still in `env_vars` | Allowed (cleanup recommended) |

### Quick Definitions

| Term | Definition |
|------|------------|
| `pathfinder.yaml` | Manifest file in the repo root; identifies the repo as a template or service |
| `required_vars` | Variable declarations (name + description only) -- not values |
| `env_vars` | Variable values configured in Pathfinder -- the existing cascade system |
| git tag | A version of a template -- each tag is a selectable option in the wizard |
| Scaffolding | The process of creating a service repo from a template; transforms `kind: template` to `kind: service` |
