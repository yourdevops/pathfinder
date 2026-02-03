---
phase: 06-builds
verified: 2026-02-03T13:53:22Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 6: Builds Verification Report

**Phase Goal:** GitHub Actions can report build status; services transition from draft to active on first successful build

**Verified:** 2026-02-03T13:53:22Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GitHub Actions workflow can call build-started webhook with authenticated token | ✓ VERIFIED | Webhook endpoint exists at `/webhooks/build/`, HMAC verification implemented in `verify_github_signature()`, always returns 200 OK |
| 2 | GitHub Actions workflow can call build-complete webhook with artifact reference | ✓ VERIFIED | `extract_artifact_ref()` function parses `artifacts_url` from payload, passes to `poll_build_details` task, stored in `Build.artifact_ref` field |
| 3 | Build record shows commit SHA, status, artifact ref, and CI job URL | ✓ VERIFIED | Build model has all fields: `commit_sha`, `commit_message`, `status`, `artifact_ref`, `ci_job_url`, `github_run_id`, `run_number`, `branch`, `author`, `author_avatar_url`, timing fields |
| 4 | Service status transitions from "draft" to "active" after first successful build | ✓ VERIFIED | `activate_service_on_first_success()` checks for first success, sets `service.status = "active"`, updates `current_build_id` |
| 5 | User can view build history for a service showing all builds with statuses | ✓ VERIFIED | Builds tab queries `Build.objects.filter(service=self.service)`, displays table with status badges, commit info, author, timing, pagination (20/page), status filter, HTMX auto-refresh every 5s for running builds |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `core/models.py` | Build model with status state machine | ✓ VERIFIED | Build model exists with all fields, STATUS_CHOICES, `map_github_status()` static method, registered with auditlog |
| `core/views/webhooks.py` | CSRF-exempt webhook endpoint with HMAC verification | ✓ VERIFIED | 207 lines, `build_webhook()` function, `verify_github_signature()` with `hmac.compare_digest()`, `identify_service_from_webhook()`, `extract_artifact_ref()`, always returns 200 OK |
| `core/tasks.py` | poll_build_details background task | ✓ VERIFIED | `@task(queue_name="build_updates")` decorator, fetches from GitHub API, creates/updates Build records, calls `activate_service_on_first_success()` on success |
| `plugins/github/plugin.py` | get_workflow_run and get_commit methods | ✓ VERIFIED | `get_workflow_run()` returns run details (id, status, conclusion, timestamps, actor), `get_commit()` returns commit message |
| `core/views/services.py` | Builds tab context with filtering and pagination | ✓ VERIFIED | Imports Build and Paginator, filters by status, paginates (20/page), detects running builds for auto-refresh, provides empty state check |
| `core/templates/core/services/_builds_tab.html` | Builds tab template with table and filters | ✓ VERIFIED | 123 lines, table layout with 7 columns (Status, Commit, Branch, Author, Started, Duration, Actions), status filter dropdown, pagination controls, empty state UI, HTMX auto-refresh when `has_running_builds=True` |
| `core/templates/core/services/_build_row.html` | Individual build row component | ✓ VERIFIED | 121 lines, status badges with colors/icons, commit SHA (7 chars) + message, branch icon, author avatar with fallback, relative timestamps, duration formatting, CI job external link |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `core/views/webhooks.py` | `core/tasks.py` | `poll_build_details.enqueue()` | ✓ WIRED | Line 197: `poll_build_details.enqueue(run_id=..., artifact_ref=...)` with all required params |
| `core/tasks.py` | `plugins/github/plugin.py` | `plugin.get_workflow_run()` and `plugin.get_commit()` | ✓ WIRED | Lines 421, 431: Both methods called with proper error handling |
| `core/tasks.py` | `core/models.py` | `Build.objects.update_or_create()` | ✓ WIRED | Line 450: Creates/updates Build with all fields including `artifact_ref` and `commit_message` |
| `core/tasks.py` | Service activation | `activate_service_on_first_success()` | ✓ WIRED | Line 471: Called when `status == "success"`, checks for first success, updates service status to "active" |
| `core/views/services.py` | `core/models.py` | `Build.objects.filter()` query | ✓ WIRED | Line 374: Filters builds by service, applies status filter, paginates results |
| `core/templates/_builds_tab.html` | `core/templates/_build_row.html` | Template include | ✓ WIRED | Line 61: `{% include "core/services/_build_row.html" with build=build %}` |

### Requirements Coverage

