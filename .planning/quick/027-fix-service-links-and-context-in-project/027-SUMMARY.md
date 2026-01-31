---
phase: quick
plan: 027
subsystem: ui-navigation
tags: [sidebar, service-detail, navigation, htmx]
dependency-graph:
  requires: [05-04]
  provides: [service-sidebar-override, service-settings-tab]
  affects: []
tech-stack:
  added: []
  patterns: [block-sidebar-override]
key-files:
  created:
    - core/templates/core/services/_settings_tab.html
  modified:
    - theme/templates/base.html
    - core/templates/core/projects/_services_tab.html
    - core/templates/core/services/_details_tab.html
    - core/templates/core/components/nav_service.html
    - core/views/services.py
decisions:
  - key: block-sidebar-pattern
    choice: "Wrap sidebar in {% block sidebar %} in base.html"
    rationale: "Allows child templates to override sidebar without modifying context processors"
metrics:
  duration: 1 min
  completed: 2026-01-31
---

# Quick Task 027: Fix Service Links and Context in Project Summary

**One-liner:** Block sidebar override in base.html enables service-scoped navigation, with proper anchor links and a new Settings tab.

## What Was Done

### Task 1: Add block sidebar to base.html and fix service links
- Wrapped sidebar include logic in `base.html` with `{% block sidebar %}...{% endblock %}` so child templates (like `detail.html`) can override it
- Changed service names on the project services tab from `<span>` to `<a>` anchor tags with hover styling
- Service detail page now correctly renders `nav_service.html` instead of `nav_project.html`

### Task 2: Add Settings tab to service view
- Added "settings" to `valid_tabs` in `ServiceDetailView` with merged env vars context
- Created `_settings_tab.html` with Environment Variables section and Danger Zone (delete)
- Removed env vars and danger zone from `_details_tab.html` (moved to settings)
- Added Settings nav item with gear icon to `nav_service.html` sidebar

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Block sidebar pattern in base.html | Cleanest Django approach -- child templates override the block, no context processor changes needed |

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 627e2da | feat(quick-027): add block sidebar to base.html and fix service links |
| 2 | d7d340f | feat(quick-027): add Settings tab to service view |
