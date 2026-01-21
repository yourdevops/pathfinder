# Architecture Patterns for Internal Developer Platforms

**Domain:** Internal Developer Platform (IDP)
**Researched:** 2026-01-21
**Focus:** Validating Django monolith approach for DevSSP

---

## Executive Summary

DevSSP's planned architecture as a Django monolith with plugin-based extensibility is **appropriate and well-suited** for an IDP control plane. Research confirms:

1. **IDPs are orchestration layers, not compute-intensive systems** - They coordinate external tools rather than performing heavy processing, making monolith architecture viable
2. **Modular monoliths are the 2025-2026 consensus for small-medium teams** - 42% of organizations that adopted microservices have consolidated services back (CNCF 2025 survey)
3. **DevSSP's role as control plane (not data plane) maps well to monolith** - Low throughput, state-heavy, configuration-focused workloads favor monolithic designs
4. **Django's app system provides natural module boundaries** - The existing `core`, `integrations`, `wizard` app structure aligns with modular monolith best practices

**Recommendation:** Continue with Django monolith. Focus on clean module boundaries and async task handling for external operations.

---

## IDP Reference Architecture

### Industry Standard: Five Planes Model

The McKinsey/Humanitec reference architecture defines five planes for IDPs:

```
+------------------------------------------------------------------+
|                    DEVELOPER CONTROL PLANE                        |
|  - Developer Portal (UI)                                          |
|  - Service Catalog                                                |
|  - Self-Service Actions                                           |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                  INTEGRATION & DELIVERY PLANE                     |
|  - Platform Orchestrator (configuration engine)                   |
|  - CI/CD Pipelines                                                |
|  - Image/Artifact Registry                                        |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                       RESOURCE PLANE                              |
|  - Kubernetes / Container Runtimes                                |
|  - Databases / Messaging                                          |
|  - Cloud Resources                                                |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                      MONITORING PLANE                             |
|  - Observability (logs, metrics, traces)                          |
|  - Alerting                                                       |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                       SECURITY PLANE                              |
|  - Identity & Access                                              |
|  - Secrets Management                                             |
|  - Policy Enforcement                                             |
+------------------------------------------------------------------+
```

### Where DevSSP Fits

DevSSP operates primarily in the **Developer Control Plane** and **Integration & Delivery Plane**:

| Plane | DevSSP Role | Implementation |
|-------|-------------|----------------|
| Developer Control | Primary UI, service catalog, self-service | Django views, wizard flow |
| Integration & Delivery | Orchestration, CI/CD coordination | Plugin system, webhook handlers |
| Resource | Delegates to external tools | Kubernetes, Docker plugins |
| Monitoring | Aggregates status from external tools | Health checks, status polling |
| Security | RBAC, connection auth | Django auth, encrypted secrets |

**Key insight:** DevSSP is a **control plane**, not a data plane. It manages state and coordinates actions but does not process the actual workloads. This is the ideal use case for a monolith.

---

## Control Plane vs Data Plane

### Why This Distinction Matters

| Aspect | Control Plane | Data Plane |
|--------|---------------|------------|
| **Purpose** | Decision making, state management | Actual work execution |
| **Load profile** | Low volume, high complexity | High volume, high throughput |
| **Scaling needs** | Scale with complexity | Scale with throughput |
| **Architecture** | Often monolithic | Often distributed |

DevSSP characteristics (all control plane):
- Receives webhooks (low volume)
- Manages configuration state (database-heavy)
- Triggers actions in external systems (orchestration)
- Provides UI for developers (user-facing)

**Implication:** Microservices overhead is not justified. A monolith with async task handling handles this workload well.

---

## Recommended Architecture for DevSSP

### Component Diagram

