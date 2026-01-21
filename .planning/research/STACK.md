# Technology Stack Research

**Project:** DevSSP (Developer Self-Service Portal)
**Researched:** 2026-01-21
**Mode:** Stack validation and improvement for Django-based IDP

## Executive Summary

The existing stack decisions are **largely sound** for a Django-based internal developer platform. Django 6.0 is an excellent choice with its new built-in Tasks framework that reduces the need for Celery in simple use cases. However, several refinements and additions will improve the production readiness of DevSSP.

**Key validations:**
- Django 6.x: Excellent choice with new async capabilities and built-in background tasks
- django-guardian: Still the best choice for object-level permissions in Django
- Gunicorn: Solid for WSGI, but consider hybrid approach with Uvicorn workers
- SQLite (dev) / PostgreSQL (prod): Correct approach

**Key improvements recommended:**
- Add HTMX + Alpine.js for modern, lightweight frontend interactivity
- Replace django-fernet-fields with django-fernet-encrypted-fields (Jazzband maintained)
- Leverage Django 6.0's built-in Tasks framework for simple background jobs
- Add comprehensive testing and security tooling

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.13 | Runtime | Django 6.0 requires Python 3.12+. Python 3.13 is current and stable. | HIGH |
| Django | 6.0.x | Web framework | LTS track, built-in Tasks framework, template partials, CSP support. New features align perfectly with IDP requirements. | HIGH |

**Rationale:** Django 6.0 (released December 2025) introduces:
- **Built-in Tasks framework** - Queue background work without Celery for simple use cases (webhook processing, notification sending)
- **Template partials** - Better component reuse with `{% partialdef %}` and `{% partial %}` tags
- **Native CSP support** - Easier Content Security Policy configuration
- **Async pagination** - `AsyncPaginator` and `AsyncPage` for async views

