# CI Workflows — Logging

CI-specific logging follows the patterns defined in the [core logging doc](../logging.md). This document covers the operation log models and audited entities specific to CI Workflows.

---

## Audited Entities

| Entity | Audited Actions |
|--------|----------------|
| CIWorkflow | created, updated, published, revoked, deleted |
| CIWorkflowVersion | published, revoked, deleted |
| StepsRepository | created, deleted, protection_validated, protection_failed |
| Step (catalog) | added, updated, archived, removed |

---

## Operation Log: Steps Repository Sync

Created on every sync attempt (webhook-triggered, manual, or scheduled).

```
StepsRepoSyncLog:
  - repo            : FK(StepsRepository)
  - commit_sha      : string
  - previous_sha    : string (nullable — null on first sync)
  - status          : enum (success, partial, failed, skipped)
  - started_at      : datetime
  - completed_at    : datetime
  - protection_valid: bool

StepSyncEntry:
  - sync_log  : FK(StepsRepoSyncLog)
  - step_slug : string
  - action    : enum (added, updated, archived, skipped)
  - severity  : enum (info, warning, error)
  - message   : string
```

`status=skipped` when the commit SHA hasn't changed since last sync. `status=partial` when some steps imported but others failed to parse or had conflicts.

### Warning Examples

Warnings surfaced via `StepSyncEntry`:

| Condition | Severity | Message |
|-----------|----------|---------|
| Slug collision with existing step | warning | `Slug "docker-build" already exists for github-actions (from repo X)` |
| YAML parse failure | error | `Failed to parse test/broken/action.yml: invalid YAML at line 12` |
| Name change causes slug change | warning | `Name changed from "Pytest Test" to "Test with Pytest" — archived step "pytest-test", created new step "test-with-pytest". 4 workflows reference the archived step.` |
| `x-pathfinder.name` diverges from CI-native `name` | warning | `x-pathfinder.name "Security Scanner" differs from CI-native name "lint-check"` |
| Branch protection degraded | error | `Required reviews not configured on default branch. Sync aborted.` |
| Step has no resolvable name | warning | `Skipped test/unnamed/action.yml: no x-pathfinder.name and no fallback` |

### UI

- **Steps Repository detail page**: Shows sync history with expandable entries per sync run
- **Step detail page**: Shows relevant sync entries for that specific step