```
                           +------------------+
                           |    Developers    |
                           +--------+---------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                           DJANGO MONOLITH                             |
|                                                                       |
|  +------------------+  +------------------+  +------------------+      |
|  |    Web Layer     |  |    API Layer     |  |  Webhook Layer   |      |
|  |  (Django Views)  |  |  (DRF or views)  |  | (Inbound events) |      |
|  +--------+---------+  +--------+---------+  +--------+---------+      |
|           |                     |                     |               |
|           +----------+----------+----------+----------+               |
|                      |                     |                          |
|                      v                     v                          |
|           +------------------+  +------------------+                   |
|           |   Core Domain    |  | Integration App  |                   |
|           |  (Models, Logic) |  |  (Plugin System) |                   |
|           +--------+---------+  +--------+---------+                   |
|                    |                     |                             |
|                    v                     v                             |
|           +------------------+  +------------------+                   |
|           |    Database      |  |   Task Queue     |                   |
|           |    (SQLite*)     |  |   (Celery opt.)  |                   |
|           +------------------+  +------------------+                   |
|                                          |                             |
+------------------------------------------+-----------------------------+
                                           |
                                           v
        +------------------------------------------------------------------+
        |                    EXTERNAL SYSTEMS (Data Plane)                 |
        |                                                                  |
        |  +----------+  +---------+  +------------+  +-------------+      |
        |  |   SCM    |  |   CI    |  |  Artifact  |  |   Deploy    |      |
        |  | (GitHub) |  |(Jenkins)|  |  Registry  |  | (K8s/Docker)|      |
        |  +----------+  +---------+  +------------+  +-------------+      |
        +------------------------------------------------------------------+

* SQLite for dev/small deployments; PostgreSQL for production at scale
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Web Layer** | User interface, form handling | Core Domain, Integration App |
| **API Layer** | REST endpoints for external access | Core Domain, Integration App |
| **Webhook Layer** | Receive events from CI/CD | Core Domain, Task Queue |
| **Core Domain** | Business logic, models, state | Database, Integration App |
| **Integration App** | Plugin registry, external calls | External Systems, Task Queue |
| **Task Queue** | Async operations, retries | Integration App, External Systems |
| **Database** | Persistent state | Core Domain |

### Data Flow

#### 1. Service Creation Flow

```
Developer                Django Web Layer              Core Domain
    |                          |                           |
    | 1. Submit wizard form    |                           |
    |------------------------->|                           |
    |                          | 2. Validate, create       |
    |                          |    Service record         |
    |                          |-------------------------->|
    |                          |                           |
    |                          |      Integration App      |
    |                          |           |               |
    |                          | 3. Get SCM plugin         |
    |                          |---------->|               |
    |                          |           |               |
    |                          |           | 4. Create repo
    |                          |           |-------------->| SCM (GitHub)
    |                          |           |<--------------|
    |                          |           |               |
    |                          | 5. Update Service         |
    |                          |    with repo reference    |
    |                          |-------------------------->|
    |                          |                           |
    | 6. Redirect to detail    |                           |
    |<-------------------------|                           |
```

#### 2. Build Webhook Flow

```
CI System               Webhook Layer             Core Domain         Task Queue
    |                        |                        |                   |
    | 1. POST /webhooks/     |                        |                   |
    |   builds/.../started   |                        |                   |
    |-----------------------|>|                        |                   |
    |                        | 2. Validate token,     |                   |
    |                        |    find Service        |                   |
    |                        |----------------------->|                   |
    |                        |                        |                   |
    |                        | 3. Create Build record |                   |
    |                        |    (status: running)   |                   |
    |                        |----------------------->|                   |
    |                        |                        |                   |
    | 4. 202 Accepted        |                        |                   |
    |<-----------------------|                        |                   |
    |                        |                        |                   |
    | ... build runs ...     |                        |                   |
    |                        |                        |                   |
    | 5. POST /webhooks/     |                        |                   |
    |   builds/.../complete  |                        |                   |
    |-----------------------|>|                        |                   |
    |                        | 6. Update Build        |                   |
    |                        |    (status: success)   |                   |
    |                        |----------------------->|                   |
    |                        |                        |                   |
    |                        | 7. Update Service      |                   |
    |                        |    current_artifact    |                   |
    |                        |----------------------->|                   |
    |                        |                        |                   |
    |                        | 8. Queue auto-deploy   |                   |
    |                        |    if configured       |                   |
    |                        |--------------------------------------->|   |
    |                        |                        |                   |
    | 9. 200 OK              |                        |                   |
    |<-----------------------|                        |                   |
