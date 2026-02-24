# Architecture

**Analysis Date:** 2026-02-24

## Pattern Overview

**Overall:** Django monolith with a plugin-based extension system and background task processing

**Key Characteristics:**
- Single `core` Django app owns all domain models, views, forms, tasks, and business logic
- Plugins in `plugins/` extend core via a formal `BasePlugin` / `CICapableMixin` contract — core never imports from a specific plugin implementation
- Background task processing via `django-tasks` database-backed queue with a separate `db_worker` process
- Real-time UI updates via Django Channels WebSockets (polling-based state-diff on `ServiceConsumer`, not pub/sub)
- HTMX + Alpine.js CSP build for all interactive frontend — no SPA framework
- Import contracts enforced by `import-linter` at lint time (configured in `pyproject.toml`)
- Three deployment processes: web server (Gunicorn + Uvicorn), worker (`db_worker`), scheduler (`run_task_scheduler`)

---

## Layers

**Configuration Layer:**
- Purpose: Django project settings, root URL routing, ASGI/WSGI entrypoints
- Location: `pathfinder/`
- Contains: `settings.py`, `urls.py`, `asgi.py`, `wsgi.py`
- Depends on: `core`, `plugins`
- Used by: Django runtime, Gunicorn

**Core App:**
- Purpose: All domain models, views, forms, tasks, permissions, and business logic
- Location: `core/`
- Contains: `models.py` (all domain models), `views/` (one module per feature area), `forms/` (form classes per feature), `tasks.py` (all background tasks), `permissions.py`, `middleware.py`, `consumers.py` (WebSocket), `git_utils.py`, `ci_manifest.py`, `encryption.py`, `context_processors.py`, `decorators.py`, `utils.py`, `validators.py`
- Depends on: `plugins.base` (interface only — never `plugins.github` or `plugins.docker` directly)
- Used by: `pathfinder/urls.py`, `pathfinder/asgi.py`

**Plugin Layer:**
- Purpose: Provider-specific integrations (SCM, CI engines, deploy targets)
- Location: `plugins/`
- Contains: `base.py` (registry + abstract base classes + `CICapableMixin`), `github/` (GitHub App integration), `docker/` (Docker integration)
- Depends on: External SDKs (PyGithub, docker-py); may import from `core.models` and `core.tasks`
- Used by: Core views that resolve plugins via `plugins.base.registry.get(name)`

**Theme Layer:**
- Purpose: Tailwind CSS build pipeline and global base HTML template
- Location: `theme/`
- Contains: `static_src/` (npm/Tailwind sources), `static/css/dist/` (compiled CSS), `static/js/vendor/` (Alpine.js, HTMX vendor files), `templates/base.html`
- Depends on: Nothing (import-linter forbids theme importing from core or plugins)
- Used by: Django template engine via `APP_DIRS = True`

---

## Data Flow

**HTTP Request:**

1. Request enters `pathfinder/asgi.py` via Gunicorn + Uvicorn worker
2. Middleware stack runs in order: `SecurityMiddleware` → `WhiteNoiseMiddleware` → `ContentSecurityPolicyMiddleware` → `SessionMiddleware` → `HtmxMiddleware` → `CommonMiddleware` → `CsrfViewMiddleware` → `SetupMiddleware` → `AuthenticationMiddleware` → `AuditlogMiddleware` → `MessageMiddleware` → `XFrameOptionsMiddleware`
3. `SetupMiddleware` (`core/middleware.py`) enforces setup flow — all traffic redirects to `/setup/unlock/` until an admin account is created and the unlock token is deleted
4. URL router (`pathfinder/urls.py`) dispatches to a view in `core/views/`; class-based views use permission mixins from `core/permissions.py`
5. Views query `core/models.py` via Django ORM, resolve plugins through `registry.get(name)` when integration is needed, enqueue background tasks via `task_function.enqueue(...)`
6. Templates (Django template language) use HTMX for partial updates; Alpine.js CSP build for reactive UI state

**WebSocket Real-Time Updates:**

1. Client opens WebSocket to `ws/services/<service_id>/` (defined in `core/routing.py`)
2. `pathfinder/asgi.py` routes WebSocket connections through `AllowedHostsOriginValidator` → `AuthMiddlewareStack` → `URLRouter` → `ServiceConsumer`
3. `ServiceConsumer` (`core/consumers.py`) polls the database every 3 seconds via `@database_sync_to_async`
4. On state change (detected via SHA-256 hash of fetched data), renders HTMX partials server-side with `render_to_string` and pushes raw HTML to client
5. Client receives HTML and HTMX OOB-swaps it into the DOM

**Background Task Flow:**

