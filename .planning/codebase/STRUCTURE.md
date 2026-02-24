# Codebase Structure

**Analysis Date:** 2026-02-24

## Directory Layout

```
pathfinder/                          # Project root
├── pathfinder/                      # Django project config package
│   ├── settings.py                  # Django settings (apps, middleware, DB, CSP, tasks, caches)
│   ├── urls.py                      # Root URL router + plugin URL autodiscovery
│   ├── asgi.py                      # ASGI entrypoint (HTTP + WebSocket via Channels)
│   └── wsgi.py                      # WSGI entrypoint (fallback, not used in production)
├── core/                            # Core Django app: all domain models, views, tasks
│   ├── models.py                    # All domain models (single file, ~1200 lines)
│   ├── tasks.py                     # All background tasks (~1400 lines)
│   ├── consumers.py                 # WebSocket consumer (ServiceConsumer)
│   ├── routing.py                   # WebSocket URL patterns
│   ├── urls.py                      # All HTTP URL pattern groups
│   ├── views/                       # View modules by feature area
│   │   ├── __init__.py              # Re-exports all views for core/urls.py imports
│   │   ├── api.py                   # API endpoints (step validation)
│   │   ├── audit.py                 # Audit log views
│   │   ├── auth.py                  # Login/logout views
│   │   ├── ci_workflows.py          # CI workflow + steps catalog views
│   │   ├── connections.py           # Integration connection views
│   │   ├── dashboard.py             # Dashboard view
│   │   ├── env_vars.py              # Environment variable bulk-save view
│   │   ├── groups.py                # Group management views
│   │   ├── projects.py              # Project + environment views
│   │   ├── services.py              # Service views + creation wizard
│   │   ├── settings.py              # Settings views (general, user management, etc.)
│   │   ├── setup.py                 # Initial setup / unlock flow views
│   │   ├── templates.py             # Service template views
│   │   └── users.py                 # User management views
│   ├── forms/                       # Django form classes by feature area
│   │   ├── base.py                  # Shared form base classes
│   │   ├── ci_workflows.py          # CI workflow forms
│   │   ├── services.py              # Service creation wizard forms
│   │   └── templates.py             # Template registration forms
│   ├── templates/core/              # Django templates (co-located with app)
│   │   ├── audit/                   # Audit log templates
│   │   ├── auth/                    # Login/logout templates
│   │   ├── ci_workflows/            # CI workflow templates
│   │   ├── components/              # Shared partial components
│   │   ├── connections/             # Integration connection templates
│   │   ├── dashboard/               # Dashboard templates
│   │   ├── env_vars/                # Environment variable templates
│   │   ├── groups/                  # Group management templates
│   │   ├── projects/                # Project/environment templates
│   │   ├── services/                # Service templates
│   │   │   └── wizard/              # Service creation wizard step templates
│   │   ├── settings/                # Settings page templates
│   │   ├── setup/                   # Initial setup templates
│   │   ├── templates/               # Service template browser templates
│   │   └── users/                   # User management templates
│   ├── templatetags/                # Custom template tags and filters
│   │   ├── audit_tags.py            # Audit log template tags
│   │   └── core_filters.py          # General-purpose template filters
│   ├── static/core/                 # App-specific static files (images)
│   ├── migrations/                  # Database migrations
│   ├── management/commands/         # Management commands
│   │   └── cleanup_versions.py      # `manage.py cleanup_versions`
│   ├── tests/                       # Unit tests for core app
│   ├── apps.py                      # CoreConfig (registers custom User model)
│   ├── admin.py                     # Django admin registrations
│   ├── ci_manifest.py               # CI manifest utilities (runtime compatibility, constraint intersection)
│   ├── ci_steps.py                  # CI step utility functions
│   ├── context_processors.py        # Template context processors (user_roles, navigation_context)
│   ├── converters.py                # URL converters (DnsLabelConverter)
│   ├── decorators.py                # View decorators (admin_required, operator_required)
│   ├── encryption.py                # Fernet encryption/decryption for sensitive config
│   ├── git_utils.py                 # Git operations (clone, scan, parse URLs)
│   ├── middleware.py                # SetupMiddleware (enforces initial setup flow)
│   ├── permissions.py               # Permission functions and view mixins (RBAC)
│   ├── utils.py                     # Shared utilities (env var cascade, setup token, resolve_env_vars)
│   └── validators.py                # DNS label validator for name fields
├── plugins/                         # Integration plugin packages
│   ├── __init__.py                  # autodiscover() function
│   ├── base.py                      # BasePlugin, CICapableMixin, PluginRegistry, helper functions
│   ├── github/                      # GitHub App integration plugin
│   │   ├── __init__.py              # Registers GitHubPlugin with registry
│   │   ├── plugin.py                # GitHubPlugin (BasePlugin + CICapableMixin implementation)
│   │   ├── forms.py                 # GitHub connection wizard forms
│   │   ├── views.py                 # GitHub-specific views
│   │   ├── urls.py                  # GitHub plugin URL patterns
│   │   ├── webhooks.py              # GitHub webhook handler (signature verification, event dispatch)
│   │   └── templates/github/        # GitHub-specific templates
│   └── docker/                      # Docker integration plugin
│       ├── __init__.py              # Registers DockerPlugin with registry
│       ├── plugin.py                # DockerPlugin implementation
│       ├── forms.py                 # Docker connection wizard forms
│       ├── views.py                 # Docker-specific views
│       ├── urls.py                  # Docker plugin URL patterns
│       └── templates/docker/        # Docker-specific templates
├── theme/                           # Tailwind CSS build and base template
│   ├── static_src/                  # npm build source
│   │   └── src/                     # Tailwind CSS input files
│   ├── static/css/dist/             # Compiled Tailwind CSS output
│   ├── static/js/vendor/            # Vendor JS (Alpine.js CSP build, HTMX)
│   └── templates/base.html          # Global base HTML template (Alpine.js component registrations)
├── tests/                           # Integration / cross-app tests
│   ├── core/                        # Core app test modules
│   └── plugins/                     # Plugin test modules
├── docs/                            # Design and feature documentation
│   ├── ci-workflows/                # CI workflow design docs
│   ├── deployments/                 # Deployment design docs
│   ├── security/                    # Security design docs
│   └── templates/                   # Template system docs
├── data/                            # Runtime data (git-ignored except .gitkeep)
│   ├── db.sqlite3                   # SQLite database
│   └── cache/                       # File-based Django cache (build logs)
├── secrets/                         # Auto-generated secrets (git-ignored)
│   ├── initialUnlockToken           # Unlock token for first-run setup
│   └── encryption.key               # Fernet encryption key (fallback if PTF_ENCRYPTION_KEY unset)
├── staticfiles/                     # Collected static files (git-ignored, generated)
├── scripts/                         # Dev scripts
│   └── run-dev.sh                   # Starts web + worker processes for `make run`
├── manage.py                        # Django CLI entrypoint
├── pyproject.toml                   # uv dependencies + ruff + pytest + import-linter config
├── uv.lock                          # Locked dependency versions
├── Makefile                         # Dev commands (run, stop, build, migrate, test)
├── Dockerfile                       # Container image (Python 3.13, uv, Gunicorn + Uvicorn)
├── docker-compose.yml               # Three services: portal, worker, scheduler
├── entrypoint.sh                    # Container startup (migrations + gunicorn)
└── CLAUDE.md                        # AI agent instructions for this codebase
```