```

#### 3. Deployment Flow

```
Developer           Web Layer          Core Domain       Integration App      Deploy Target
    |                   |                   |                  |                   |
    | 1. Click Deploy   |                   |                  |                   |
    |------------------>|                   |                  |                   |
    |                   | 2. Create         |                  |                   |
    |                   |    Deployment     |                  |                   |
    |                   |    record         |                  |                   |
    |                   |------------------>|                  |                   |
    |                   |                   |                  |                   |
    |                   | 3. Get deploy     |                  |                   |
    |                   |    plugin         |                  |                   |
    |                   |--------------------------------->|   |                   |
    |                   |                   |                  |                   |
    |                   |                   | 4. Execute       |                   |
    |                   |                   |    deployment    |                   |
    |                   |                   |----------------->|                   |
    |                   |                   |                  |------------------>|
    |                   |                   |                  |<------------------|
    |                   |                   |                  |                   |
    |                   |                   | 5. Update status |                   |
    |                   |                   |<-----------------|                   |
    |                   |                   |                  |                   |
    | 6. Show result    |                   |                  |                   |
    |<------------------|                   |                  |                   |
```

---

## Django Modular Monolith Pattern

### App Structure

Current DevSSP structure aligns with modular monolith best practices:

```
devssp/
  devssp/              # Project settings
    settings.py
    urls.py
  core/                # Core domain models
    models.py          # Project, Service, Build, Deployment, Environment
    views.py           # Main UI views
  integrations/        # Plugin system
    plugins/           # Auto-discovered plugins
      github.py
      jenkins.py
      kubernetes.py
    models.py          # IntegrationConnection
    registry.py        # Plugin discovery
  wizard/              # Service creation wizard
    views.py
    forms.py
  webhooks/            # Inbound event handlers
    views.py
```

### Module Communication Rules

Following modular monolith principles:

| Module | Can Call | Cannot Call |
|--------|----------|-------------|
| **core** | integrations (via registry) | wizard |
| **integrations** | core (read models) | wizard |
| **wizard** | core (create models), integrations | - |
| **webhooks** | core (update models) | wizard, integrations |

**Key principle:** Modules communicate via defined interfaces (service classes, registry), not direct model access across boundaries.

### Database Considerations

For modular monolith:
- **Single database is acceptable** when modules are in same codebase
- **Foreign keys across modules are fine** in monolith context
- **Module boundaries are logical**, enforced by code organization

When/if scaling requires:
- Start with read replicas for reporting
- Consider PostgreSQL for production
- Task queue for heavy operations (Celery)

---

## Plugin System Architecture

DevSSP's plugin pattern aligns with IDP best practices:

### Plugin Registry Pattern

```python
# integrations/registry.py (conceptual)

class PluginRegistry:
    _plugins: Dict[str, Type[IntegrationPlugin]] = {}

    @classmethod
    def register(cls, plugin_class):
        cls._plugins[plugin_class.name] = plugin_class

    @classmethod
    def get(cls, name: str) -> Type[IntegrationPlugin]:
        return cls._plugins[name]

    @classmethod
    def discover(cls):
        """Auto-discover plugins in integrations/plugins/"""
        # Import all modules in plugins/ directory
        # Each module registers its plugin classes
```

### Plugin Interface

```python
# integrations/base.py (conceptual)

class IntegrationPlugin(ABC):
    name: str
    category: str  # scm, ci, artifact, deploy
    capabilities: List[str]

    @abstractmethod
    def get_config_schema(self) -> Dict:
        """Return JSON schema for configuration"""
        pass

    @abstractmethod
    def test_connection(self, config: Dict) -> bool:
        """Verify connection works"""
        pass