1. Views or plugin webhooks enqueue tasks via `task_function.enqueue(...)` or `task_function.using(run_after=timedelta(...)).enqueue(...)`
2. Tasks stored as database rows via `django-tasks` `DatabaseBackend`
3. `db_worker` process (`python manage.py db_worker --queue-name "*"`) dequeues and executes tasks
4. Cron tasks triggered by `scheduler` process (`python manage.py run_task_scheduler`)
5. Queues and their purpose:
   - `default`: general tasks (`auto_update_services`, `scheduled_cleanup_versions`)
   - `health_checks`: `check_connection_health`, `schedule_health_checks`
   - `repository_scaffolding`: `scaffold_repository`, `push_ci_manifest`
   - `steps_scan`: `scan_steps_repository`, `sync_template`, `cleanup_archived_steps`, `scheduled_scan_all_steps_repos`
   - `build_updates`: `verify_build`, `poll_build_details`

**Plugin Webhook Flow (GitHub):**

1. GitHub sends POST to `/integrations/github/webhook/`
2. Plugin URL patterns dynamically registered at startup via `autodiscover()` in `pathfinder/urls.py` from `registry.all()`
3. `plugins/github/webhooks.py` verifies HMAC-SHA256 signature (`X-Hub-Signature-256`), parses event type
4. Identifies the affected `Service` via payload data, looks up matching `Build` or creates one
5. Enqueues core tasks (`verify_build`, `poll_build_details`) to process build status asynchronously

**Environment Variable Cascade:**

1. `resolve_env_vars(project, service, environment)` in `core/utils.py` merges variables
2. Resolution order (top to bottom; locked upstream blocks override): system PTF_* vars → project vars → service vars → environment vars
3. System-injected vars (`PTF_PROJECT`, `PTF_SERVICE`, `PTF_ENVIRONMENT`) are always locked and cannot be overridden

---

## Key Abstractions

**BasePlugin / PluginRegistry:**
- Purpose: Formal contract for all integration plugins; singleton class-level registry for discovery
- Location: `plugins/base.py`
- Pattern: `BasePlugin` is an ABC with `@abstractmethod` for `get_config_schema()`, `health_check()`, `get_urlpatterns()`, `get_wizard_forms()`; `PluginRegistry` is a class with a `_plugins` dict; `autodiscover()` in `plugins/__init__.py` scans the `plugins/` directory on startup
- Key methods: `get_clone_credentials()`, `get_webhook_url()`, `is_sensitive_field()`

**CICapableMixin:**
- Purpose: Extension mixin for plugins that also provide CI engine capabilities
- Location: `plugins/base.py`
- Pattern: Non-abstract mixin with `raise NotImplementedError` guards; implemented by `GitHubPlugin`
- Key methods: `generate_manifest()`, `parse_step_file()`, `map_run_status()`, `resolve_artifact_ref()`, `provision_ci_variables()`, `check_branch_protection()`, `format_step_id()`, `format_output_reference()`

**IntegrationConnection (encrypted config storage):**
- Purpose: Database record of a configured plugin instance with transparent field-level encryption
- Location: `core/models.py`
- Pattern: `set_config(full_config)` splits fields into sensitive/non-sensitive using `plugin.is_sensitive_field()`, encrypts sensitive fields with Fernet; `get_config()` decrypts and merges; plaintext fields in `config` (JSONField), encrypted in `config_encrypted` (BinaryField)

**Project Permission Hierarchy:**
- Purpose: Enforce project-scoped access control in class-based views
- Location: `core/permissions.py`
- Pattern: Three permission mixins — `ProjectViewerMixin`, `ProjectContributorMixin`, `ProjectOwnerMixin` — each setting `required_role`; system roles `admin`/`operator` always resolve to project `owner` access; roles flow through `Group.system_roles` (JSONField) via `GroupMembership`
- System-level guards: `AdminRequiredMixin`, `OperatorRequiredMixin`, `IntegrationsReadMixin` in `core/permissions.py`; `admin_required` / `operator_required` decorators in `core/decorators.py`

**Background Tasks (`core/tasks.py`):**
- Purpose: All long-running operations off the request cycle
- Location: `core/tasks.py`
- Pattern: Functions decorated with `@task(queue_name=...)` from `django-tasks`; enqueued via `.enqueue()` from views or other tasks; never called synchronously in the request path
- Key tasks: `scaffold_repository`, `push_ci_manifest`, `scan_steps_repository`, `sync_template`, `check_connection_health`, `verify_build`, `poll_build_details`, `auto_update_services`

**CIWorkflow / Version Lifecycle:**
- Purpose: Composed CI pipeline definition with versioned, SHA-256-hashed manifests for build authorization
- Location: `core/models.py` — `CIWorkflow`, `CIWorkflowStep`, `CIWorkflowVersion`, `Build`
- Pattern: `CIWorkflow` composed of ordered `CIWorkflowStep` records linking to `CIStep`s; publishing creates an immutable `CIWorkflowVersion` with SHA-256 `manifest_hash` and stored `manifest_content`; `Build` records link to their `workflow_version` for verification; revoked versions invalidate associated builds

