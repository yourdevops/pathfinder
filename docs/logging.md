# Logging

**Status:** design — not yet implemented

Pathfinder uses four log streams, each serving a different consumer.

| Stream | Question It Answers | Storage | Consumer |
|--------|---------------------|---------|----------|
| **Audit log** | Who changed what, when? | Database (append-only) | Compliance, administrators |
| **Operation log** | What happened during this operation? | Database (per-module models) | Platform engineers (UI) |
| **Access log** | What requests hit the system? | stdout (JSON) | Security, ops |
| **System log** | How is the system behaving? | stdout (JSON) | Ops, log aggregator |

---

## Instrumentation Stack

Logging is built on **OpenTelemetry (OTel) auto-instrumentation for Django** and Python's standard `logging` module.

| Concern | Provided By |
|---------|-------------|
| Correlation (trace_id, span_id) | OTel auto-instrumentation |
| Service identity | `OTEL_SERVICE_NAME=pathfinder` resource attribute |
| Request spans | OTel Django instrumentation (automatic) |
| JSON formatting | JSON `logging.Formatter` (stdout) |
| Log level control | Django `LOGGING` dictConfig |
| Audit change tracking | django-auditlog |

No structlog dependency. OTel bridges Python's standard `logging` — existing `logging.getLogger(__name__)` calls work unchanged.

OTel runs **in-process only** — no network exporters, no collector connection from the app. The app writes structured JSON to stdout; the container orchestrator handles log collection and forwarding.

### Dependencies

```
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation-django
```

### Configuration

```shell
OTEL_SERVICE_NAME=pathfinder
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
OTEL_PYTHON_LOG_CORRELATION=true
OTEL_TRACES_EXPORTER=none
OTEL_LOGS_EXPORTER=none

# Log level (applied via Django LOGGING dict)
PTF_LOG_LEVEL=INFO  # default
```

stdout output uses a JSON `logging.Formatter` configured in Django's `LOGGING` dictConfig — not OTel exporters.

---

## Cross-Cutting Concerns

### Logger Naming

No application prefix. Module loggers use `__name__` per Python convention. Dedicated streams use short fixed names.

| Stream | Logger | Source |
|--------|--------|--------|
| Audit log | `audit` | `post_save` signal on `LogEntry` |
| Access log | `access` | Custom Django middleware |
| Operation log | `ops` | Dual-write on operation log save |
| System log | `__name__` | `core.tasks`, `core.git_utils`, `plugins.github`, etc. |

Service identity comes from OTel's `service.name` resource attribute, not from logger names. Downstream routing uses the `logger` field to split streams: match `audit`, `access`, or `ops` for dedicated pipelines; everything else is system log. These three logger names are a stable contract.

### Correlation

OTel auto-instrumentation injects `trace_id` and `span_id` into every log record produced during a request. Background tasks get their own trace context at execution start.

```json
{"ts": "...", "trace_id": "abc123...", "span_id": "def456...", "logger": "audit", "actor": "admin", ...}
```

No custom correlation middleware needed — OTel handles propagation across threads and async contexts.

### Sensitive Field Policy

Log entries must never contain passwords, tokens, API keys, encrypted field values, session identifiers, or CSRF tokens.

Enforcement by stream:

- **Audit log**: Use django-auditlog's `exclude_fields` on every model registration. Every new registration must list sensitive fields — this is a mandatory review checkpoint.
- **Operation log**: The `message` field must not interpolate secrets or raw user input. Use identifiers (IDs, slugs) instead.
- **System log**: Git commands must redact URL credentials. SCM API calls must not log request/response bodies containing tokens.
- **Access log**: Query parameters are logged but endpoints must never accept secrets via query string.

### Dual-Write (Database to stdout)

Audit and operation log entries are also emitted to stdout as structured JSON on write. The database is the source of truth. If stdout emission fails (serialization error, I/O), the failure is logged at WARNING level but does **not** roll back the database write. The stdout copy is best-effort.

### Log Levels

| Level | What's Logged | Production Safe? |
|-------|--------------|-----------------|
| `DEBUG` | SQL queries, full Git command args, HTTP request/response detail | No — high volume, may expose sensitive data |
| `INFO` | Task lifecycle, sync results, webhook delivery, health checks, startup/shutdown | Yes — default |
| `WARNING` | Deprecated config, rate limits approaching, dual-write stdout failures, retry attempts | Yes |
| `ERROR` | Task failures, unhandled exceptions, external service errors | Yes |
| `CRITICAL` | Audit chain integrity failure, data corruption, security events | Yes |

Unhandled exceptions are logged at ERROR with the full stack trace serialized as a single JSON `traceback` field (not multi-line).

