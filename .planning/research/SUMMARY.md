# Project Research Summary

**Project:** Pathfinder (Developer Self-Service Portal)
**Domain:** Internal Developer Platform (IDP)
**Researched:** 2026-01-21
**Confidence:** HIGH

## Executive Summary

Pathfinder is an Internal Developer Platform control plane - a category with 89% market dominance held by Backstage, and growing enterprise adoption (75% by 2026 according to Gartner). The research validates Pathfinder's core architecture decisions while identifying critical improvements needed for production readiness.

**The recommended approach:** Pathfinder should remain a Django monolith with plugin-based extensibility. The control plane workload profile (low volume, high complexity, state-heavy) aligns perfectly with monolithic architecture. Django 6.0's new built-in Tasks framework, template partials, and CSP support make it an excellent choice. The stack should be augmented with HTMX + Alpine.js for lightweight interactivity, avoiding the build complexity of React/Vue. The existing plugin architecture (IntegrationPlugin -> IntegrationConnection) is well-designed and matches IDP industry patterns.

**Key risks and mitigations:** Five critical pitfalls require immediate attention: (1) webhook-only integration creates state inconsistency - add reconciliation endpoints; (2) permission leakage via django-guardian - filter every queryset, not just check permissions in views; (3) secrets in environment variables - integrate external secrets managers before env var cascade; (4) SQLite in production - support PostgreSQL from day one; (5) static portal syndrome - build orchestration APIs first, UI second. The current design has already avoided the worst IDP anti-pattern: trying to rebuild existing tools instead of orchestrating them.

## Key Findings

### Recommended Stack

Django 6.0 is the right foundation, bringing critical new features aligned with IDP needs: built-in Tasks framework for background jobs (webhook processing, notifications), template partials for better component reuse, and native CSP support. Python 3.13 is required. The SQLite (dev) / PostgreSQL (prod) split follows established Django patterns, though PostgreSQL support should be implemented from the start, not deferred.

**Core technologies:**
- **Django 6.0** — Web framework with new Tasks framework, template partials, CSP support. Eliminates need for Celery in simple use cases.
- **django-guardian 3.2.0** — Object-level permissions. Best choice for explicit permission storage (vs rule-based evaluation). Requires careful queryset filtering to avoid leaks.
- **HTMX 2.x + Alpine.js 3.x** — Lightweight frontend interactivity (29KB total). Server-rendered HTML with dynamic updates. No build pipeline. Real-world case: Contexte reduced 21.5K LOC React to 7.2K LOC HTMX (67% reduction).
- **PostgreSQL 16+** — Production database. Required for horizontal scaling, concurrent writes, full-text search, JSON operators. Managed services (RDS, Cloud SQL) recommended.
- **Gunicorn 23.0 + Uvicorn workers** — Hybrid WSGI/ASGI serving. Enables async views for external API calls without full rewrite.
- **PyGithub 2.8.1** — GitHub API integration with GithubIntegration class for App auth.
- **docker 7.1.0** — Official Docker SDK for container operations via socket mount.
- **cryptography 46.0 + django-fernet-encrypted-fields** — Fernet encryption for secrets. Original django-fernet-fields unmaintained since 2019.

**Critical upgrade:** Replace the unmaintained django-fernet-fields with Jazzband-maintained django-fernet-encrypted-fields (0.3.1+).

**What NOT to use:** Django REST Framework (not needed for server-rendered app), React/Vue (over-engineered, adds build complexity), Celery initially (Django Tasks sufficient for MVP), MongoDB (no clear benefit for this domain).

### Expected Features

Pathfinder's current design covers table stakes well: service catalog, blueprints/golden paths, self-service deployment, environment management, RBAC, build/deployment tracking, and integration plugins. The approach aligns with industry expectations for IDP functionality.

**Must have (table stakes):**
- Software catalog with ownership tracking (covered: Services/Projects; gap: add explicit owner field, not just created_by)
- Service blueprints/golden paths (covered: ssp-template.yaml manifest system)
- Self-service deployment (covered: wizard + direct/GitOps/pipeline mechanisms)
- Environment management (covered: Environment model with connection binding, env var cascade)
- RBAC at system and project levels (covered: SystemRoles + ProjectRoles with group-based model)
- Build and deployment tracking (covered: Build/Deployment models with webhooks)
- Integration plugins (covered: IntegrationPlugin + IntegrationConnection architecture)
- Production safeguards (covered: is_production flag; planned: approval workflows)
- Audit logging (planned: comprehensive trails beyond permission changes)