**SiteConfiguration (singleton):**
- Purpose: Site-wide settings stored in database, not environment variables
- Location: `core/models.py`
- Pattern: `save()` always sets `pk = 1`; accessed via `SiteConfiguration.get_instance()`; stores `external_url` (for webhooks), `version_retention_days`

---

## Entry Points

**HTTP / WebSocket (ASGI):**
- Location: `pathfinder/asgi.py`
- Triggers: Gunicorn with Uvicorn worker class (`entrypoint.sh`)
- Responsibilities: Routes HTTP requests to Django WSGI app; routes WebSocket connections through `AuthMiddlewareStack` + `URLRouter` to `ServiceConsumer`

**Root URL Dispatcher:**
- Location: `pathfinder/urls.py`
- Pattern: Root `""` redirects permanently to `/dashboard/`; all feature URL namespaces defined; plugin URLs dynamically appended under `integrations/<plugin_name>/` from `registry.all()` after `autodiscover()` runs

**Background Worker:**
- Invocation: `python manage.py db_worker --queue-name "*"` (`django-tasks`)
- Deployment: Separate `worker` container in `docker-compose.yml`; started by `make run` dev script
- Responsibilities: Processes all named task queues; health checks, repo scaffolding, CI step scanning, build polling, version lifecycle

**Task Scheduler:**
- Invocation: `python manage.py run_task_scheduler` (`django-scheduled-tasks`)
- Deployment: Separate `scheduler` container in `docker-compose.yml`
- Responsibilities: Cron-based task dispatch — `scheduled_health_checks` (15-min interval), `scheduled_scan_all_steps_repos`, `scheduled_cleanup_versions`

**Setup Flow:**
- Location: `core/middleware.py` (`SetupMiddleware`) + `core/views/setup.py` + `core/utils.py`
- Triggers: Every HTTP request until setup complete
- Responsibilities: On fresh install, generates unlock token at `secrets/initialUnlockToken`; enforces all traffic to `/setup/unlock/`; setup completes when token is deleted and at least one admin user exists in the `admins` group

**Management Commands:**
- Location: `core/management/commands/cleanup_versions.py`
- Invocation: `python manage.py cleanup_versions`

---

## Error Handling

**Strategy:** Django's exception middleware with explicit HTTP responses; status field updates on model records

**Patterns:**
- HTMX views return inline error HTML partials rather than full-page error responses
- Background tasks catch all exceptions, log via `logger.exception()`, update model status fields (e.g., `scaffold_status = "failed"`, `scaffold_error = str(e)`, `health_status = "unhealthy"`)
- Plugin `health_check()` always returns `{"status": "...", "message": "..."}` — never raises to caller
- `IntegrationConnection.get_config()` can raise `cryptography.fernet.InvalidToken` if encryption key changes
- `SetupMiddleware` enforces setup precondition before authentication middleware runs

---

## Cross-Cutting Concerns

**Logging:** Python `logging` module; `core` logger at `DEBUG`, `plugins` logger at `DEBUG`, `django.request` at `ERROR`; all output to stderr/stdout for container log aggregation

**Validation:** `dns_label_validator` in `core/validators.py` applied to all name fields (projects, groups, services, connections, workflows, steps repos, templates); enforces `^[a-z][a-z0-9-]*[a-z0-9]$`, max 63 chars. Custom URL converter `DnsLabelConverter` in `core/converters.py` for slug-based URL parameters

**Authentication:** Django session auth; `LoginRequiredMixin` on all views; session cookie is `HttpOnly`, `Secure` in production; system roles (`admin`, `operator`, `auditor`) resolved through `Group.system_roles` JSONField (not Django's built-in permissions system)

**Audit Logging:** `django-auditlog` registered on `User`, `Group`, `GroupMembership`, `Project`, `Environment`, `ProjectMembership`, `ApiToken`, `SiteConfiguration`; `AuditlogMiddleware` attaches actor to all ORM writes

**Encryption:** Fernet symmetric encryption (`cryptography` library) for sensitive connection config fields; key from `PTF_ENCRYPTION_KEY` env var or auto-generated `secrets/encryption.key` file; `core/encryption.py` provides `encrypt_config()` / `decrypt_config()`

**CSP:** Django 6.x native CSP middleware (`django.middleware.csp.ContentSecurityPolicyMiddleware`); nonce-based `script-src` and `style-src`; Alpine.js CSP build required for all templates; `connect-src` explicitly allows `ws:` and `wss:` for WebSocket connections

**Import Boundaries (enforced by import-linter):**
- `core` must not import from `plugins.github` or `plugins.docker`
- `plugins.github` and `plugins.docker` must not import from each other
- `theme` must not import from `core` or `plugins`

---

*Architecture analysis: 2026-02-24*
