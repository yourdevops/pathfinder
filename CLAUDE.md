# Pathfinder DevSSP - Agent Instructions
Pathfinder DevSSP (Developer Self-Service Portal) is a Django web app for managing SDLC via a wizard-based UI.

**Project Docs**: docs/ directory

**Django Documentation**: use context7 MCP to look up the Django documentation

**Stack**: Django 6.x, SQLite, Docker/Podman, Gunicorn

**Package Management**: uv (pyproject.toml + uv.lock). Do NOT use pip or requirements.txt.

**No Backwards Compatibility Required**: This project is in early development stage. There is no need to maintain backwards compatibility for any features. When refactoring, feel free to remove deprecated code, change database schemas, and break existing functionality if it leads to a cleaner implementation.

## Architecture Rules

1. **Core code must be plugin-agnostic.** All SCM-plugin-specific logic (GitHub, GitLab, etc.) lives exclusively in `plugins/`. Core code interacts with SCM only through the plugin interface — never import or call provider-specific APIs from `core/`.

2. **Prefer generic Git operations over SCM API calls.** Use Git protocol commands (`git ls-remote`, `git clone`, `git fetch` over SSH/HTTPS) instead of provider REST/GraphQL APIs whenever possible. Git operations have separate, more generous rate limits and work identically across providers. Reserve API calls for operations that have no Git-protocol equivalent (e.g., creating PRs, managing webhooks).

## Local run
When running locally, use uv (no manual venv activation needed):
```bash
# Install/sync dependencies
make sync

# Rebuild UI & Collect static files
make build

# Run
make run
```

**USE Makefile** commands to run/restart app locally

**First run**: Navigate to http://localhost:8000/, paste unlock token from `secrets/initialUnlockToken`, create admin account with the following credentials:
- **Username**: `admin`
- **Password**: `AdminPass123!`
