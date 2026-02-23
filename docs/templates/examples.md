# Examples

This page provides complete `pathfinder.yaml` examples for common service templates and scaffolded service repos. All examples are minimal and valid against the schema documented in [Manifest Schema](manifest-schema.md).

## Template Examples

The following examples are for template repositories (`kind: template`). These files live in template repos and are read by Pathfinder during registration and when the template is selected in the service creation wizard.

### Python FastAPI Service

A Python FastAPI service with PostgreSQL and Redis.

```yaml
kind: template
name: python-fastapi
description: "FastAPI service with async PostgreSQL and Redis"
runtimes:
  - python: ">=3.11"
required_vars:
  DATABASE_URL: "PostgreSQL connection string (asyncpg format)"
  SECRET_KEY: "Application secret key for JWT signing"
  REDIS_URL: "Redis connection string for caching"
```

### Node.js Express API

A Node.js Express API with TypeScript.

```yaml
kind: template
name: node-express-api
description: "Node.js Express REST API with TypeScript"
runtimes:
  - node: ">=20"
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
  JWT_SECRET: "Secret for JWT token signing"
  PORT: "Port the service listens on (e.g. 8080)"
```

### Go HTTP Service

A minimal Go HTTP service.

```yaml
kind: template
name: go-http-service
description: "Minimal Go HTTP service with Chi router"
runtimes:
  - go: ">=1.22"
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
  LOG_LEVEL: "Log verbosity: debug, info, warn, error"
```

### React Frontend (SPA)

A React single-page application. No `required_vars` because the frontend is served as static assets with no server-side secrets.

```yaml
kind: template
name: react-spa
description: "React single-page application with TypeScript and Vite"
runtimes:
  - node: ">=20"
```

No `required_vars` -- this is a valid template. If no runtime-level secrets are needed, the `required_vars` section can be omitted entirely.

### Multi-Runtime Service

A service that builds Python with Node.js tooling (e.g., a Django app with a compiled frontend).

```yaml
kind: template
name: django-with-frontend
description: "Django web app with compiled React frontend"
runtimes:
  - python: ">=3.11"
  - node: ">=20"
required_vars:
  DATABASE_URL: "PostgreSQL connection string"
  SECRET_KEY: "Django secret key"
  ALLOWED_HOSTS: "Comma-separated list of allowed hostnames"
```

## Service Examples

The following examples show `pathfinder.yaml` files as they appear in scaffolded service repos (`kind: service`). These are produced by scaffolding -- the template's `kind: template` becomes `kind: service` with `name` set to the service name entered in the wizard.

### Scaffolded Python FastAPI Service

The `python-fastapi` template after scaffolding into a service named `order-service`.

```yaml
kind: service
name: order-service
description: "FastAPI service with async PostgreSQL and Redis"
runtimes:
  - python: ">=3.11"
required_vars:
  DATABASE_URL: "PostgreSQL connection string (asyncpg format)"
  SECRET_KEY: "Application secret key for JWT signing"
  REDIS_URL: "Redis connection string for caching"
```

### Minimal Service (No Required Variables)

A service that requires no configurable variables.

```yaml
kind: service
name: frontend-static
description: "React SPA frontend"
runtimes:
  - node: ">=20"
```

No `required_vars` -- no variable enforcement applies. The service deploys without any manifest gate.

### Manually Added Manifest (Non-Scaffolded Service)

An existing service repo that was onboarded to Pathfinder without scaffolding. An operator added `pathfinder.yaml` manually to enable variable discovery.

```yaml
kind: service
name: legacy-api
description: "Legacy API service onboarded to Pathfinder"
required_vars:
  DATABASE_URL: "Primary database connection string"
  API_KEY: "Third-party API key for payment processing"
```

`runtimes` is optional. Omitting it means no CI Workflow recommendation is available for this service, but variable enforcement still applies.

---

For the full `pathfinder.yaml` field reference, see [Manifest Schema](manifest-schema.md). For how `required_vars` are enforced at deployment time, see [Variable Lifecycle](variable-lifecycle.md).
