---
phase: quick-008
plan: 01
subsystem: ui
tags: [navigation, sidebar, settings, projects, layout]
requires: [quick-007]
provides:
  - Settings context-replacing sidebar
  - Consistent p-8 padding across settings pages
  - Clean project detail without duplicate tabs
affects: []
tech-stack:
  added: []
  patterns: [context-aware-sidebar]
key-files:
  created:
    - core/templates/core/components/nav_settings.html
  modified:
    - core/context_processors.py
    - theme/templates/base.html
    - core/templates/core/settings/general.html
    - core/templates/core/settings/user_management.html
    - core/templates/core/settings/audit_logs.html
    - core/templates/core/settings/api_tokens.html
    - core/templates/core/settings/notifications.html
    - core/templates/core/projects/detail.html
    - core/templates/core/projects/_services_tab.html
    - core/templates/core/projects/_environments_tab.html
    - core/templates/core/projects/_members_tab.html
decisions: []
metrics:
  duration: 3 min
  completed: 2026-01-23
---

# Quick Task 008: Fix Settings and Projects UI Sidebar Replacement

**One-liner:** AWS-style context-replacing sidebar for Settings, consistent padding, and cleaned up project detail layout.

## Changes Made

### 1. Settings Context Detection and Sidebar Component
- Added `in_settings_context` detection to `navigation_context` context processor
- Created `nav_settings.html` reusable sidebar component with:
  - Back to Dashboard link
  - Settings header with description
  - All 5 settings nav items with icons (General, User Management, Audit & Logs, API & Tokens, Notifications)
  - User section at bottom
- Updated `base.html` with three-way conditional: settings context > project context > main nav

### 2. Simplified Settings Templates
- Removed 51 lines of duplicate sidebar code from all 5 settings templates
- Changed from `flex min-h-screen` with embedded sidebar to simple `p-8` wrapper
- All settings pages now have consistent padding matching Users page

### 3. Project Detail Cleanup
- Removed redundant tab navigation from project detail header (sidebar already has tabs)
- Changed padding from `p-6` to `p-8` for consistency
- Reduced empty state icons from `w-16 h-16` to `w-12 h-12` in all tab templates

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add settings context and sidebar | fcdd594 | context_processors.py, nav_settings.html, base.html |
| 2 | Simplify settings templates | c5f8692 | 5 settings templates |
| 3 | Fix project detail | 22deebd | detail.html, 3 tab templates |

## Verification

All success criteria met:
- [x] Settings pages show ONLY settings sidebar (context-replacing, like AWS)
- [x] Settings content has consistent p-8 padding matching Users page
- [x] Project detail has NO redundant tab navigation in header
- [x] Empty state icons are w-12 h-12 (not giant w-16 h-16)
- [x] All navigation still works (sidebar links, HTMX tab switching)

## Deviations from Plan

None - plan executed exactly as written.