| Requirement | Status | Supporting Evidence |
|-------------|--------|---------------------|
| BILD-01: GitHub Actions can call build started webhook | ✓ SATISFIED | Webhook at `/webhooks/build/` accepts POST, processes 'requested' action |
| BILD-02: GitHub Actions can call build complete webhook with artifact ref | ✓ SATISFIED | Processes 'completed' action, extracts `artifact_ref` from payload, stores in Build model |
| BILD-03: Webhook validates authentication token | ✓ SATISFIED | `verify_github_signature()` with HMAC-SHA256 and timing-safe `compare_digest()` |
| BILD-04: Build record stores commit SHA, status, artifact ref, CI job URL | ✓ SATISFIED | All fields present in Build model and populated by `poll_build_details` task |
| BILD-05: Service status transitions from draft to active on first successful build | ✓ SATISFIED | `activate_service_on_first_success()` implements logic with proper checks |
| BILD-06: User can view build history for a service | ✓ SATISFIED | Builds tab with table, filtering, pagination, auto-refresh for running builds |

### Anti-Patterns Found

None detected. Code quality is high:
- No TODO/FIXME comments in key files
- No placeholder returns or empty implementations
- Proper error handling with try/except blocks
- Logging at appropriate levels
- Security best practice: always returns 200 OK from webhook

### Human Verification Required

#### 1. Webhook HMAC Signature Verification

**Test:** Configure GitHub webhook with secret, send test payload with valid and invalid signatures

**Expected:**
- Valid signature: Build record created, task enqueued
- Invalid signature: Logged warning, no Build created, still returns 200 OK

**Why human:** Requires external GitHub configuration and webhook delivery testing

#### 2. Build Status Auto-Refresh

**Test:** Create a build with "running" status, navigate to Builds tab, observe page behavior

**Expected:** Page auto-refreshes every 5 seconds without full page reload, status updates when build completes

**Why human:** Real-time behavior requires running app and timing observation

#### 3. Service Activation on First Success

**Test:** Create service (starts as "draft"), trigger successful build, verify service status

**Expected:** Service status changes from "draft" to "active", subsequent successful builds don't change status

**Why human:** Requires full CI integration with GitHub Actions to trigger real builds

#### 4. Build History UI Visual Appearance

**Test:** View Builds tab with multiple builds in different states, verify visual hierarchy and styling

**Expected:** Status badges colored correctly (blue/green/red/gray), avatars display, durations formatted nicely, empty state looks good

**Why human:** Visual appearance and UX feel can't be verified programmatically

#### 5. Pagination and Filtering

**Test:** Create 25+ builds, apply status filter, navigate pages

**Expected:** Shows 20 builds per page, filter updates URL and results, pagination maintains filter, page numbers accurate

**Why human:** Requires substantial test data and interaction testing

### Gaps Summary

None. All automated verification passed.

---

## Verification Details

### Level 1: Existence ✓

All required files exist:
- `core/models.py` - Build model added
- `core/views/webhooks.py` - 207 lines (new file)
- `core/tasks.py` - Modified with poll_build_details and activate_service_on_first_success
- `core/urls.py` - Webhooks patterns registered
- `pathfinder/urls.py` - Webhooks namespace included
- `pathfinder/settings.py` - build_updates queue added
- `plugins/github/plugin.py` - get_workflow_run and get_commit methods added
- `core/migrations/0017_build.py` - Build model migration
- `core/views/services.py` - Builds tab implementation
- `core/templates/core/services/_builds_tab.html` - 123 lines
- `core/templates/core/services/_build_row.html` - 121 lines

### Level 2: Substantive ✓

All files have real implementations:
- Build model: 80+ lines with full field definitions, state machine, helper method
- Webhook endpoint: 207 lines with HMAC verification, service identification, artifact extraction
- poll_build_details task: 100+ lines with API calls, error handling, Build creation, service activation
- GitHub plugin methods: Proper API calls returning structured data
- Builds tab view logic: Filtering, pagination, running build detection
- Templates: Complete HTML with HTMX, styling, empty states, all table columns

**No stub patterns found:**
- Zero TODO/FIXME comments in critical paths
- No `return null` or empty returns
- No console.log-only implementations
- All functions have real logic

### Level 3: Wired ✓

All components properly connected:
- Webhook URL registered: `/webhooks/build/` → `webhooks.build_webhook`
- Task enqueued: `poll_build_details.enqueue()` called with all params
- GitHub API called: `plugin.get_workflow_run()` and `plugin.get_commit()` used
- Build record created: `Build.objects.update_or_create()` with all fields
- Service activated: `activate_service_on_first_success()` called on success
- UI queries data: `Build.objects.filter(service=...)` in view
- Template includes row: `{% include "_build_row.html" %}` with build context
- HTMX auto-refresh: Conditional `hx-trigger="every 5s"` when running builds exist

---

_Verified: 2026-02-03T13:53:22Z_
_Verifier: Claude (gsd-verifier)_