---

## Directory Purposes

**`pathfinder/` (config package):**
- Purpose: Django project-level configuration — not a feature app
- Key files: `settings.py` (all Django settings), `urls.py` (root URL routing with plugin autodiscovery), `asgi.py` (Channels protocol router)
- Do not add feature code here

**`core/` (the app):**
- Purpose: Sole Django app — owns all domain models, all views, all background tasks
- Everything that is not a plugin or theme lives here
- `models.py` is a single large file with all models registered to `auditlog`
- `tasks.py` is a single large file with all `@task`-decorated functions
- `views/` has one module per feature area; `core/views/__init__.py` re-exports everything for `core/urls.py`

**`plugins/` (plugin packages):**
- Purpose: Provider-specific implementations extending core via `BasePlugin` / `CICapableMixin`
- Each plugin is a Python package with `__init__.py` that registers itself on import
- Plugin templates are served by adding `plugins/*/templates` directories to `TEMPLATES[0]["DIRS"]` in `settings.py`
- Core never imports from `plugins.github` or `plugins.docker` directly — only through `registry.get(name)` or `plugins.base` helpers

**`theme/` (CSS + base template):**
- Purpose: Tailwind CSS build pipeline and global `base.html` template
- `theme/static_src/` — npm build source; `theme/static/` — compiled output
- `theme/templates/base.html` — all pages inherit from this; Alpine.js component registrations (`Alpine.data()`) live here
- Import-linter enforces that theme never imports from core or plugins