Level configured via `PTF_LOG_LEVEL` environment variable (default: `INFO`), applied through Django's `LOGGING` dictConfig.

---

## Audit Log

Built on [django-auditlog](https://django-auditlog.readthedocs.io/). Every registered model automatically gets create/update/delete tracking via `LogEntry`.

### Model Registration

Models are registered in `core/models.py` with explicit field exclusions:

```python
auditlog.register(User, exclude_fields=["password", "last_login"])
auditlog.register(IntegrationConnection, exclude_fields=["config_encrypted"])
```

Each module documents which of its entities are audited and which actions apply. See:

- [CI Workflows — Logging](ci-workflows/logging.md)

### Change Tracking

django-auditlog captures field-level changes automatically. The `changes` field stores `{field_name: [old_value, new_value]}` for updates, and full field snapshots for creates/deletes.

### stdout Representation

A `post_save` signal on `LogEntry` emits each audit event to stdout via the `audit` logger:

```json
{"ts": "...", "trace_id": "...", "logger": "audit", "actor": "admin", "action": "update", "model": "CIWorkflow", "object_id": 7, "object_repr": "python-uv", "changes": {"name": ["Python Build", "Python UV Build"]}}
```

For deletion snapshots, the stdout copy omits the full changes body and logs event metadata only — the database has the full record.

### Actor Identity

| Source | Actor Value |
|--------|-------------|
| Authenticated user | username (e.g. `admin`) |
| Background task | `system:<task_name>` (e.g. `system:sync_steps`) |
| Webhook handler | `webhook:<provider>` (e.g. `webhook:github`) |

### Tamper Detection

Each `LogEntry` is extended with an `integrity_hash` field: SHA-256 of `(previous_hash, entry_id, timestamp, actor, action, object_id, changes)`. This creates a hash chain — gaps or modifications are detectable.

Verification runs:

- On-demand via `manage.py verify_audit_chain`
- Daily via scheduled task

Verification failures produce a CRITICAL system log entry. When alerting is configured, they trigger a notification.

### Retention & Lifecycle

Each `LogEntry` tracks two lifecycle timestamps:

| Field | Set By |
|-------|--------|
| `archived_at` | Scheduled task, when record passes retention period (default: **365 days**) |
| `exported_at` | SIEM outbox worker (automatic, if configured) or bulk cold storage export (admin UI action, if SIEM is not configured) |

Only one export mechanism is active at a time: if SIEM is configured, it handles export automatically. Bulk cold storage export is available only when SIEM is not configured.

Archived records are excluded from default UI queries but remain queryable with `include_archived=true`.

Purge precondition: `archived_at` is set AND `exported_at` is set. Records cannot be purged until an external copy is confirmed. Purge is an admin UI action.

When the SIEM endpoint is changed, the admin is prompted:

- **Re-export all** — reset `exported_at` on all records, full backfill to new endpoint
- **New events only** — keep existing `exported_at`, only future records go to the new endpoint

Archive, export, and purge operations are themselves audited (they go through normal request auth flow).

### UI

Compact timeline on entity detail pages and a dedicated audit log view (admin/auditor only). Each row shows timestamp, actor, action, and object. Expanding a row shows field-level changes with old/new columns (red/green styling). For multi-line fields (e.g., YAML workflow definitions), a richer diff view using `diff2html` can be added as an enhancement.

---

## Operation Log

Step-by-step traces of batch or background operations. Unlike the audit log (which records *that* something changed), operation logs record *how* an operation progressed — including intermediate states, warnings, and partial failures.

Each module defines its own operation log models. The generic pattern:

```
OperationLog:
  - status       : enum     — success, partial, failed, skipped
  - started_at   : datetime
  - completed_at : datetime

OperationLogEntry:
  - operation     : FK(OperationLog)
  - timestamp     : datetime
  - action        : enum     — module-specific
  - severity      : enum     — info, warning, error
  - message       : string   — max 2000 chars, truncated if exceeded
```

Module-specific docs:

- [CI Workflows — Logging](ci-workflows/logging.md)

### Failure Escalation

| Parent Status | Behavior |
|--------------|----------|
| `success` | No action |
| `partial` | WARNING system log. Amber indicator in UI. |
| `failed` | ERROR system log. When alerting is configured, triggers notification. |

### Retention

Default: **90 days**. Older entries are hard-deleted by a scheduled cleanup task. Operation logs are operational, not compliance-relevant — hard delete is acceptable.

### UI

Surfaced on the relevant entity's detail page. Users see a history of operations with expandable entries showing individual log lines, severity, timestamps, and warnings.

---

## Access Log

HTTP request log emitted by custom Django middleware via the `access` logger. Every request produces an access log entry to stdout.

```json
{"ts": "...", "trace_id": "...", "span_id": "...", "level": "info", "logger": "access", "method": "GET", "path": "/dashboard/", "status": 200, "duration_ms": 42, "user": "admin", "ip": "10.0.0.1"}
```

Captures: request method, path, query parameters, status code, duration, authenticated user (or `anonymous`), client IP, and failed authentication attempts (logged at WARNING).

Note: Django's built-in `django.request` logger also logs requests (5xx as ERROR, 4xx as WARNING), but doesn't include duration, client IP, or user identity. The custom `access` middleware provides the full picture.

### Client IP Resolution

Client IP is resolved from `X-Forwarded-For` using a configured trusted proxy list:

```python
PTF_TRUSTED_PROXIES = env.list("PTF_TRUSTED_PROXIES", default=[])
```

Only the rightmost untrusted IP in `X-Forwarded-For` is used. When `PTF_TRUSTED_PROXIES` is empty (local dev), `REMOTE_ADDR` is used directly. **Never trust `X-Forwarded-For` without a configured proxy list in production.**

Access logs are stdout-only — not stored in the database.

---

## System Log

Structured JSON to stdout for operational debugging and monitoring. Not stored in the database. Uses standard `logging.getLogger(__name__)` in each module.

### Processes

| Container | Responsibility |
|-----------|---------------|
| **portal** | Web server — HTTP requests, webhooks, admin UI |
| **worker** | Task worker — background jobs, syncs, scheduled tasks |

Both use the same log format. Locally via `make run`, output is prefixed with `[portal]` / `[worker]`.

### Format

```json
{"ts": "2025-01-15T10:30:00Z", "level": "info", "logger": "core.tasks", "trace_id": "abc123...", "msg": "Steps repo sync started", "repo": "ci-steps-github", "trigger": "webhook"}
```

### What Gets Logged

- Git command execution (command, duration, exit code — credentials redacted)
- SCM/CI API calls (endpoint, status code, duration, rate-limit headers)
- Webhook delivery and processing
- Background task lifecycle (queued, started, completed, failed, retried)
- Health check results
- Application startup and shutdown
- Configuration warnings

---

## Log Export

### stdout — Container-Native

All four streams reach stdout (database-backed logs are dual-written). The container runtime collects stdout automatically. Recommended container log driver settings:

```
max-size: 50m
max-file: 10
```

Log collection and forwarding to backends is an infrastructure concern — handled by the container orchestrator's log driver or a DaemonSet collector (Fluent Bit, OTel Collector, Vector). The application has no knowledge of downstream log destinations.

### Audit SIEM Integration (Optional)

Database-backed delivery of audit events to a SIEM endpoint using the **outbox pattern**. Configured by admins in **Settings > Audit SIEM**. Disabled by default.

Settings: endpoint URL, authentication token (stored encrypted), request timeout, and enable/disable toggle. The token field uses the same encrypted storage as integration connection credentials. When SIEM is enabled, bulk cold storage export is disabled — SIEM becomes the sole export path.

SIEM settings are managed via the admin UI and can also be declared in the CasC configuration file (see Settings docs). File-declared settings are locked in the UI.

**How it works:**

A background worker task polls for records where `exported_at` is null and pushes them to the SIEM endpoint in chronological order, in batches. On successful delivery → `exported_at` is set.

- On failure → retried with exponential backoff. Connection-level circuit breaker prevents hammering a dead endpoint (suspends after 5 consecutive failures, probes at increasing intervals capped at 5 minutes).
- Events are **never dropped** — they stay undelivered until `exported_at` is set, even across outages or restarts.
- On initial SIEM connection, all existing audit records have `exported_at = null` — providing full historical backfill. Batch size prevents worker starvation during large backfills.
- Scoped to audit events only — system, access, and operation logs are not shipped. Those streams rely on infrastructure-level collection.

**Delivery visibility:**

- Delivery state is surfaced on the **Settings > Audit SIEM** page: connection status, last successful delivery timestamp, count of unexported records, and a sticky warning when the circuit breaker is open. Clears automatically on recovery.
- Circuit breaker state changes (open/closed) produce a single WARNING/INFO system log entry — no per-event warnings.

---

## Access Control

| Action | Required Role |
|--------|--------------|
| View audit log (UI) | `admin`, `auditor` |
| View archived audit records | `admin`, `auditor` |
| Export audit log (API) | `admin`, `auditor` |
| View operation log (UI) | `admin`, `operator` |
| Export operation log (API) | `admin`, `operator` |
| Configure retention periods | `admin` |
| Run audit chain verification | `admin` |
| Export archived audit to cold storage | `admin` |
| Purge exported audit records | `admin` |
| Create API tokens | `admin` |
| Access log, system log | Infrastructure team (via log aggregator) |