```

### Category-Specific Interfaces

```python
class SCMPlugin(IntegrationPlugin):
    category = "scm"

    @abstractmethod
    def list_repos(self, connection) -> List[Repo]: pass

    @abstractmethod
    def create_repo(self, connection, name, org) -> Repo: pass

    @abstractmethod
    def clone(self, connection, repo, path) -> None: pass

class CIPlugin(IntegrationPlugin):
    category = "ci"

    @abstractmethod
    def trigger_build(self, connection, job, params) -> BuildRef: pass

    @abstractmethod
    def get_build_status(self, connection, build_ref) -> BuildStatus: pass

class DeployPlugin(IntegrationPlugin):
    category = "deploy"

    @abstractmethod
    def deploy(self, connection, artifact, config) -> DeployResult: pass

    @abstractmethod
    def get_status(self, connection, deployment) -> DeployStatus: pass
```

---

## Async Operations Pattern

### When to Use Async

| Operation | Sync or Async | Rationale |
|-----------|---------------|-----------|
| Webhook receive | Sync (fast ack) | Must respond quickly |
| Status update in DB | Sync | Fast, local operation |
| External API call | **Async** | May timeout, should retry |
| Repository creation | **Async** | Multiple steps, can fail |
| Deployment trigger | **Async** | Long-running, needs progress |

### Implementation Options

**Option 1: Django Background Tasks (Simple)**
- Use `django-background-tasks` for lightweight queue
- Good for MVP, single-server deployment
- No external dependencies (Redis/RabbitMQ)

**Option 2: Celery (Production)**
- Industry standard for Django async
- Requires Redis or RabbitMQ
- Better for multi-worker, high-volume scenarios

**Option 3: Database Queue (Minimal)**
- Use database table as simple queue
- Process with management command
- Simplest possible approach

**Recommendation for DevSSP MVP:** Start with Django Background Tasks or database queue. Add Celery if scaling requires it.

### Task Pattern Example

```python
# core/tasks.py (conceptual)

from background_task import background

@background(schedule=0)
def execute_deployment(deployment_id: int):
    """Execute deployment asynchronously"""
    deployment = Deployment.objects.get(id=deployment_id)
    deployment.status = 'running'
    deployment.save()

    try:
        plugin = PluginRegistry.get(deployment.deploy_connection.plugin_name)
        result = plugin.deploy(
            deployment.deploy_connection,
            deployment.artifact_ref,
            deployment.get_config()
        )
        deployment.status = 'success' if result.success else 'failed'
        deployment.error_message = result.error
    except Exception as e:
        deployment.status = 'failed'
        deployment.error_message = str(e)

    deployment.completed_at = timezone.now()
    deployment.save()
