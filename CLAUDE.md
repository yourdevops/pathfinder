# SSP - Agent Instructions
Pathfinder (Developer Self-Service Portal) is a Django web app for managing container deployments via a wizard-based UI.

**Project Docs**: docs/ directory

**Django Documentation**: use context7 MCP to look up the Django documentation

**Stack**: Django 6.x, SQLite, Docker/Podman, Gunicorn

**Package Management**: uv (pyproject.toml + uv.lock). Do NOT use pip or requirements.txt.

**No Backwards Compatibility Required**: This project is in early development stage. There is no need to maintain backwards compatibility for any features. When refactoring, feel free to remove deprecated code, change database schemas, and break existing functionality if it leads to a cleaner implementation.

When running locally, use uv (no manual venv activation needed):
```bash
# Install/sync dependencies
uv sync

# Rebuild UI
uv run python manage.py tailwind build

# Collect static files
uv run python manage.py collectstatic
```

**USE Makefile** commands to run/restart app locally

**First run**: Navigate to http://localhost:8000/, paste unlock token from `secrets/initialUnlockToken`, create admin account with the following credentials:
- **Username**: `admin`
- **Password**: `AdminPass123!`
