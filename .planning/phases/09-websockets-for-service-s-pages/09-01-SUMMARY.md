---
phase: 09-websockets-for-service-s-pages
plan: 01
subsystem: infra
tags: [django-channels, websocket, htmx-ext-ws, asgi, uvicorn, real-time]

# Dependency graph
requires:
  - phase: 05-services
    provides: "Service model and views"
  - phase: 06-builds
    provides: "Build model for polling data"
provides:
  - "Django Channels configured with ASGI ProtocolTypeRouter"
  - "ServiceConsumer with database polling and SHA-256 state diffing"
  - "htmx-ext-ws vendored and loaded in base.html"
  - "CSP connect-src allowing ws: and wss: schemes"
  - "WebSocket URL routing at /ws/services/<id>/"
  - "Development server using uvicorn for WebSocket support"
affects: [09-02, 09-03, 09-04]

# Tech tracking
tech-stack:
  added: [channels==4.3.2, htmx-ext-ws@2.0.3]
  patterns: [AsyncWebsocketConsumer with polling loop, database_sync_to_async for ORM queries, SHA-256 state hashing for change detection]

key-files:
  created:
    - core/consumers.py
    - core/routing.py
    - theme/static/js/vendor/htmx-ext-ws.min.js
  modified:
    - pathfinder/asgi.py
    - pathfinder/settings.py
    - scripts/run-dev.sh
    - theme/templates/base.html
    - theme/static_src/copy-vendor.js
    - theme/static_src/package.json
    - pyproject.toml

key-decisions:
  - "SHA-256 instead of MD5 for state hashing (bandit/semgrep security compliance)"
  - "contextlib.suppress for CancelledError cleanup (ruff SIM105 compliance)"
  - "Stub routing.py in Task 1 to unblock ASGI import before consumer exists"

patterns-established:
  - "AsyncWebsocketConsumer: poll loop with asyncio.create_task, cancel on disconnect"
  - "database_sync_to_async: import models inside method to avoid AppRegistryNotReady"
  - "State diffing: SHA-256 hash comparison to minimize WebSocket traffic"

requirements-completed: [SRVC-09]

# Metrics
duration: 4min
completed: 2026-02-24
---

# Phase 09 Plan 01: WebSocket Infrastructure Summary

**Django Channels with ASGI routing, ServiceConsumer polling loop with SHA-256 state diffing, and htmx-ext-ws client-side extension**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-24T19:47:01Z
- **Completed:** 2026-02-24T19:51:44Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Django Channels installed and configured with ProtocolTypeRouter for HTTP + WebSocket protocol dispatch
- ServiceConsumer accepts authenticated WebSocket connections, polls database every 3 seconds, and detects state changes via SHA-256 hashing
- htmx-ext-ws vendored, loaded in base.html, and CSP connect-src updated for ws:/wss: schemes
- Development server switched from runserver to uvicorn for WebSocket protocol upgrade support

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies and configure Django Channels + htmx-ext-ws** - `43a8ba6` (feat)
2. **Task 2: Create ServiceConsumer with polling loop and WebSocket routing** - `029b31c` (feat)

## Files Created/Modified
- `core/consumers.py` - ServiceConsumer with polling loop, state diffing, and build data aggregation
- `core/routing.py` - WebSocket URL routing mapping /ws/services/<id>/ to ServiceConsumer
- `theme/static/js/vendor/htmx-ext-ws.min.js` - Client-side WebSocket extension for htmx
- `pathfinder/asgi.py` - ProtocolTypeRouter with AllowedHostsOriginValidator and AuthMiddlewareStack
- `pathfinder/settings.py` - channels in INSTALLED_APPS, CSP connect-src with ws:/wss:
- `scripts/run-dev.sh` - uvicorn replaces runserver for WebSocket support
- `theme/templates/base.html` - htmx-ext-ws.min.js script tag after htmx
- `theme/static_src/copy-vendor.js` - htmx-ext-ws entry in vendor copy array
- `theme/static_src/package.json` - htmx-ext-ws@2.0.3 dependency
- `pyproject.toml` - channels==4.3.2 dependency

## Decisions Made
- **SHA-256 instead of MD5** for state change hashing: bandit and semgrep flagged MD5 as insecure. SHA-256 is equally fast for small payloads and passes all security linters.
- **Stub routing.py created in Task 1**: The ASGI config imports from core.routing, which does not exist until Task 2 creates it. Created an empty stub to unblock `manage.py check` verification.
- **contextlib.suppress for CancelledError**: ruff SIM105 requires this pattern instead of try/except/pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created stub core/routing.py in Task 1**
- **Found during:** Task 1 (ASGI configuration)
- **Issue:** pathfinder/asgi.py imports from core.routing which does not exist until Task 2
- **Fix:** Created empty stub with `websocket_urlpatterns = []`
- **Files modified:** core/routing.py
- **Verification:** `uv run python manage.py check` passes
- **Committed in:** 43a8ba6 (Task 1 commit)

**2. [Rule 1 - Bug] Changed MD5 to SHA-256 for state hashing**
- **Found during:** Task 2 (ServiceConsumer creation)
- **Issue:** bandit B324 and semgrep flagged MD5 as insecure hash algorithm
- **Fix:** Replaced `hashlib.md5()` with `hashlib.sha256()`
- **Files modified:** core/consumers.py
- **Verification:** All security linters pass
- **Committed in:** 029b31c (Task 2 commit)

**3. [Rule 1 - Bug] Used contextlib.suppress instead of try/except/pass**
- **Found during:** Task 2 (ServiceConsumer creation)
- **Issue:** ruff SIM105 requires contextlib.suppress pattern
- **Fix:** Replaced try/except asyncio.CancelledError/pass with contextlib.suppress
- **Files modified:** core/consumers.py
- **Verification:** ruff check passes
- **Committed in:** 029b31c (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 bug fixes, 1 blocking)
**Impact on plan:** All auto-fixes necessary for linter compliance and import resolution. No scope creep.

## Issues Encountered
None - all issues were auto-fixed during commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- WebSocket infrastructure fully operational, ready for Plan 02 (template partials)
- ServiceConsumer.render_updates() is a placeholder returning empty string, awaiting Plan 03 expansion
- All subsequent plans (02-04) can build on this foundation

## Self-Check: PASSED

- FOUND: core/consumers.py
- FOUND: core/routing.py
- FOUND: theme/static/js/vendor/htmx-ext-ws.min.js
- FOUND: commit 43a8ba6
- FOUND: commit 029b31c

---
*Phase: 09-websockets-for-service-s-pages*
*Completed: 2026-02-24*