**`data/` (runtime data):**
- SQLite database at `data/db.sqlite3`; file-based cache at `data/cache/`; mounted as Docker volume `data`

**`secrets/` (auto-generated):**
- `initialUnlockToken` — generated on first run, deleted after setup completes
- `encryption.key` — Fernet key fallback; production should use `PTF_ENCRYPTION_KEY` env var

---

## Key File Locations

**Entry Points:**
- `pathfinder/asgi.py`: ASGI entrypoint — HTTP + WebSocket protocol routing
- `manage.py`: Django CLI; used for migrations, `db_worker`, `run_task_scheduler`, `cleanup_versions`
- `entrypoint.sh`: Docker container startup script

**Configuration:**
- `pathfinder/settings.py`: All Django settings including CSP, task queues, cache, session, logging
- `pathfinder/urls.py`: Root URL router with plugin autodiscovery
- `pyproject.toml`: Dependencies (uv), linting (ruff), testing (pytest), import contracts (import-linter)
- `Makefile`: Developer commands

**Core Domain:**
- `core/models.py`: All Django models (User, Group, Project, Environment, Service, IntegrationConnection, CIStep, CIWorkflow, CIWorkflowVersion, Build, Template, etc.)
- `core/tasks.py`: All background tasks (scaffold_repository, scan_steps_repository, verify_build, etc.)
- `core/urls.py`: All HTTP URL patterns grouped by feature namespace
- `core/permissions.py`: RBAC functions and view mixins
- `core/utils.py`: `resolve_env_vars()` (env var cascade), setup token utilities
- `core/encryption.py`: `encrypt_config()` / `decrypt_config()` (Fernet)
- `core/git_utils.py`: Git protocol operations (clone, scan repos, parse URLs)
- `core/ci_manifest.py`: Runtime compatibility checking and constraint intersection

**Plugin Infrastructure:**
- `plugins/base.py`: `BasePlugin`, `CICapableMixin`, `PluginRegistry`, `get_ci_plugin_for_engine()`, `get_available_engines()`
- `plugins/__init__.py`: `autodiscover()` function

**WebSocket:**
- `core/consumers.py`: `ServiceConsumer` (poll-based WebSocket for service page real-time updates)
- `core/routing.py`: WebSocket URL patterns (`ws/services/<int:service_id>/`)

**Templates:**
- `theme/templates/base.html`: Global base template — Alpine.js registrations, navigation, CSP nonce injection
- `core/templates/core/components/`: Shared HTMX partial components
- `core/templates/core/<feature>/`: Feature-specific full-page and partial templates
- `plugins/<name>/templates/<name>/`: Plugin-specific templates

**Testing:**
- `tests/core/`: Core app integration tests
- `tests/plugins/`: Plugin tests
- `core/tests/`: Core app unit tests

---

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `ci_workflows.py`, `git_utils.py`)
- Django templates: `snake_case.html` or `kebab-case.html` (e.g., `list.html`, `wizard-step.html`)
- Test files: `test_<subject>.py` (e.g., `test_models.py`, `test_permissions.py`)

**Directories:**
- Django app directories: `snake_case` (e.g., `core/`, `plugins/`, `theme/`)
- Plugin packages: lowercase provider name (e.g., `github/`, `docker/`)
- Template subdirectories: `snake_case` matching feature name (e.g., `ci_workflows/`, `env_vars/`)

