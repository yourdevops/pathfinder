# Deployments -- Logging

Deployment-specific logging follows the patterns defined in the [core logging doc](../logging.md). This document covers the audited entities and operation log models specific to Deployments.

---

## Audited Entities

| Entity | Audited Actions |
|--------|----------------|
| Deployment | created, status_changed, completed, failed |
| DeployConnection (on Environment) | added, removed, set_default |

---

## Operation Log: Deployment Execution

Created on every deployment execution attempt (auto-deploy or manual).

```
DeploymentLog:
  - deployment     : FK(Deployment)
  - status         : enum (success, partial, failed)
  - started_at     : datetime
  - completed_at   : datetime

DeploymentLogEntry:
  - deploy_log     : FK(DeploymentLog)
  - timestamp      : datetime
  - action         : enum (pull_image, create_container, start_container, health_check, cleanup)
  - severity       : enum (info, warning, error)
  - message        : string
```

`status=partial` when the container started but the health check is inconclusive (e.g., health check timeout with container still running). `status=failed` when execution could not complete (connection refused, image pull failure).

### Warning Examples

Warnings surfaced via `DeploymentLogEntry`:

| Condition | Severity | Message |
|-----------|----------|---------|
| Image pull timeout | warning | `Image pull took 45s (threshold: 30s)` |
| Health check retry | warning | `Health check failed, retrying (attempt 2/3)` |
| Container port conflict | error | `Port 8080 already in use by container xyz` |
| Deploy connection unreachable | error | `Cannot reach Docker daemon at tcp://host:2375` |

---

## UI

- Deployment detail page shows execution log with expandable entries per deploy operation.
- Failed deployments show the error entry highlighted.
- Log entries are ordered by timestamp, with severity-based color coding (info: default, warning: amber, error: red).
