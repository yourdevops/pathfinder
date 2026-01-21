# External Integrations

**Analysis Date:** 2026-01-21

## APIs & External Services

**Source Control (SCM):**
- GitHub, BitBucket, GitLab, Gitea - Planned integration plugins
  - Capabilities: list repos, clone, create repos/branches, commit, push, create PRs, webhooks
  - Reference: `docs/integrations.md`

**CI/CD Systems:**
- Jenkins, GitHub Actions, GitLab CI - Planned integration plugins
  - Capabilities: trigger builds, get build status, cancel builds, get logs, list workflows
  - Reference: `docs/integrations.md`

**Container/Artifact Registries:**
- ECR, Docker Hub, Nexus, GitHub Packages, S3 - Planned integration plugins
  - Capabilities: push/pull images, list tags, delete tags
  - Reference: `docs/integrations.md`

**Deployment Targets:**
- ArgoCD (GitOps), Docker, Kubernetes, SSH Hosts - Planned integration plugins
  - Capabilities: deploy, get status, rollback, get logs, list resources
  - Reference: `docs/integrations.md`

## Data Storage

**Databases:**
- SQLite3 (django.db.backends.sqlite3)
  - Location: `db.sqlite3` (file-based, project root)
  - Connection: Local file
  - Client: Django ORM built-in

**File Storage:**
- Local filesystem only (current state)
  - Manifests directory: `manifests/` (mounted via docker-compose volume)
  - Data directory: `ssp-data` (Docker named volume)

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- Custom - Built-in Django authentication system
  - Implementation: Django contrib.auth with standard password validators
  - Session-based authentication via Django middleware
  - Initial unlock token-based admin account creation (`secrets/initialUnlockToken`)

**User Management:**
- Django admin interface for user/group management
- Role-Based Access Control (RBAC) planned - documented in `docs/rbac.md`

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Standard output (logs visible via `docker logs ssp-portal`)
- Log files: `*.log` (gitignored in `.gitignore`)
- Entrypoint provides status messages during startup

**Health Checks:**
- HTTP health check: GET `http://localhost:8000/`
  - Interval: 30 seconds
  - Timeout: 10 seconds
  - Retries: 3
  - Start period: 5-10 seconds (Dockerfile vs docker-compose)
  - Implementation: Python urllib request check

## CI/CD & Deployment

**Hosting:**
- Docker/Podman containers
- Deployment: Traefik reverse proxy integration
  - Domain: `ssp.yourdevops.me` (from docker-compose.yml labels)
  - TLS: Enabled

**CI Pipeline:**
- None detected (project in early development stage)

**Container Orchestration:**
- Docker socket mounted (`/var/run/docker.sock:ro`)
  - Purpose: Container management from within application
  - Access: Read-only mounting with group_add for DOCKER_GID

## Environment Configuration

**Required env vars:**
- `DJANGO_SECRET_KEY` - Required for production (must override default)
- `DJANGO_DEBUG` - Should be False in production
- `DJANGO_ALLOWED_HOSTS` - Comma-separated host list
- `CSRF_TRUSTED_ORIGINS` - Comma-separated origin list
- `SSP_PUBLIC_URL` - Public-facing URL for the portal
- `DOCKER_GID` - Docker group ID if using container management features

**Optional env vars:**
- `SSP_DATA_DIR` - Data directory (default: /app/data)

**Secrets location:**
- Secrets directory: `secrets/` (git-ignored)
  - Initial unlock token: `secrets/initialUnlockToken` (referenced in CLAUDE.md)
- Environment variables: docker-compose.yml or external .env files
- Django secret key: Hardcoded default in settings.py (MUST be overridden in production)

## Webhooks & Callbacks

**Incoming:**
- Not yet implemented (planned capability in integration plugins)
- Reference: `docs/integrations.md` lists `webhooks` as SCM capability

**Outgoing:**
- Not yet implemented

## Network & Reverse Proxy

**Traefik Integration:**
- Reverse proxy labels configured in docker-compose.yml:
  - Router: `ssp`
  - Host rule: `Host('ssp.yourdevops.me')`
  - TLS: Enabled
  - Service port: 8000

**Networking:**
- External Docker network: `yourdevops_public`
- Port mapping: 8000:8000 (localhost in dev, Traefik in prod)

## Security Configuration

**CSRF Protection:**
- CsrfViewMiddleware enabled
- Trusted origins configurable via `CSRF_TRUSTED_ORIGINS`

**Security Middleware:**
- SecurityMiddleware (Django built-in)
- XFrameOptionsMiddleware (clickjacking protection)

**Database:**
- SQLite3 suitable for development/testing only
- Consider PostgreSQL for production deployments

## Docker Socket Access

**Purpose:** Container management from within the application

**Configuration:**
- Volume: `/var/run/docker.sock:/var/run/docker.sock:ro`
- Access method: Docker group membership (via group_add)
- Requires: DOCKER_GID environment variable matching host Docker group

---

*Integration audit: 2026-01-21*
