---
phase: quick-028
plan: 01
subsystem: security
tags: [csp, templates, alpine, htmx, security]
completed: 2026-02-02
duration: 4 min
dependency-graph:
  requires: [quick-025, quick-026]
  provides: [zero-inline-handlers, csp-compliant-templates]
  affects: [any-future-template-work]
tech-stack:
  patterns: [event-delegation, data-attributes, alpine-store, global-listeners]
key-files:
  modified:
    - theme/templates/base.html
    - core/templates/core/projects/create_modal.html
    - core/templates/core/projects/env_var_modal.html
    - core/templates/core/projects/add_member_modal.html
    - core/templates/core/users/list.html
    - core/templates/core/services/_settings_tab.html
    - core/templates/core/ci_workflows/workflow_detail.html
    - core/templates/core/groups/detail.html
    - core/templates/core/connections/detail.html
    - core/templates/core/projects/_settings_tab.html
    - core/templates/core/projects/environment_detail.html
    - core/templates/core/projects/_services_tab.html
    - core/templates/core/services/wizard/step_configuration.html
decisions:
  - Alpine $store for in-page modal toggle (users list) -- CSP build cannot evaluate inline expressions
  - Global data-confirm submit listener instead of per-form onsubmit
  - Global data-href click listener instead of per-row onclick
  - Event delegation for dynamically generated wizard inputs
---

# Quick Task 028: Address CSP Violation Findings Summary

Eliminated all CSP-violating inline event handlers across 13 template files using Alpine.js directives, data attributes, and addEventListener patterns.

## What Was Done

### Task 1: Global CSP-safe listeners in base.html (10b9c8c)
- Made closeModal handler generic (removes all z-50 overlays, not just attach-modal)
- Added global `data-confirm` submit listener for delete confirmations
- Added global `data-href` click listener for clickable table rows

### Task 2: Modal close buttons - 3 files, 9 onclick handlers (0010c36)
- Converted create_modal.html, env_var_modal.html, add_member_modal.html
- Applied same pattern as _attach_modal.html reference: x-data + @keydown.escape.window + @click

### Task 3: Users list modal - Alpine $store pattern (43027b5)
- Converted 3 onclick handlers to Alpine $store.createModal.open
- Converted 1 onsubmit to data-confirm
- Used Alpine.store() in nonce'd script for CSP-safe state management
- Server-side show_modal context variable preserved for form error re-opening

### Task 4: Delete confirmations - 10 onsubmit handlers across 6 files (fd812f5)
- Converted all onsubmit="return confirm(...)" to data-confirm="..." attributes
- Files: services settings, workflow detail, groups detail, connections detail, project settings, environment detail

### Task 5: Row click + copy manifest button (d1748d2)
- Replaced onclick on service table row with data-href attribute
- Replaced onclick on copy manifest button with addEventListener

### Task 6: Wizard env var handlers - event delegation (a9d5afd)
- Replaced inline onchange/onclick in dynamically generated HTML (innerHTML)
- Used data-action/data-index attributes with event delegation on container element

### Task 7: Verification sweep
- Confirmed x-cloak CSS already exists in styles.css
- Final grep: zero inline event handlers across all template files
- 11 data-confirm attributes across 7 files (all working via global listener)

## Deviations from Plan

None -- plan executed exactly as written.

## Patterns Established

| Pattern | Where | Purpose |
|---------|-------|---------|
| `data-confirm="msg"` on form | Global submit listener in base.html | CSP-safe delete confirmations |
| `data-href="url"` on tr | Global click listener in base.html | CSP-safe row navigation |
| `x-data @keydown.escape.window` on modal | Each HTMX-loaded modal | CSP-safe modal close (Alpine) |
| `Alpine.store()` in nonce'd script | In-page modals (users list) | CSP-safe state for non-removable modals |
| `data-action` + event delegation | Dynamic innerHTML content | CSP-safe handlers for JS-generated DOM |

## Metrics

- **Templates modified:** 13
- **Inline handlers eliminated:** 25+ (onclick, onsubmit, onchange)
- **Commits:** 6
- **Duration:** 4 minutes