**Should have (competitive differentiators):**
- **Scorecards/Service maturity** — HIGH PRIORITY addition. Track service health, production readiness, compliance. Key differentiator vs Cortex/OpsLevel ($40-65/user/month competitors).
- **Observability integration** — MEDIUM PRIORITY. Link services to monitoring dashboards/alerts. 32.8% of platform engineers cite observability as main focus.
- **Documentation as code** — MEDIUM PRIORITY. Render markdown docs from service repos in portal UI (Backstage TechDocs pattern).
- **Secrets management integration** — Already on roadmap. Implement External Secrets Operator pattern for K8s.

**Defer (v2+):**
- Service dependency visualization (high complexity, nice-to-have)
- AI-assisted features (emerging, not essential yet)
- Ephemeral environments (complex, not MVP-critical)
- Full FinOps/cost attribution (enterprise tier feature)

**Anti-features to avoid:**
- Custom CI system (integrate Jenkins/GitHub Actions, don't replace them)
- Built-in secrets storage (security liability; use Vault/AWS Secrets Manager)
- Custom container runtime (delegate to Docker/Kubernetes)
- Full PaaS functionality (Pathfinder is control plane, not compute plane)
- Unlimited custom workflows (Port.io's flexible approach creates maintenance burden)

### Architecture Approach

The Django monolith with modular app structure is validated as appropriate for IDP control planes. Research confirms 42% of organizations that adopted microservices have consolidated services back (CNCF 2025). Pathfinder operates in the Developer Control Plane and Integration/Delivery Plane - orchestrating actions, not processing workloads. This low-volume, high-complexity, state-heavy profile favors monolithic architecture.

**Major components:**
1. **Core Domain** (core app) — Models (Project, Service, Environment, Build, Deployment), business logic. State management and orchestration coordination.
2. **Integration App** (integrations app) — Plugin registry with auto-discovery, category-specific interfaces (SCMPlugin, CIPlugin, DeployPlugin), IntegrationConnection model for encrypted configs.
3. **Web Layer** (wizard app) — Django views with HTMX partials for dynamic updates. Wizard flows for service creation, status polling for deployments.
4. **Webhook Layer** (webhooks app) — Inbound event handlers from CI/CD systems. Fast acknowledgment (202 Accepted) with async processing.
5. **Task Queue** — Background job processing. Start with django-background-tasks or database queue; upgrade to Celery + Redis if volume demands.

**Data flow pattern:** User -> Web Layer -> Core Domain -> Integration App -> External System (GitHub/Jenkins/K8s). Webhooks flow reverse: External System -> Webhook Layer -> Task Queue -> Core Domain update.

**Module boundaries:** Core can call integrations via registry; integrations can read core models; wizard can call both; webhooks can only update core (no calling wizard/integrations). Single database acceptable for monolith; foreign keys across modules are fine.

### Critical Pitfalls

Research identified five critical pitfalls that could cause rewrites, security breaches, or adoption failure:

1. **Webhook-Only Integration Fragility** — Pathfinder's design choice of "webhook-only CI integration (no polling)" creates state inconsistency risk. Missed webhooks leave builds showing "pending" forever. Prevention: implement idempotent handlers with deduplication, add reconciliation API endpoint for manual sync, log all webhook payloads for replay capability. Consider hybrid: webhook for real-time + periodic health sync.

2. **Permission Leakage via Object-Level Access** — Using django-guardian without comprehensive queryset filtering exposes data across projects. Prevention: always filter querysets with get_objects_for_user(), never just check permissions in views. Test every list view for proper scoping. Complex hierarchy (User -> Group -> ProjectMembership -> Service) needs audit. Add "effective permissions" debug endpoint.

3. **Secrets in Environment Variables** — The env var cascade (Project -> Environment -> Service -> Deployment) will tempt users to store secrets. Prevention: document "env_vars are for CONFIGURATION ONLY", add validation rejecting common secret patterns (api_key, password, token), integrate external secrets managers (Vault, AWS Secrets Manager) before implementing env vars. Secrets should be injected at deploy time by plugin, never stored in Pathfinder.

4. **SQLite in Production** — Current CLAUDE.md spec lists SQLite as stack. Works for dev but creates write locks under concurrent webhooks, no HA, limited scaling. Prevention: support PostgreSQL from day one, use SQLite only for local development. Enterprise deployment requires PostgreSQL.

5. **Static Portal Syndrome** — IDP becomes directory of links, not self-service platform. Developers bypass it. Prevention: build orchestration APIs first, UI second. Every page should enable action, not just display info. Measure "actions completed" not "portal visits". Pathfinder wizard design already avoids this - ensure wizard actually triggers deployments.

## Implications for Roadmap

Based on combined research findings, dependencies from architecture analysis, and pitfalls to avoid, here's the recommended phase structure:

### Phase 1: Foundation & Security
**Rationale:** RBAC, audit logging, and PostgreSQL support must precede all features. Permission filtering baked in from start avoids rewrites. Database choice impacts scalability permanently.

**Delivers:** User/Group/Role models with django-guardian integration, audit logging via django-auditlog, PostgreSQL support with SQLite fallback for dev, base Django admin for system configuration.

**Addresses:**
- Table stakes: RBAC at system level
- Critical pitfall: Permission leakage (filter every queryset from day one)
- Critical pitfall: SQLite in production (PostgreSQL support upfront)

**Stack:** Django 6.0, PostgreSQL 16, django-guardian 3.2.0, django-auditlog, cryptography

**Research flag:** SKIP - standard Django patterns, well-documented.

### Phase 2: Plugin Infrastructure
**Rationale:** All subsequent features depend on integration capabilities. Plugin architecture must be proven with at least two diverse integrations before building on it.

**Delivers:** IntegrationPlugin base classes (SCMPlugin, CIPlugin, DeployPlugin), plugin registry with auto-discovery, IntegrationConnection model with encrypted config storage, connection management UI, health check system.

**Addresses:**
- Table stakes: Integration plugins framework
- Moderate pitfall: Plugin architecture rigidity (test with diverse integrations early)

**Stack:** django-fernet-encrypted-fields for connection secrets, httpx for external API calls

**Avoids:** Tight coupling to specific tool (GitHub-only design). Must work for GitHub + GitLab + BitBucket from architecture.

**Research flag:** MEDIUM - category-specific plugin interfaces (SCM vs CI vs Deploy) may need refinement during implementation.

### Phase 3: Core Domain Models
**Rationale:** Project/Environment/Service hierarchy provides organizational structure. Build/Deployment tracking captures state. Must be complete before wizard can create services.

**Delivers:** Project, Environment, Service, Build, Deployment models with project-scoped permissions, environment variable cascade infrastructure (without UI), artifact reference tracking, status state machines.

**Addresses:**
- Table stakes: Service catalog, environment management, build/deployment tracking
- Critical pitfall: Permission leakage (test queryset filtering comprehensively)

**Implements:** Core Domain architecture component

**Research flag:** SKIP - CRUD models with standard Django patterns.

### Phase 4: SCM & CI Integration
**Rationale:** Service creation requires SCM for repo creation. Build tracking requires CI webhooks. These are the first two external integrations that prove the plugin architecture.

**Delivers:** GitHub plugin (repo creation, branch operations, PR creation), Jenkins plugin (build triggering, status webhooks), webhook ingestion endpoints with token authentication, webhook reconciliation API for state sync.

**Addresses:**
- Table stakes: First two integration types (SCM + CI)
- Critical pitfall: Webhook-only fragility (implement reconciliation from start)

**Stack:** PyGithub 2.8.1, httpx for Jenkins API

**Avoids:** Synchronous external API calls in request path. Queue webhook processing, return 202 Accepted immediately.

**Research flag:** HIGH - GitHub App authentication, Jenkins webhook security, retry/idempotency patterns need research during phase planning.

### Phase 5: Deployment Orchestration
**Rationale:** Secrets integration must precede env var cascade to avoid secrets in database. Deploy plugins bring self-service value but require external secrets.

**Delivers:** External secrets integration (Vault plugin or K8s External Secrets Operator), environment variable UI with "config vs secrets" separation, Docker deployment plugin, Kubernetes deployment plugin (direct mode), deployment state tracking with async task processing.

**Addresses:**
- Table stakes: Self-service deployment, production safeguards
- Critical pitfall: Secrets in environment variables (external secrets first)

**Stack:** docker 7.1.0 SDK, kubernetes client, HashiCorp Vault client

**Implements:** Async operations pattern from architecture research

**Research flag:** HIGH - Vault integration patterns, K8s RBAC for deployments, Docker socket security need phase-specific research.

### Phase 6: Developer Experience (Wizard)
**Rationale:** All infrastructure in place. Now build the developer-facing UX that ties it together. Wizard is the primary adoption driver.

**Delivers:** Multi-step service creation wizard, blueprint/template system with ssp-template.yaml parsing, template repository management with git tag versioning, variable substitution and repo scaffolding, HTMX-powered dynamic form updates, template catalog UI.

**Addresses:**
- Table stakes: Service blueprints/golden paths, self-service workflow
- Moderate pitfall: Abstraction level mismatch (progressive disclosure, show generated manifests before commit)

**Stack:** HTMX 2.x, Alpine.js 3.x, django-htmx 1.27.0, PyYAML 6.0

**Avoids:** Static portal syndrome. Wizard must complete full flow: create repo, configure CI, set up deployment.

**Research flag:** MEDIUM - HTMX patterns for multi-step forms, template variable schema design.

### Phase 7: Operational Visibility
**Rationale:** Dashboard and status views provide ongoing value after initial service creation. Real-time updates enhance UX but aren't blocking.

**Delivers:** Service dashboard with build/deployment status, project overview with service health, deployment history and rollback UI, real-time status updates via HTMX polling (upgrade to WebSocket in future), audit trail viewer.

**Addresses:**
- Table stakes: Comprehensive audit trails (expand beyond permission changes)
- Moderate pitfall: Adoption without intrinsic value (measure actions completed, not visits)

**Stack:** HTMX for partial refreshes, django-auditlog for comprehensive tracking

**Research flag:** SKIP - standard dashboard patterns.

### Phase Ordering Rationale

**Dependencies drive order:**
- Phase 1 before all: RBAC filters every subsequent queryset
- Phase 2 before 4: Plugin infrastructure required for integrations
- Phase 3 before 6: Models required for wizard to create services
- Phase 4 before 6: SCM integration required for wizard repo creation
- Phase 5 before 6: Deployment plugins required for wizard to offer deployment
- Phase 6 last: Wizard ties all infrastructure together

**Pitfall avoidance:**
- PostgreSQL support in Phase 1 avoids migration pain later
- Permission filtering in Phase 1 avoids security rewrites
- Reconciliation in Phase 4 prevents webhook state drift
- Secrets in Phase 5 (before env vars) prevents database secrets
- Diverse integrations in Phase 2 validates plugin architecture flexibility

**Value delivery:**
- Phase 4 delivers first external integration (can create repos)
- Phase 5 delivers first deployments (limited UX)
- Phase 6 delivers full self-service experience (adoption driver)
- Phase 7 enhances ongoing usage

### Research Flags

**Needs `/gsd:research-phase` during planning:**
- **Phase 4 (SCM & CI Integration):** GitHub App authentication flow, Jenkins webhook verification, webhook replay/idempotency patterns, error handling for API rate limits
- **Phase 5 (Deployment Orchestration):** Vault authentication/token renewal, K8s RBAC models for service accounts, Docker socket security (DOCKER_GID handling), External Secrets Operator setup
- **Phase 6 (Developer Experience):** HTMX multi-step form patterns, template variable schema design (balance simplicity vs flexibility), git operations error handling

**Standard patterns (skip research):**
- **Phase 1 (Foundation):** Django auth, django-guardian setup, audit logging, PostgreSQL configuration
- **Phase 3 (Core Domain):** Django models, state machines, foreign key relationships
- **Phase 7 (Operational Visibility):** Dashboard layouts, list/detail views, HTMX polling

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Django 6.0 official release verified, PyPI packages confirmed, HTMX production case studies documented |
| Features | HIGH | Multiple IDP comparisons (Backstage, Port, Humanitec, Cortex), Gartner research, feature consistency across sources |
| Architecture | HIGH | AWS Prescriptive Guidance, internaldeveloperplatform.org, CNCF survey data on monolith trend |
| Pitfalls | MEDIUM-HIGH | Multiple industry sources agree on top pitfalls, Pathfinder-specific assessment based on design docs |

**Overall confidence:** HIGH

Research is based on official documentation (Django, django-guardian, PyGithub), authoritative industry sources (AWS, CNCF, Gartner), and multiple community sources with consistent findings. The IDP domain is mature with established patterns.

### Gaps to Address

**Django 6.0 compatibility:**
- django-guardian lists Django 3.2+ support; no explicit 6.0 testing documented. Validate with integration tests during Phase 1.
- django-fernet-encrypted-fields lists Django 4.2+ support; test with Django 6.0 or implement manual Fernet encryption as fallback.

**Task queue for production:**
- Django 6.0 Tasks framework is new; production backends still emerging. Start with django-background-tasks or database queue for MVP. Monitor django-tasks-database or similar packages. Add Celery if webhook volume exceeds simple queue capacity.

**Template drift:**
- Current design treats templates as one-time scaffolding. Long-term, fleet management requires tracking template versions used per service and upgrade workflows. Defer to post-MVP but plan model field (Service.template_version_used).

**Webhook reliability:**
- Research confirms webhook-only integration is brittle. Reconciliation endpoint is minimum; consider optional polling fallback for unreliable networks (corporate firewalls, NAT issues). Implement webhook signature verification (HMAC) in Phase 4.

**Multi-tenancy:**
- Current design uses Projects for organizational separation. If true multi-tenancy required (isolated databases), consider django-tenants. Not blocking for MVP but impacts PostgreSQL schema design.

## Sources

### Primary (HIGH confidence)
- [Django 6.0 Release Notes](https://docs.djangoproject.com/en/6.0/releases/6.0/) — Tasks framework, template partials, CSP support
- [AWS Prescriptive Guidance: IDP Architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/internal-developer-platform/design-architecture.html) — Five planes model
- [internaldeveloperplatform.org](https://internaldeveloperplatform.org/what-is-an-internal-developer-platform/) — IDP definition, control plane concept
- [django-guardian Documentation](https://django-guardian.readthedocs.io/en/3.0.3/userguide/performance/) — Object permissions, performance optimization
- [PyGithub Documentation](https://pygithub.readthedocs.io/en/stable/github_integration.html) — GitHub App integration
- [Fernet Documentation](https://cryptography.io/en/latest/fernet/) — Encryption implementation

### Secondary (MEDIUM confidence)
- [Gartner Peer Insights](https://www.gartner.com/reviews/market/internal-developer-portals) — 75% adoption prediction
- [Roadie: Platform Engineering 2026](https://roadie.io/blog/platform-engineering-in-2026-why-diy-is-dead/) — Backstage 89% market share
- [CNCF 2025 Survey](https://foojay.io/today/monolith-vs-microservices-2025/) — 42% microservices consolidation
- [HTMX + Django Guide](https://www.saaspegasus.com/guides/modern-javascript-for-django-developers/htmx-alpine/) — 67% code reduction case study
- [Humanitec vs Backstage](https://humanitec.com/blog/humanitec-vs-backstage-friends-or-foes) — Platform orchestrator patterns
- [Port.io Platform Architecture](https://www.port.io/blog/building-a-platform-an-architecture-for-developer-autonomy) — IDP architecture patterns
- [Makimo: Modular Monolith Django](https://makimo.com/blog/modular-monolith-in-django/) — Module boundaries
- [Django Auditlog Guide](https://medium.com/@mahdikheireddine7/tracking-changes-in-django-with-django-auditlog-a-practical-guide-5bd2404b68b9) — Implementation patterns
- [Kubernetes Secrets Management 2025](https://infisical.com/blog/kubernetes-secrets-management-2025) — External Secrets Operator
- [Webhooks vs Polling](https://www.merge.dev/blog/webhooks-vs-polling) — Integration trade-offs
- [IDP Implementation Pitfalls](https://www.fairwinds.com/blog/how-to-avoid-7-idp-implementation-pitfalls) — Common mistakes
- [Platform Engineering Anti-Patterns](https://www.infoworld.com/article/4064273/8-platform-engineering-anti-patterns.html) — Adoption failures

### Tertiary (validation needed)
- Various Medium articles on Django guardian filtering, HTMX patterns, platform metrics

---
*Research completed: 2026-01-21*
*Ready for roadmap: yes*
