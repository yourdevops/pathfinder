# Technology Stack

**Analysis Date:** 2026-01-21

## Languages

**Primary:**
- Python 3.13 - Core application language

**Secondary:**
- Bash - Container entrypoint and deployment scripts
- HTML/CSS - Web UI templates (via Django)

## Runtime

**Environment:**
- Python 3.13 (local development)
- Python 3.13-slim (Docker container)
- WSGI application server: Gunicorn

**Package Manager:**
- pip (Python 3.13)
- Lockfile: Not present (requirements.txt inferred to exist based on Dockerfile)
- Installed packages (as of analysis):
  - Django 6.0.1
  - asgiref 3.11.0
  - sqlparse 0.5.5

## Frameworks

**Core:**
- Django 6.0.1 - Web framework and ORM
  - Includes: Admin interface, auth system, form validation, templates, migrations

**WSGI Server:**
- Gunicorn 2+ (referenced in entrypoint.sh, likely in requirements.txt)
  - Configuration: 2 workers, 4 threads per worker
  - Binding: 0.0.0.0:8000

**Containerization:**
- Docker/Podman - Application container format
- Dockerfile present for both local and production builds
- Docker socket mounted for container management access

## Key Dependencies

**Critical:**
- Django 6.0.1 - Core web framework with built-in admin, ORM, middleware, and security features
- asgiref 3.11.0 - ASGI library for async support
- sqlparse 0.5.5 - SQL parsing utility for migrations and query analysis

**Infrastructure:**
- Gunicorn - WSGI HTTP server for production-like deployment
- pip - Python dependency management

## Configuration

**Environment:**
- Environment variables (via docker-compose or .env files):
  - `DJANGO_DEBUG` - Debug mode toggle (default: False in production)
  - `DJANGO_SECRET_KEY` - Secret key for cryptographic operations
  - `DJANGO_ALLOWED_HOSTS` - Comma-separated allowed hostnames
  - `CSRF_TRUSTED_ORIGINS` - CSRF-exempt origins (comma-separated)
  - `DOCKER_GID` - Docker group ID for socket access

**Build:**
- `Dockerfile` - Multi-stage build (FROM python:3.13-slim)
- `docker-compose.yml` - Docker Compose/Podman Compose configuration
- `.gitignore` - Excludes db.sqlite3, venv/, __pycache__, .env files
- `entrypoint.sh` - Runs migrations and starts Gunicorn on container start

## Django Configuration

**Settings Module:** `devssp.settings`

**Installed Apps:**
- `django.contrib.admin` - Admin interface
- `django.contrib.auth` - Authentication and authorization
- `django.contrib.contenttypes` - Content type framework
- `django.contrib.sessions` - Session management
- `django.contrib.messages` - Messaging framework
- `django.contrib.staticfiles` - Static file serving

**Middleware:**
- SecurityMiddleware
- SessionMiddleware
- CommonMiddleware
- CsrfViewMiddleware
- AuthenticationMiddleware
- MessageMiddleware
- XFrameOptionsMiddleware (clickjacking protection)

**Database:**
- SQLite3 (django.db.backends.sqlite3)
- Location: `db.sqlite3` (project root)
- Migrations applied via `python manage.py migrate`

**Templates:**
- Backend: django.template.backends.django.DjangoTemplates
- Template discovery: APP_DIRS enabled
- Context processors: request, auth, messages

**Static Files:**
- URL: `/static/`
- Collection via `python manage.py collectstatic`
- Output directory: `/app/staticfiles`

**Authentication:**
- Built-in Django auth system
- Password validators: UserAttributeSimilarity, MinimumLength, CommonPassword, Numeric
- Initial admin user creation described in CLAUDE.md (username: admin, password: AdminPass123!)

## Platform Requirements

**Development:**
- Python 3.13 or compatible
- Virtual environment (venv)
- pip for package management
- Unix-like shell (for venv activation)

**Production:**
- Docker or Podman container runtime
- External Docker/Podman daemon (for container management via mounted socket)
- Network access to external services (if integrations configured)
- Storage volume for data persistence (`ssp-data`)
- Network connectivity to `yourdevops_public` Docker network (for Traefik integration)

**Deployment:**
- Host supports Docker socket mounting
- Traefik reverse proxy integration (labels in docker-compose.yml)
- Port 8000 exposed for HTTP (configured for HTTPS via Traefik)

---

*Stack analysis: 2026-01-21*
