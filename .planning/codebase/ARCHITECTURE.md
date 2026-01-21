# Architecture

**Analysis Date:** 2026-01-21

## Pattern Overview

**Overall:** Django monolithic application with planned plugin-based extensibility

**Key Characteristics:**
- Single Django project (`devssp`) with a template-driven wizard UI for service onboarding
- Orchestration pattern: DevSSP acts as control plane, delegates execution to external CI/CD systems
- Two-level integration model: code-defined IntegrationPlugin classes and database-stored IntegrationConnection instances
- Service lifecycle tracked from source code through build artifacts to deployments
- Database-driven with SQLite (single-file, development-focused)
- Gunicorn WSGI application server with 2 workers and 4 threads per worker

## Layers

**Presentation Layer (Views & Templates):**
- Purpose: HTTP request handling, HTML rendering, user interface
- Location: Not yet created (planned: `devssp/templates/`, class-based or function views)
- Contains: Django view functions/classes, template HTML files, static assets (CSS/JS)
- Depends on: Models, Forms (for validation), Integrations
- Used by: HTTP clients, browser
- Entry point: URL routing via `devssp/urls.py`

**Application Logic Layer (Services & Business Logic):**
- Purpose: Orchestration of wizard flows, service creation, build tracking, deployment coordination
- Location: Planned `devssp/services/` or similar (currently not created)
- Contains: Workflow orchestrators, state machine logic for service/build/deployment lifecycle
- Depends on: Models, Integration connections
- Used by: Views, Signals, Background jobs

**Integration Layer (External System Communication):**
- Purpose: Abstract communication with SCM, CI systems, artifact registries, deployment targets
- Location: Planned `devssp/integrations/plugins/` (plugin discovery) and `devssp/integrations/connections/` (management)
- Contains: Plugin base classes, per-plugin implementations (GitHub, Jenkins, Kubernetes, etc.)
- Depends on: Models (IntegrationConnection), external APIs
- Used by: Application logic layer, views
- Design: Plugin registry pattern - scanned at startup from `integrations/plugins/` directory

**Data Access Layer (Models):**
- Purpose: Database schema definition, ORM abstraction
- Location: Planned `devssp/models.py` or `devssp/core/models/` directory
- Contains: Django models for Project, Service, Build, Deployment, Environment, IntegrationConnection, User, Group, Repository
- Depends on: Django ORM, database backend
- Used by: All layers above

**Configuration & Settings:**
- Location: `devssp/settings.py`
- Contains: Django settings, database configuration, middleware, installed apps, static files
- Current state: Minimal - only built-in Django apps, no custom apps registered yet

## Data Flow

**Service Creation (Wizard Flow):**

1. User selects project and service template (Page 1)
2. User configures source code repository and branch (Page 2)
3. User provides deployment-specific configuration (Page 3)
4. User reviews and confirms (Page 4)
5. Wizard handler creates:
   - Service record in database with reference to selected template
   - Repository record tracking external SCM location
   - Calls SCM connection to create/configure repo
   - Creates initial branch with template contents via commit
   - Creates pull request to base branch (if using existing repo)
   - Registers webhook with CI system (if supported)
6. View redirects to service detail page
7. When PR merges → webhook triggers CI build
8. CI build completes → Build record created, artifact reference stored
9. Service transitions from `draft` to `active` status on first successful build
10. If "Deploy Now" was selected → deployment queued as background job

**Deployment Flow:**

1. User selects environment and deployment configuration for a Service
2. Deployment record created in database with environment-specific variables
3. Application logic layer calls appropriate integration connection based on environment's deployment mechanism
4. Connection routes to ArgoCD (GitOps), Docker API, Kubernetes API, or pipeline trigger per mechanism
5. Deployment status tracked via polling or webhooks from external system
6. Build artifacts promoted across environments by artifact reference (no re-build)

**State Management:**

- **Service Status**: Transitions from `draft` → `active` when first successful build completes
- **Build Status**: `pending` → `running` → `success`/`failed`
- **Deployment Status**: Created → queued → deploying → deployed/failed (polling external system)
- Persisted entirely in SQLite database, no in-memory state

## Key Abstractions

