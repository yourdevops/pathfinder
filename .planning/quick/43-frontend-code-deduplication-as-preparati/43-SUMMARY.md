---
phase: quick-43
plan: 01
subsystem: ui
tags: [tailwind, css, semantic-tokens, component-classes, dark-mode]

# Dependency graph
requires:
  - phase: 01-02
    provides: "Initial dark mode setup with 7 semantic tokens"
provides:
  - "7 new semantic color tokens for surfaces, text, buttons"
  - "9 badge component classes (success/warning/danger/info/neutral + sm variants)"
  - "surface-interactive utility class"
  - "CSS custom properties for scrollbar theming"
  - "All 13 key templates use semantic tokens instead of raw gray-* colors"
affects: [theme-toggle, light-mode, ui-redesign]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Semantic dark-* color tokens for all themed surfaces and text", "Badge component classes for status indicators", "CSS custom properties for non-Tailwind contexts (scrollbar)"]

key-files:
  created: []
  modified:
    - "theme/static_src/tailwind.config.js"
    - "theme/static_src/src/styles.css"
    - "core/templates/core/services/_builds_tab.html"
    - "core/templates/core/services/_build_row.html"
    - "core/templates/core/services/_build_row_expanded.html"
    - "core/templates/core/services/_build_logs_partial.html"
    - "core/templates/core/services/_stats_row.html"
    - "core/templates/core/services/_recent_builds.html"
    - "core/templates/core/services/_details_tab.html"
    - "core/templates/core/services/_ci_tab.html"
    - "core/templates/core/services/_ci_manifest_status.html"
    - "core/templates/core/services/list.html"
    - "core/templates/core/projects/_services_tab.html"
    - "core/templates/core/components/nav_service.html"
    - "core/templates/core/ci_workflows/workflow_detail.html"

key-decisions:
  - "Status indicator dots (cancelled=gray-400, disconnected=gray-500) kept as raw gray since they are semantic status colors, not themed surfaces"
  - "bg-gray-950 kept for deepest log/expanded-row backgrounds since it is below the themed surface hierarchy"
  - "Cancelled build panel styling (gray-500/10 border) kept as status-specific, matching green/blue/red panel patterns"

patterns-established:
  - "Semantic token naming: dark-surface-alt for deeper surfaces, dark-surface-hover for interactive hover states"
  - "Badge component classes: badge-{variant} for py-1, badge-sm-{variant} for py-0.5"
  - "CSS custom properties in :root for non-Tailwind contexts (scrollbar styling)"

requirements-completed: [DEDUP-01, DEDUP-02]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Quick Task 43: Frontend Code Deduplication Summary

**Semantic dark-* color tokens and badge component classes replacing 27+ raw gray-* references across 15 files for future theme toggle readiness**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T18:04:26Z
- **Completed:** 2026-03-03T18:08:50Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Added 7 new semantic color tokens to tailwind.config.js (dark-surface-alt, dark-surface-hover, dark-text-secondary, dark-text-tertiary, dark-icon-muted, dark-btn-neutral, dark-btn-neutral-hover)
- Extracted 9 badge component classes and 1 surface-interactive utility into styles.css
- Replaced hardcoded hex colors in scrollbar CSS with CSS custom properties
- Replaced all raw gray-* surface/text colors across 13 template files with semantic tokens or badge classes

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Tailwind semantic tokens and extract CSS component classes** - `8ab1bd8` (feat)
2. **Task 2: Replace all raw gray-* colors in templates with semantic tokens and badge classes** - `321a935` (refactor)

## Files Created/Modified
- `theme/static_src/tailwind.config.js` - 7 new semantic color tokens added to extend.colors
- `theme/static_src/src/styles.css` - CSS custom properties for scrollbar, 9 badge classes, surface-interactive utility
- `core/templates/core/services/_builds_tab.html` - Table header, pagination, fetch button hover colors
- `core/templates/core/services/_build_row.html` - Row background, hover, copy button, cancelled badge
- `core/templates/core/services/_build_row_expanded.html` - Panel background, GitHub link hover, copy button
- `core/templates/core/services/_build_logs_partial.html` - Scroll buttons, log line text color
- `core/templates/core/services/_stats_row.html` - Card hover states
- `core/templates/core/services/_recent_builds.html` - Row hover states
- `core/templates/core/services/_details_tab.html` - Draft status badge
- `core/templates/core/services/_ci_tab.html` - Pending CI variables badge
- `core/templates/core/services/_ci_manifest_status.html` - Never Pushed and fallback status badges
- `core/templates/core/services/list.html` - Unknown status badge
- `core/templates/core/projects/_services_tab.html` - Draft status badge
- `core/templates/core/components/nav_service.html` - Draft status badge
- `core/templates/core/ci_workflows/workflow_detail.html` - Archive button, Never Pushed badge

## Decisions Made
- Status indicator dot colors (bg-gray-400 for cancelled, bg-gray-500 for disconnected WS) left as raw gray since they are semantic status indicators, not themed surfaces
- bg-gray-950 for log container and expanded row backgrounds left as-is since it represents the deepest layer below all themed surfaces
- Cancelled build status panels (bg-gray-500/10 with border-gray-500/30) left unchanged to maintain consistency with blue/green/red status panel patterns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 13 specified template files now use semantic tokens exclusively for surface/text theming
- Future theme toggle only needs to change tailwind.config.js color definitions and :root CSS custom properties
- Remaining gray-* references in other templates (connections, CI workflows, env vars) are out of scope for this task

---
*Quick Task: 43-frontend-code-deduplication*
*Completed: 2026-03-03*
