# Pathfinder - Developer Self-Service Portal

Pathfinder is a lightweight internal developer platform that turns your existing templates and CI/CD into governed, self-service workflows. It gives developers fast golden paths while giving platform teams consistent policy enforcement and audit visibility.

## Quick Start

### Running Locally (without containers)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
cd theme/static_src && npm install

# Rebuild UI
uv run python manage.py tailwind build

# Collect static files
uv run python manage.py collectstatic

# Run database migrations
uv run python manage.py migrate

# Start development server
make run
```

The portal will be available at **http://localhost:8000**