```

---

## Scalability Considerations

### Scale Stages

| Stage | Users | Architecture Changes |
|-------|-------|---------------------|
| MVP | 1-10 | Single Django + SQLite |
| Small team | 10-50 | PostgreSQL, Gunicorn workers |
| Growing | 50-200 | Redis cache, Celery workers |
| Enterprise | 200+ | Read replicas, horizontal scaling |

### What DevSSP Doesn't Need

Because DevSSP is a control plane:
- **No need for microservices** - Low traffic volume
- **No need for event sourcing** - Simple CRUD state
- **No need for GraphQL** - REST adequate for this domain
- **No need for real-time at MVP** - Polling acceptable initially

### What DevSSP Might Need Later

- **WebSocket for real-time updates** (deployment progress)
- **Read replicas** (if query load grows)
- **Caching layer** (plugin config, template metadata)

---

## Anti-Patterns to Avoid

### 1. Premature Microservices

**What goes wrong:** Splitting services before complexity justifies it
**Why it happens:** Following "best practices" without context
**Prevention:** Keep monolith until team size exceeds 10 or specific scaling bottleneck appears

### 2. Tight Coupling to External Tools

**What goes wrong:** Business logic depends on specific CI/deploy tool
**Why it happens:** Taking shortcuts in initial implementation
**Prevention:** All external interactions through plugin interface

### 3. Synchronous External Calls in Request Path

**What goes wrong:** User waits while DevSSP calls slow external APIs
**Why it happens:** Simpler to implement synchronously
**Prevention:** Queue external operations, return immediately with "pending" status

### 4. Fat Controllers

**What goes wrong:** Business logic in views/views
**Why it happens:** Django's MVC pattern encourages it
**Prevention:** Service layer between views and models

### 5. Shared Database State Across Plugins

**What goes wrong:** Plugins write to each other's tables
**Why it happens:** Seems efficient to share
**Prevention:** Plugins only access Connection model, not each other's data

---

## Build Order for Implementation

Based on dependencies between components:

### Phase 1: Foundation (Prerequisites for Everything)

1. **Core Models** - Project, Environment, Service (without plugins)
2. **Auth/RBAC** - Users, Groups, Roles, Permissions
3. **Admin UI** - Basic Django admin for setup

### Phase 2: Integration Infrastructure

4. **Plugin Registry** - Discovery mechanism, base classes
5. **IntegrationConnection Model** - Encrypted config storage
6. **Plugin Admin** - Connection management UI

### Phase 3: First Plugin (Validates Architecture)

7. **GitHub Plugin** - SCM operations (repos, branches, PRs)
8. **Webhook Handlers** - Receive events from external systems
9. **Basic Service Creation** - Without full wizard

### Phase 4: Build Pipeline

10. **Jenkins Plugin** - Trigger builds, receive status
11. **Build Model** - Track builds, artifacts
12. **Artifact Handling** - Store/retrieve artifact references

### Phase 5: Deployment

13. **Deploy Plugins** - Kubernetes and/or Docker
14. **Deployment Model** - Track deployments
15. **Environment Variables** - Cascade system

### Phase 6: Developer Experience

16. **Wizard Flow** - Full service creation experience
17. **Service Templates** - Blueprint system
18. **Dashboard** - Status overview

---

## Validation: Django Monolith for IDP

### Characteristics That Favor Monolith

| Characteristic | DevSSP | Monolith Appropriate? |
|----------------|--------|----------------------|
| Team size | Small (< 10) | Yes |
| Request volume | Low (< 100 req/s) | Yes |
| Data complexity | Moderate (10-20 models) | Yes |
| External dependencies | Many (plugins) | Yes |
| State management | Database-centric | Yes |
| Deployment frequency | Weekly/daily | Yes |

### When to Reconsider

Monitor for these signals that might warrant architecture change:
- Team grows beyond 10 full-time engineers on DevSSP
- Webhook volume exceeds 1000/minute sustained
- Need to deploy components independently
- Database becomes bottleneck despite optimization

### Verdict

**Django monolith is the right choice for DevSSP.** The application is:
- A control plane (low throughput)
- State-management focused
- Plugin-based (extensible without microservices)
- Team-size appropriate

The modular monolith approach with Django apps provides sufficient isolation while avoiding microservices complexity.

---

## Sources

### HIGH Confidence (Official Documentation)
- [AWS Prescriptive Guidance: Internal Developer Platform Architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/internal-developer-platform/design-architecture.html)
- [internaldeveloperplatform.org: What is an IDP](https://internaldeveloperplatform.org/what-is-an-internal-developer-platform/)

### MEDIUM Confidence (Verified Industry Sources)
- [Humanitec: Platform Orchestrator vs Developer Portal](https://humanitec.com/blog/humanitec-vs-backstage-friends-or-foes)
- [Port.io: Building a Platform Architecture](https://www.port.io/blog/building-a-platform-an-architecture-for-developer-autonomy)
- [CNCF 2025 Survey on Microservices Consolidation](https://foojay.io/today/monolith-vs-microservices-2025/)

### MEDIUM Confidence (Django-Specific)
- [Makimo: Modular Monolith in Django](https://makimo.com/blog/modular-monolith-in-django/)
- [Majestic Monolith Django Pattern](https://dev.to/kokospapa8/majestic-monolith-django-3690)

### LOW Confidence (General Guidance)
- Various Medium articles on monolith vs microservices 2025 decision frameworks