**Database / Model Identifiers:**
- Entity name fields (Project, Service, Group, etc.): DNS-label format enforced by `dns_label_validator` — lowercase letters, digits, hyphens; max 63 chars
- Service handler: `{project-name}-{service-name}` (computed property)
- URL parameters use `<dns:name>` type converter (e.g., `<dns:project_name>`, `<dns:workflow_name>`)
- UUIDs used for external references (`uuid` field); primary keys are BigAutoField integers

**Views:**
- Class-based views named `<Entity><Action>View` (e.g., `ProjectDetailView`, `ServiceCreateWizard`, `WorkflowPublishVersionView`)
- HTMX partial views follow same naming but templates are `_partial.html` convention

**URL Namespaces:**
- `setup`, `auth`, `dashboard`, `users`, `groups`, `audit`, `ci_workflows`, `connections`, `projects`, `settings`, `services`, `templates`
- Plugin namespaces match plugin name: `github`, `docker`

---

## Where to Add New Code

**New view (existing feature area):**
- Add class to the appropriate `core/views/<feature>.py`
- Re-export from `core/views/__init__.py` if needed by `core/urls.py`
- Add URL pattern to the matching pattern list in `core/urls.py`
- Add template to `core/templates/core/<feature>/`

**New feature area (new section of the app):**
- Create `core/views/<feature>.py`
- Create `core/forms/<feature>.py` if forms needed
- Create `core/templates/core/<feature>/` directory with templates
- Add URL pattern group in `core/urls.py`, import and register in `pathfinder/urls.py`
- Do NOT create a new Django app — keep all core logic in `core/`

**New domain model:**
- Add to `core/models.py`
- Create migration: `uv run python manage.py makemigrations`
- Register with `auditlog` at the bottom of `core/models.py` if it needs change tracking

**New background task:**
- Add `@task(queue_name="...")` function to `core/tasks.py`
- Use an existing queue name or add a new one to `TASKS["default"]["QUEUES"]` in `settings.py`

**New plugin:**
1. Create directory `plugins/<name>/`
2. Create `plugins/<name>/__init__.py` — must import plugin class and call `registry.register(instance)`
3. Create `plugins/<name>/plugin.py` — implement `BasePlugin`; implement `CICapableMixin` if CI engine support is needed
4. Create `plugins/<name>/forms.py` for wizard forms
5. Create `plugins/<name>/urls.py` returning URL patterns from `get_urlpatterns()`
6. Create `plugins/<name>/views.py` for plugin-specific views
7. Optionally create `plugins/<name>/templates/<name>/` for plugin templates
8. Update import-linter independence contract in `pyproject.toml` to include the new plugin module

**New Alpine.js component (multi-step logic):**
- Register via `Alpine.data('componentName', function() {...})` using `alpine:init` event listener in `theme/templates/base.html` if truly shared across pages
- Register in `{% block extra_head %}` of the specific page template if page-specific
- Never use `=>` arrow functions or semicolons in Alpine CSP expressions

**New template tag or filter:**
- Add to `core/templatetags/core_filters.py` for general filters
- Add to `core/templatetags/audit_tags.py` for audit-specific tags
- Load in template with `{% load core_filters %}`

---

## Special Directories

**`data/`:**
- Purpose: Runtime persistent data — SQLite DB and file cache
- Generated: Yes (auto-created by `settings.py`)
- Committed: No (git-ignored, mounted as Docker volume)

**`secrets/`:**
- Purpose: Auto-generated secret files for local/dev use
- Generated: Yes (created by `core/utils.py` and `core/encryption.py`)
- Committed: No (git-ignored)

**`staticfiles/`:**
- Purpose: Collected static files served by WhiteNoise in production
- Generated: Yes (by `python manage.py collectstatic` or `make build`)
- Committed: No (git-ignored)

**`theme/static_src/node_modules/`:**
- Purpose: npm dependencies for Tailwind CSS build
- Generated: Yes (by npm install)
- Committed: No (git-ignored)

**`.planning/`:**
- Purpose: GSD planning documents — codebase analysis, phase plans, quick fixes
- Generated: Yes (by GSD mapping and planning agents)
- Committed: Yes (version-controlled for team reference)

**`.import_linter_cache/`:**
- Purpose: import-linter analysis cache
- Generated: Yes (by `lint-imports` pre-commit hook)
- Committed: No (git-ignored)

---

*Structure analysis: 2026-02-24*