**Source:** [Django 6.0 release notes](https://docs.djangoproject.com/en/6.0/releases/6.0/)

---

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| SQLite | 3.x | Development DB | Zero setup, WAL mode for better concurrency, sufficient for single-instance dev | HIGH |
| PostgreSQL | 16+ | Production DB | Full-text search, JSON operators, concurrent connections, production proven | HIGH |

**Validation of existing decision:** The SQLite (dev) / PostgreSQL (prod) split is a well-established Django pattern. Key considerations:

**SQLite for development:**
- Add WAL mode configuration in Django 5.1+ settings for better concurrency
- Sufficient for single-developer or small team development
- Zero infrastructure requirements

**PostgreSQL for production:**
- Required for horizontal scaling (multiple app instances)
- Better concurrent write performance
- Full `django.contrib.postgres` feature set (ArrayField, JSONField with operators, full-text search)
- Managed services (RDS, Cloud SQL) recommended over self-hosted

**Migration path:** Django's ORM abstraction makes SQLite-to-PostgreSQL migration straightforward. Test migrations in CI with PostgreSQL.

**Source:** [Django SQLite in Production guide](https://alldjango.com/articles/definitive-guide-to-using-django-sqlite-in-production)

---

### Authentication & Authorization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Django auth | 6.0 | Base auth | Built-in User, Group, Permission models. Extend with AbstractUser for `source` and `external_id` fields. | HIGH |
| django-guardian | 3.2.0 | Object-level permissions | Most mature Django object permission library. Direct FK optimization available for performance. | HIGH |

**Validation of django-guardian choice:**

After researching alternatives (django-rules, custom implementations), django-guardian remains the best choice for DevSSP's permission model:

**Why django-guardian over django-rules:**
- DevSSP needs explicit permission storage ("user X can access project Y") not rule-based evaluation
- Audit requirements need queryable permission records
- Group-based permissions integrate naturally with django-guardian's GroupObjectPermission
- Performance optimizations available (direct FK, ObjectPermissionChecker prefetching)

**Performance considerations:**
- Default generic foreign keys can be slow at scale
- Use direct FK permission models for Project and Environment permissions
- Prefetch permissions with `ObjectPermissionChecker` in list views

**Alternative considered:** `django-rules` - Better for rule-based ("users can edit their own objects") but DevSSP needs explicit assignment model for compliance/audit.

**Source:** [django-guardian documentation](https://django-guardian.readthedocs.io/en/3.0.3/userguide/performance/)

---

### Frontend

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Django Templates | 6.0 | HTML rendering | Built-in, now with partials support. Server-rendered for simplicity. | HIGH |
| HTMX | 2.x | Dynamic UI | 14KB, HTML-driven interactivity. Perfect for wizard flows, form updates, status polling. | HIGH |
| Alpine.js | 3.x | Client state | Lightweight (15KB), declarative, handles modal/dropdown/tabs without build step. | HIGH |
| django-htmx | 1.27.0 | HTMX integration | Middleware, template tags, request attributes for HTMX requests. | HIGH |

**Rationale for HTMX + Alpine.js over React/Vue:**

DevSSP is a **server-rendered** application with moderate interactivity needs:
- Wizard forms (multi-step, dynamic fields)
- Status polling (build/deployment status)
- Modal dialogs (confirmations, forms)
- Dynamic lists (filtering, pagination)

HTMX + Alpine.js provides this interactivity without:
- Separate build pipeline
- API duplication (views serve HTML, not JSON)
- Full-stack JavaScript expertise requirement
- 200KB+ JavaScript bundle

**Real-world validation:** Contexte replaced a 21,500 LOC React UI with Django + HTMX in 7,200 LOC (67% reduction). The entire team became "full stack" developers.

**Source:** [HTMX Django guide](https://www.saaspegasus.com/guides/modern-javascript-for-django-developers/htmx-alpine/)

---

### Background Tasks

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Django Tasks | 6.0 | Simple background jobs | Built-in, no external broker for basic use cases. Webhook processing, notifications. | MEDIUM |
| Celery | 5.4+ | Complex task orchestration | If needed: retries, chords, scheduled tasks, high-volume processing. | MEDIUM |
| Redis | 7.x | Task broker (if Celery) | Fast, production-proven message broker. Also useful for caching. | MEDIUM |

**Django 6.0 Tasks Framework - Key insight:**

Django 6.0's new Tasks framework is a **foundational API**, not a complete solution. It provides:
- `@task` decorator for defining background tasks
- Priority and queue_name support
- Pluggable backend architecture

**But:** Django only ships development backends (Immediate, Dummy). Production backends are community-provided or coming soon.

**Recommendation for DevSSP:**
1. **Start with Django Tasks** using database backend (community packages emerging)
2. **Evaluate Celery** if you need: complex task chains, scheduled tasks, high concurrency
3. **Keep architecture simple** - most IDP operations (repo creation, webhook processing) are infrequent

**Source:** [Django Tasks documentation](https://docs.djangoproject.com/en/6.0/topics/tasks/)

---

### Encryption & Security

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| cryptography | 46.0.x | Fernet encryption | Standard Python crypto library. Fernet for symmetric encryption of secrets. | HIGH |
| django-fernet-encrypted-fields | 0.3.1+ | Encrypted model fields | Jazzband maintained, Django 4.2+ compatible, likely Django 6.0 compatible. | MEDIUM |

**Warning:** The original `django-fernet-fields` is **unmaintained** (last release 2019). Use alternatives:

**Recommended: django-fernet-encrypted-fields (Jazzband)**
- Actively maintained by Jazzband community
- Supports Django 4.2+
- Built on cryptography library

**Alternative: Manual implementation**
```python
from cryptography.fernet import Fernet
# Store Fernet-encrypted values in TextField with custom property
```

**Key management best practices:**
- Store encryption key in environment variable (`SSP_ENCRYPTION_KEY`)
- Support key rotation (list of keys, newest first)
- Consider cloud KMS for production (AWS KMS, GCP KMS)

**Source:** [Fernet documentation](https://cryptography.io/en/latest/fernet/)

---

### Integration Libraries

| Library | Version | Purpose | Why | Confidence |
|---------|---------|---------|-----|------------|
| PyGithub | 2.8.1 | GitHub API | Typed, comprehensive GitHub REST API v3 wrapper. GithubIntegration for App auth. | HIGH |
| docker | 7.1.0 | Docker API | Official Docker SDK for Python. Container management via socket. | HIGH |
| httpx | 0.28.x | HTTP client | Async-capable, modern requests replacement. For webhook sending, API calls. | HIGH |
| PyYAML | 6.0.x | YAML parsing | ssp-template.yaml manifest parsing. | HIGH |

**GitHub integration notes:**
- Use `GithubIntegration` class for GitHub App authentication
- Generate installation access tokens for repo operations
- PyGithub supports all required operations: repo creation, branch creation, commits, PRs, webhooks

**Docker integration notes:**
- Mount Docker socket (`/var/run/docker.sock`) for container operations
- Use connection pooling for performance
- Handle Docker socket permission issues (DOCKER_GID environment variable)

**Source:** [PyGithub documentation](https://pygithub.readthedocs.io/en/stable/github_integration.html)

---

### WSGI/ASGI Server

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Gunicorn | 23.0.0 | Process manager | Stable, production-proven process management. | HIGH |
| Uvicorn | 0.34+ | ASGI server | High-performance ASGI for async views (optional) | MEDIUM |

**Current setup (validated):**
```bash
gunicorn devssp.wsgi:application -w 2 --threads 4 -b 0.0.0.0:8000
```

**Recommended upgrade path:**
```bash
# Hybrid approach: Gunicorn process management + Uvicorn ASGI workers
gunicorn devssp.asgi:application -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000
```

**Benefits of hybrid approach:**
- Gunicorn handles process management, graceful restarts
- Uvicorn handles HTTP requests with async support
- Enables async views for webhook processing, external API calls
- No architectural change needed, just worker class switch

**When to switch:** When implementing async views for external integrations (GitHub API calls, Docker API calls).

**Source:** [Uvicorn deployment guide](https://www.uvicorn.org/)

---

### Testing

| Library | Version | Purpose | Why | Confidence |
|---------|---------|---------|-----|------------|
| pytest | 8.x | Test runner | Better than Django's unittest. Fixtures, plugins, parametrization. | HIGH |
| pytest-django | 4.11.x | Django integration | Database fixtures, client fixtures, settings override. | HIGH |
| factory-boy | 3.3.x | Test factories | Cleaner than fixtures. Generates model instances with realistic data. | HIGH |
| coverage | 7.x | Code coverage | Track test coverage, fail builds below threshold. | HIGH |

**Testing strategy:**
```
tests/
  conftest.py          # Shared fixtures
  factories/           # Model factories
  unit/               # Unit tests (models, utils)
  integration/        # View tests, API tests
  e2e/                # Full workflow tests (optional)
```

---

### Development Tools

| Tool | Version | Purpose | Why | Confidence |
|------|---------|---------|-----|------------|
| ruff | 0.8+ | Linting/formatting | Replaces flake8, isort, black. Fast, all-in-one. | HIGH |
| mypy | 1.13+ | Type checking | Catch type errors before runtime. Django stubs available. | HIGH |
| pre-commit | 4.x | Git hooks | Enforce code quality on commit. | HIGH |
| django-debug-toolbar | 5.x | Development debugging | SQL queries, template context, profiling. | HIGH |

**pyproject.toml configuration:**
```toml
[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
plugins = ["mypy_django_plugin.main"]
strict = true
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Object permissions | django-guardian | django-rules | Need explicit storage for audit, not rule-based evaluation |
| Frontend | HTMX + Alpine | React/Vue | Over-engineered for server-rendered IDP. Adds build complexity. |
| Background tasks | Django Tasks | Celery (initially) | Django 6.0 Tasks sufficient for MVP. Add Celery if complexity demands. |
| Encryption | django-fernet-encrypted-fields | django-fernet-fields | Original package unmaintained since 2019 |
| HTTP client | httpx | requests | httpx supports async, modern API, better for ASGI |
| Linting | ruff | flake8 + isort + black | ruff is all-in-one and 10-100x faster |

---

## What NOT to Use

| Technology | Why Avoid |
|------------|-----------|
| django-fernet-fields (original) | Unmaintained since 2019, likely broken with Django 6.0 |
| Django REST Framework | Not needed - DevSSP is server-rendered, not a JSON API. HTMX partial responses suffice. |
| React/Vue/Next.js | Over-engineered for IDP needs. Adds build pipeline, API duplication, expertise requirements. |
| MongoDB | Django's ORM is PostgreSQL-optimized. NoSQL adds complexity without clear benefit. |
| GraphQL | No client diversity (single web UI). REST-style views simpler for server-rendered app. |
| Kubernetes (for DevSSP itself) | Over-engineered for single-instance IDP. Docker Compose sufficient for deployment. |

---

## Installation

### Core Dependencies
```bash
pip install Django==6.0.1
pip install gunicorn==23.0.0
pip install psycopg[binary]==3.2.4  # PostgreSQL adapter
```

### Authentication & Permissions
```bash
pip install django-guardian==3.2.0
```

### Frontend Enhancement
```bash
pip install django-htmx==1.27.0
# HTMX and Alpine.js via CDN or static files
```

### Integrations
```bash
pip install PyGithub==2.8.1
pip install docker==7.1.0
pip install httpx==0.28.1
pip install pyyaml==6.0.3
```

### Security
```bash
pip install cryptography==46.0.3
pip install django-fernet-encrypted-fields==0.3.1
```

### Testing
```bash
pip install pytest==8.3.4
pip install pytest-django==4.11.1
pip install factory-boy==3.3.3
pip install coverage==7.6.10
```

### Development
```bash
pip install ruff==0.8.6
pip install mypy==1.13.0
pip install django-stubs==6.0.0
pip install pre-commit==4.0.1
pip install django-debug-toolbar==5.0.1
```

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Django 6.0 | HIGH | Official release, verified release notes |
| django-guardian | HIGH | PyPI verified, Django 3.2+ compatible, likely works with 6.0 |
| HTMX approach | HIGH | Multiple production case studies, growing adoption |
| Django Tasks framework | MEDIUM | New in 6.0, production backends still emerging |
| django-fernet-encrypted-fields | MEDIUM | Jazzband maintained, Django 4.2+ but no explicit 6.0 testing documented |
| Uvicorn hybrid | MEDIUM | Well-documented pattern but requires testing |

---

## Gaps to Address

1. **Django 6.0 Task Backends** - No production-ready database backend in Django core yet. Monitor community packages or implement simple database queue.

2. **django-fernet-encrypted-fields Django 6.0** - No explicit compatibility statement found. Test during implementation or consider manual Fernet implementation.

3. **django-guardian Django 6.0** - Listed as Django 3.2+ compatible. Likely works but should be validated in integration tests.

---

## Sources

### Official Documentation
- [Django 6.0 Release Notes](https://docs.djangoproject.com/en/6.0/releases/6.0/)
- [Django Tasks Framework](https://docs.djangoproject.com/en/6.0/topics/tasks/)
- [django-guardian Documentation](https://django-guardian.readthedocs.io/)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
- [PyGithub Documentation](https://pygithub.readthedocs.io/en/stable/)
- [Uvicorn Deployment](https://www.uvicorn.org/)

### Community Sources
- [HTMX + Django Guide](https://www.saaspegasus.com/guides/modern-javascript-for-django-developers/htmx-alpine/)
- [Django Docker Best Practices](https://betterstack.com/community/guides/scaling-python/django-docker-best-practices/)
- [SQLite in Production](https://alldjango.com/articles/definitive-guide-to-using-django-sqlite-in-production)
- [Django 6.0 Background Tasks](https://betterstack.com/community/guides/scaling-python/django-background-tasks/)
- [HTMX vs React Comparison](https://betterstack.com/community/comparisons/htmx-vs-react/)

### Package Registries
- PyPI: django-guardian 3.2.0, PyGithub 2.8.1, docker 7.1.0, cryptography 46.0.3
