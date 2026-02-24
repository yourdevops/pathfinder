# Codebase Concerns

**Analysis Date:** 2026-02-24

## Security Considerations

**API Token Stored as Plaintext:**
- Risk: `ApiToken.key` is stored as a plaintext `CharField(max_length=64)` in the database
- Files: `core/models.py` (line 187), `core/views/api.py` (line 50)
- Current mitigation: Tokens are looked up directly with `.get(key=token_key)` — no hashing
- Recommendations: Hash tokens with PBKDF2 or SHA-256 before storage (Django REST Framework's `Token` model uses SHA-256). Only show the full token once on creation. Lookup should compare hash, not plaintext.

**CSP connect-src Uses Wildcard ws: and wss::**
- Risk: `connect-src` directive allows WebSocket connections to any host (`ws:` and `wss:` without origin)
- Files: `pathfinder/settings.py` (line 197)
- Current mitigation: Other CSP directives are restrictive; this is a known cross-browser limitation with `self` and WebSockets
- Recommendations: Lock down to specific origins when the deployment URL is known, e.g., `wss://pathfinder.example.com`. The comment acknowledges this is a workaround — revisit when Django's CSP WebSocket support improves.

**Webhook Registration Not Idempotent — Duplicate Webhooks Accumulate:**
- Risk: `configure_webhook` always calls `repo.create_hook()` without checking for an existing hook with the same URL
- Files: `plugins/github/plugin.py` (line 762), `core/tasks.py` (line 1191), `core/views/services.py` (line 1107), `core/views/ci_workflows.py` (line 93)
- Current mitigation: `webhook_registered` flag on `Service` is set after first success, but manifest push calls `configure_webhook` regardless of flag
- Recommendations: Before creating a hook, list existing hooks and check for URL match. Only create if absent, update if mismatch. This prevents accumulation of duplicate webhook registrations per repo.

**PyGithub Private API Access for Token Extraction:**
- Risk: Token extraction uses private attribute chain `g._Github__requester._Requester__auth.token` — this is internal PyGithub API that can break across library versions without warning
- Files: `plugins/github/plugin.py` (lines 272, 983)
- Current mitigation: Used for log fetching and GHCR artifact resolution — operations that require raw HTTP with Bearer auth
- Recommendations: Store the installation token directly when creating the client, or use PyGithub's public `auth` object. Alternatively, use a separate authenticated `requests.Session` for raw API calls.

**Webhook Signature Verification Skipped When No Secret Configured:**
- Risk: If no `webhook_secret` is set on a connection, webhook events are accepted without any HMAC verification
- Files: `plugins/github/webhooks.py` (lines 173-179)
- Current mitigation: Warning is logged; still a soft fail with no enforcement
- Recommendations: Make webhook secret mandatory for `workflow_run` events. Reject (with 200 OK to avoid leakage, but log as warning) if no secret is configured rather than proceeding unauthenticated.

**Encryption Key Falls Back to File-Based Auto-Generated Key:**
- Risk: On fresh installs, `get_encryption_key()` auto-generates a key at `secrets/encryption.key` if `PTF_ENCRYPTION_KEY` env var is absent. If the secrets directory is not backed up, a container restart can generate a new key, making all stored configs permanently unreadable.
- Files: `core/encryption.py` (lines 54-66)
- Current mitigation: Docker Compose mounts `data:/app/data` but `secrets/` is in the project root (outside the volume mount)
- Recommendations: Either mount `secrets/` as a volume too, or enforce `PTF_ENCRYPTION_KEY` as a required env var with startup validation. Document the key rotation risk clearly.

**`ProjectUpdateCIConfigView` Missing Project-Level Authorization:**
- Risk: `ProjectUpdateCIConfigView` only checks `LoginRequiredMixin` — any authenticated user can toggle `allow_draft_workflows` on any project they can name
- Files: `core/views/projects.py` (line 590-603)
- Current mitigation: None; the view calls `get_object_or_404(Project, name=project_name)` with no role check
- Recommendations: Add `ProjectOwnerMixin` or an inline role check before saving CI config changes.

**`ServicePinVersionView` Missing Project-Level Authorization:**
- Risk: `ServicePinVersionView` only checks `LoginRequiredMixin` — any authenticated user can pin/unpin workflow versions on any service by guessing project/service names
- Files: `core/views/services.py` (line 1269)
- Current mitigation: None — no `can_access_project` check in the post handler
- Recommendations: Add contributor-level `can_access_project` check mirroring `ServiceAutoUpdateToggleView`.

---

## Tech Debt

**Large View Files Becoming Hard to Navigate:**
- Issue: `core/views/services.py` (1558 lines) and `core/views/ci_workflows.py` (1224 lines) pack many unrelated concerns into single files
- Files: `core/views/services.py`, `core/views/ci_workflows.py`
- Impact: Difficult to find logic; unrelated features become coupled via shared imports; long review diffs
- Fix approach: Split by functional area — e.g., `services_wizard.py`, `services_builds.py`, `services_ci.py` for services; `workflows_composer.py`, `workflows_steps.py` for CI workflows.

**Deferred Imports Inside Task Functions:**
- Issue: `core/tasks.py` uses local imports inside almost every task function body (`from core.models import ...` repeated 15+ times) to avoid circular imports
- Files: `core/tasks.py` (lines 27, 74, 104, 130, 139, 272, 279, 368, 460, 467, 526...)
- Impact: Circular import problem is a symptom of tight coupling between tasks and models; harder to test; obscures real dependencies; import performance cost on every task invocation
- Fix approach: Move model-level task-triggering logic to signals or service layer. Use a clean `from core import models as core_models` pattern at top of file with lazy resolution, or restructure to break the circular dependency at source.

**Hardcoded URL Strings Instead of `reverse()` in Services Views:**
- Issue: Multiple redirects inside `core/views/services.py` use f-string URLs like `f"/projects/{project_name}/services/{service_name}/?tab=ci"` instead of `reverse()`
- Files: `core/views/services.py` (lines 953, 956, 975, 1056, 1137, 1141, 1149, 1156, 1161, 1187, 1218, 1223, 1236, 1242, 1273)
- Impact: URL structure changes silently break redirects; no validation at startup; query parameter appended with string concat
- Fix approach: Use `reverse("projects:service_detail", ...)` for the base URL and append `?tab=ci` cleanly, or create a named URL that accepts a `tab` parameter.

**`build_template_context` in `consumers.py` Is Not Async-Safe:**
- Issue: `ServiceConsumer.build_template_context()` at line 152 is called from `render_updates()` via `@database_sync_to_async`, but it itself makes additional synchronous ORM calls (`Service.objects.get`, `Build.objects.filter`, etc.) without going through `database_sync_to_async`
- Files: `core/consumers.py` (lines 148-231)
- Impact: Since the whole `render_updates` method is already wrapped in `@database_sync_to_async`, the nested ORM calls run in the database thread pool correctly, but the pattern is fragile — any future refactor that moves context building out could break async safety silently
- Fix approach: Mark `build_template_context` as a standalone `@database_sync_to_async` method, or consolidate all ORM access into `get_current_state`.

**N+1 Query Pattern in Steps Repo List View:**
- Issue: `StepsRepoListView` iterates over repos and calls `.steps.count()` and `.runtimes.count()` inside the loop
- Files: `core/views/ci_workflows.py` (lines 41-45)
- Impact: 2 extra queries per `StepsRepository` row; grows linearly with number of repos
- Fix approach: Use `annotate(step_count=Count("steps"), runtime_count=Count("runtimes"))` on the queryset instead.

**Multiple Separate Count Queries in WebSocket Consumer:**
- Issue: `get_current_state()` issues 3 separate `COUNT` queries for `total_count`, `success_count`, and `completed_count` on the same table
- Files: `core/consumers.py` (lines 110-114)
- Impact: 3 round-trips to SQLite per 3-second poll cycle per connected user; at scale this multiplies
- Fix approach: Use a single aggregated query with `Count`, `Case`, `When` to get all counts in one DB hit, similar to how `services.py` uses `Avg`.

**File-Based Cache Not Suitable for Multi-Process Setup:**
- Issue: `FileBasedCache` is used for build log caching; in the Docker Compose setup, the web process and worker process share `data/` volume but file-based cache can produce race conditions under concurrent writes
- Files: `pathfinder/settings.py` (line 215), `core/views/services.py` (lines 1464, 1539)
- Impact: Log cache may be corrupted or read inconsistently under concurrent requests for the same build
- Fix approach: For now this is low-risk (one web process). As a future improvement, switch to database-backed cache or Redis. Add `cache.set(..., nx=True)` semantics to prevent write races.

**SQLite Without WAL Mode:**
- Issue: SQLite is configured with default journal mode; WAL mode allows concurrent reads and one write, which better suits an async web app with a background worker both touching the database
- Files: `pathfinder/settings.py` (lines 114-119)
- Current mitigation: Single-threaded worker limits contention
- Fix approach: Add `OPTIONS: {"init_command": "PRAGMA journal_mode=WAL;"}` in the database settings (Django 4.2+ supports `OPTIONS` for SQLite). See planning research at `.planning/research/STACK.md`.

**`consumer.py` Context Duplication with `services.py`:**
- Issue: `ServiceConsumer.build_template_context()` duplicates much of `ServiceDetailView.get_context_data()` logic, manually reconstructing context that the view already computes
- Files: `core/consumers.py` (lines 148-231), `core/views/services.py` (lines 542-820)
- Impact: Any change to page rendering logic must be made in two places; easy to diverge and create subtle WS/HTTP rendering inconsistencies
- Fix approach: Extract a shared `build_service_context(service_id, ...)` function in `core/context_helpers.py` that both view and consumer call.

---

## Performance Bottlenecks

**WebSocket Consumer Polls Every 3 Seconds Per Connected Client:**
- Problem: Each connected user to a service page maintains an asyncio task that queries SQLite every 3 seconds, computes a state hash, and conditionally renders partials
- Files: `core/consumers.py` (line 69)
- Cause: No channel layers configured — polling is used as a substitute for push-based updates
- Improvement path: Configure Django Channels `InMemoryChannelLayer` (or Redis for multi-instance) and use `channel_layer.group_send()` from tasks/webhooks to push updates only on actual state changes. This eliminates the polling loop entirely.

**Build Log Fetch Is Synchronous Inside Async WebSocket Context:**
- Problem: `BuildLogsView` is a synchronous Django view that calls `plugin.get_job_logs()` — an HTTP request to GitHub API — during request handling
- Files: `core/views/services.py` (line 1321+), `plugins/github/plugin.py` (line 965+)
- Cause: GitHub log fetching uses `requests.get()` which blocks the thread
- Improvement path: Already mitigated by file-based cache (60 minute TTL). Long-term: move to background task that pre-fetches logs for completed builds.

**`list_repositories()` Fetches All Repos Without Pagination:**
- Problem: `GitHubPlugin.list_repositories()` iterates the full result of `org.get_repos()` or `user.get_repos()` — PyGithub lazy-loads pages but the full list is consumed
- Files: `plugins/github/plugin.py` (lines 553-587)
- Cause: No limit or server-side filtering
- Improvement path: Add `per_page` parameter; only used in service creation wizard where a type-to-search pattern would be preferable to loading all repos.

---

## Fragile Areas

**GitHub App Installation Token Caching:**
- Files: `plugins/github/plugin.py` (lines 458-468, 480-484)
- Why fragile: Every call to `_get_github_client_app()` fetches a new installation access token via `gi.get_access_token()` — tokens expire in 1 hour but there is no caching. Under high activity (many health checks, webhook processing, build polls) this generates excessive JWT-signed API calls to GitHub.
- Safe modification: Add an in-memory or cache-backed token cache keyed by `(app_id, installation_id)` with TTL of 50 minutes. Check expiry before fetching.
- Test coverage: None — health check tests not present.

**Webhook Push Handler Uses In-Memory Loop to Match Steps Repos:**
- Files: `plugins/github/webhooks.py` (lines 239-246)
- Why fragile: `_handle_push` loads all `StepsRepository` objects and parses their `git_url` in a Python loop to find a match. As repo count grows, this is an O(N) scan per push event.
- Safe modification: Add a database-level lookup by normalizing the git URL at registration time into a canonical `owner/repo` field, then query directly.

**Template Clone via Full Git Clone (Not Shallow):**
- Files: `core/tasks.py` (line 272+), `core/git_utils.py` (`clone_repo_full`)
- Why fragile: Full clone is required for per-file `git log` to compute `commit_sha` per step. For large repositories this can be slow and disk-intensive in temp directories.
- Safe modification: Consider `git ls-tree` and `git log --diff-filter=A -- <path>` over a shallow clone instead of full history clone.
- Test coverage: No tests for git clone error paths.

**`scaffold_repository` Task Has No Retry Logic:**
- Files: `core/tasks.py` (`scaffold_repository` function)
- Why fragile: If a transient error occurs (network blip during clone, GitHub API 503) the task fails permanently and the service stays in `pending` scaffold state with no automatic recovery
- Safe modification: `django-tasks` supports `retry_on` parameter — add retry with exponential backoff for `GitCommandError` and `GithubException`.

**`SiteConfiguration.get_instance()` Called at Webhook Time:**
- Files: `plugins/github/webhooks.py` (line 186), `core/tasks.py` (line 1187)
- Why fragile: If `external_url` is not configured, webhook registration silently skips without surfacing this to the user. Service remains without webhook, meaning builds only show up via manual polling.
- Safe modification: Surface this as a configuration warning in the UI. Add a system health check that validates `external_url` is set when any connection exists.

---

## Test Coverage Gaps

**Core Views Are Untested:**
- What's not tested: All view classes in `core/views/services.py`, `core/views/ci_workflows.py`, `core/views/projects.py`, `core/views/connections.py`
- Files: `core/views/` (entire directory), `tests/` (only `test_ci_manifest.py` exists)
- Risk: Permission bypasses, wizard step validation failures, and redirect logic errors go undetected
- Priority: High

**Webhook Handler Has No Tests:**
- What's not tested: HMAC signature verification, `workflow_run` event dispatch, `push` event dispatch, service matching logic
- Files: `plugins/github/webhooks.py`
- Risk: Signature bypass bugs or incorrect service routing silently process unauthorized events
- Priority: High

**Background Tasks Are Untested:**
- What's not tested: `scaffold_repository`, `poll_build_details`, `push_ci_manifest`, `verify_build`, `scan_steps_repository`
- Files: `core/tasks.py`
- Risk: Task failures and retry behavior unknown; CI manifest push logic has no regression tests
- Priority: High

**GitHub Plugin Has No Tests:**
- What's not tested: All methods in `GitHubPlugin` — auth flows, API calls, manifest generation, output reference parsing
- Files: `plugins/github/plugin.py`
- Risk: PyGithub version updates or GitHub API changes break undetected
- Priority: Medium

**WebSocket Consumer Has No Tests:**
- What's not tested: `ServiceConsumer` connect/disconnect, polling loop, state hash computation, partial rendering
- Files: `core/consumers.py`
- Risk: WebSocket auth bypass or rendering regression not caught
- Priority: Medium

**Existing Tests are Django-Agnostic Unit Tests Only:**
- What's not tested: No Django test client usage, no authentication flows, no form validation, no database-level model constraints
- Files: `core/tests/test_env_vars.py` (env var cascade logic only), `tests/core/test_ci_manifest.py` (manifest math only)
- Risk: Integration between Django components (middleware, forms, views, models) completely untested
- Priority: High

---

## Known Issues / TODO Items

**Connection Detach Does Not Check Service Usage:**
- Issue: `ProjectDetachConnectionView` has a `# TODO: Check if any services use this connection (Phase 5+)` comment and unconditionally deletes the attachment
- Files: `core/views/projects.py` (line 426)
- Impact: Detaching a connection used by active services leaves services orphaned (no SCM connection for build polling, manifest push, or scaffolding)
- Fix approach: Query `Service.objects.filter(project=project, ...)` and check for services that depend on the connection before allowing detachment.

**Repository Cleanup on Service Creation Failure:**
- Issue: If service creation wizard fails after repository creation (e.g., template application fails), the GitHub repository is left orphaned with no cleanup
- Files: `core/views/services.py` (line 847 comment: `# TODO: Consider cleanup of repository...`)
- Impact: Orphaned repositories accumulate in the user's GitHub account
- Fix approach: Implement a compensating transaction: catch errors after `create_repository`, delete the repo via plugin API, then re-raise.

**`can_access_project()` Returns Boolean Not Role:**
- Issue: `can_access_project()` in `permissions.py` returns `bool`, but `ServiceFetchBuildsView` (line 906-907) calls it expecting the return value to be a role string (`if not role or role == "viewer"`)
- Files: `core/views/services.py` (lines 906-907), `core/permissions.py` (line 57-65)
- Impact: `can_access_project()` returns `True`/`False` — checking `role == "viewer"` on a boolean is always False, making the viewer guard ineffective. The actual check falls through to `True` for all authenticated users with any access.
- Fix approach: Either call `get_user_project_role()` directly (which returns the role string), or fix the guard to use boolean semantics consistently.

---

## Scaling Limits

**SQLite as Production Database:**
- Current capacity: Sufficient for single-instance deployment with low concurrent write load
- Limit: SQLite write lock means concurrent webhook ingestion + background task writes + web request writes contend for the same lock; degrades under >5 concurrent writes
- Scaling path: PostgreSQL migration via `DATABASE_URL` env var. Django ORM is database-agnostic so migration is straightforward. The main concern is `JSONField` usage which works identically on both.

**In-Process WebSocket Polling (No Channel Layers):**
- Current capacity: Each connected user spawns an asyncio coroutine polling every 3 seconds; Uvicorn handles concurrent WebSocket connections within a single process
- Limit: Memory and CPU grow linearly with connected users; no message broadcasting between processes
- Scaling path: Configure `CHANNEL_LAYERS` with `InMemoryChannelLayer` for single-instance (no Redis required), then push updates from tasks/webhooks instead of polling. For multi-instance: Redis channel layer.

---

## Dependencies at Risk

**`django-tasks` Pinned to `<0.12`:**
- Risk: Pinned to `>=0.11.0,<0.12` — may lag behind bug fixes in active development library
- Impact: Database backend task management is core infrastructure; version lock may miss security or correctness fixes
- Migration plan: Monitor `django-tasks` releases; upgrade incrementally after testing.

**`PyGithub` Private API Dependency:**
- Risk: `g._Github__requester._Requester__auth.token` accesses mangled private attributes; PyGithub major version change can break this without a deprecation notice
- Impact: GitHub log fetching and GHCR artifact resolution break silently
- Files: `plugins/github/plugin.py` (lines 272, 983)
- Migration plan: Open a PyGithub issue/PR for a public token accessor; in the interim wrap in try/except with fallback to alternative auth approach.

**`channels==4.3.2` Pinned to Exact Version:**
- Risk: Exact pin prevents security patches from being automatically applied
- Impact: WebSocket infrastructure; any CVE in channels 4.3.x requires manual pin update
- Migration plan: Loosen to `channels>=4.3.2,<5` to allow patch-level updates.

---

*Concerns audit: 2026-02-24*
