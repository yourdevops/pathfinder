---
phase: quick
plan: 032
subsystem: ci
tags: [webhook, github, ci-workflow, service-settings]

# Dependency graph
requires:
  - phase: 06-builds
    provides: Build model, webhook endpoint
provides:
  - Service.webhook_registered field for tracking webhook status
  - Auto-registration of webhooks during CI manifest push
  - Manual webhook registration via Settings tab
affects: [07-deploy, services, ci-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns: [webhook registration on manifest push]

key-files:
  created:
    - core/migrations/0018_add_service_webhook_registered.py
  modified:
    - core/models.py
    - core/tasks.py
    - core/views/services.py
    - core/urls.py
    - core/templates/core/services/_settings_tab.html

key-decisions:
  - "Webhook registration is attempted but failures don't block manifest push"
  - "Webhook status shown in Settings tab with manual registration option"
  - "Uses SiteConfiguration.external_url for webhook callback URL"

patterns-established:
  - "Webhook Configuration section in service settings with status badge"

# Metrics
duration: 4min
completed: 2026-02-03
---

# Quick Task 032: Add Webhook Registration to Manifest Summary

**Auto-register webhooks during CI manifest push with manual registration fallback in service settings**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-03
- **Completed:** 2026-02-03
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Service model tracks webhook_registered status
- push_ci_manifest task auto-registers webhook after pushing manifest
- Service Settings tab shows webhook status (Configured/Not Configured badge)
- Manual "Register Webhook" button for services without configured webhooks

## Task Commits

Each task was committed atomically:

1. **Task 1: Add webhook_registered field and update push_ci_manifest task** - `23b86be` (feat)
2. **Task 2: Add manual webhook registration view and update Settings tab** - `769b991` (feat)

## Files Created/Modified
- `core/models.py` - Added webhook_registered BooleanField to Service model
- `core/migrations/0018_add_service_webhook_registered.py` - Migration for new field
- `core/tasks.py` - Updated push_ci_manifest to register webhook after manifest push
- `core/views/services.py` - Added ServiceRegisterWebhookView for manual registration
- `core/urls.py` - Added URL pattern for service_register_webhook
- `core/templates/core/services/_settings_tab.html` - Added Webhook Configuration section

## Decisions Made
- Webhook registration failures are logged but don't fail the manifest push (graceful degradation)
- Uses SiteConfiguration.external_url for constructing webhook callback URL
- Registration requires External URL to be configured in Settings > General
- Button is disabled when service has no repo_url

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Webhook registration integrated into CI workflow
- Build status updates will flow automatically when webhook is configured
- Ready for Phase 7 (Deploy)

---
*Phase: quick-032*
*Completed: 2026-02-03*
