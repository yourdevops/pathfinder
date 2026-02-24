# Service Templates

A Template is a versioned git repository that provides a reusable file tree for scaffolding new services. Templates carry a `pathfinder.yaml` manifest that declares metadata — description, runtime hints, and suggested variables. When an operator creates a service from a template, Pathfinder copies the template's files into a new repository, seeds the metadata into its database, and drops the manifest. After scaffolding, Pathfinder's database is the source of truth for all service configuration.

## What Templates Do

- Provide a starting file tree for new service repositories
- Declare runtime hints used to recommend compatible CI Workflows during service creation
- Suggest initial environment variables (names and descriptions) that are seeded into the service record

## What Templates Do Not Do

- Define CI Workflows — CI pipeline composition is a [CI Workflows](../ci-workflows/README.md) concern
- Persist in the service repo after scaffolding — `pathfinder.yaml` is excluded from the scaffolded output
- Enforce variables at build time — variable enforcement is Pathfinder's responsibility, using its database as the source of truth
- Manage runtime version selection for builds — runtimes are a hint for CI Workflow recommendation only
- Auto-discover templates from connected repositories — registration is manual
- Define component or infrastructure templates (databases, queues, etc.) — future concern
- Contain variable values — only names and descriptions

## Documentation

| Document | Description |
|----------|-------------|
| [Design](design.md) | Manifest format, service creation wizard, and unified environment variables model |
| [Template Registration](template-registration.md) | Registering templates, git tags as versions, and sync |
| [Environment Variables](../env-vars.md) | Variable cascade, override rules, and deployment gate |

## Quick Reference

### Quick Definitions

| Term | Definition |
|------|------------|
| `pathfinder.yaml` | Manifest file in the template repo root; declares template metadata |
| `name` | The template's unique identity in Pathfinder — immutable after registration, used as slug and audit reference |
| `required_vars` | Variable declarations in the manifest (name + description) — not values |
| `env_vars` | Variable values stored in Pathfinder's database at each cascade level |
| git tag | A version of a template — each tag is a selectable option in the wizard |
| Scaffolding | Copying a template's file tree into a new repo (excluding the manifest) and seeding metadata into Pathfinder |