**IntegrationPlugin:**
- Purpose: Code-defined integration type representing a capability (GitHub, Jenkins, Kubernetes)
- Examples: `devssp/integrations/plugins/github.py`, `devssp/integrations/plugins/jenkins.py`
- Pattern: Base class with capability declarations, subclasses implement specific operations
- Categories: `scm`, `ci`, `artifact`, `deploy`
- Multi-capability support: GitHub provides SCM + CI (Actions) + Artifacts (Packages)

**IntegrationConnection:**
- Purpose: Database record of a configured plugin instance (e.g., "yourdevops" GitHub org, "prod-eks" Kubernetes cluster)
- Location: Database model definition planned in `devssp/models.py`
- Stores: plugin_name, config (JSON), config_encrypted (sensitive fields), health_status, webhook_token
- Lifecycle: Created by admin/operator, used by application logic to call plugin operations

**Service Handler:**
- Purpose: Composite identifier combining project and service name
- Format: `{project-name}-{service-name}` (max 63 chars total)
- Stored as: Computed field on Service model
- Usage: DNS-compatible identifiers for container names, Kubernetes resources, artifact tags

**Blueprint/Service Template:**
- Purpose: Reusable git repository defining source scaffolding, CI config, deployment metadata
- Identifier: `ssp-template.yaml` manifest in repository root
- Contains: deploy_type (container/serverless/static), required_plugins, CI config, build steps
- Template Availability: Blueprint available to a project if at least one environment has a connection matching required_plugins

**Deployment:**
- Purpose: Instance of a Service deployed to an Environment
- Identifier: `{service_handler}-{env-name}` (max 63 chars total)
- Contains: Environment-specific variables (cascade: Project → Environment → Service → Deployment)
- Lifecycle: Created on-demand, linked to latest Service artifact and Build

## Entry Points

**HTTP Entry Point:**
- Location: `devssp/wsgi.py` (WSGI application)
- Alternative: `devssp/asgi.py` (ASGI for async, currently unused)
- Triggers: Browser requests, CI webhooks
- Responsibilities: Route to views, handle sessions, CSRF protection

**Management Commands:**
- Location: Planned `devssp/management/commands/`
- Examples: `python manage.py migrate`, `python manage.py runserver`
- Entrypoint: `manage.py` CLI wrapper

**Webhooks (CI):**
- Purpose: CI systems post build completion status
- Location: Planned integration-specific webhook handlers (e.g., `devssp/integrations/plugins/github/webhooks.py`)
- Route Pattern: `/integrations/<plugin_name>/<connection_name>/webhook/`
- Triggers: Build record creation, status update

**Django Signals (Async-like):**
- Purpose: Trigger background jobs on model changes
- Location: Planned `devssp/core/signals.py`
- Examples: On successful build → queue deployment job
- Used by: Celery or similar task queue (planned)

## Error Handling

**Strategy:** Django's built-in exception handling with custom error pages and logging

**Patterns:**
- View-level: Try-catch with exception logging, return 400/500 response to client
- Integration-level: Plugin method raises custom exception (e.g., `GitHubRepoNotFound`), application logic catches and logs, sets IntegrationConnection.status to `error` and last_error text
- Wizard-level: Form validation errors displayed inline, step can be retried; on repository operation failure, Service created anyway with warning message shown
- Background jobs: Task failure logged, retry queued (Celery retry mechanism planned)

## Cross-Cutting Concerns

**Logging:** Python `logging` module (planned centralization in `devssp/logging.py`). Entrypoint logs major lifecycle events: service creation, build trigger, deployment start. Integration layer logs API calls and errors.

**Validation:** Django Forms for user input validation (wizard steps), model-level validators for name format (DNS-compatible), Integration plugin has schema validation for configuration fields.

**Authentication:** Django's built-in User model and session middleware. Views check `request.user.is_authenticated`. Custom permission checks planned for RBAC (Project roles: owner, contributor, viewer; System roles: admin, operator, auditor).

**CSRF Protection:** Django middleware (enabled by default), CSRF token in all POST forms.

**Secrets Management:** Environment variables for sensitive config (DATABASE_URL, API keys). `config_encrypted` JSON field in IntegrationConnection for storing sensitive connection details (encrypted with Fernet key from env var).

---

*Architecture analysis: 2026-01-21*
