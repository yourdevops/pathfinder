---
phase: quick-007
plan: 01
subsystem: ui-navigation
tags: [navigation, settings, admin, ui, sidebar]
dependency-graph:
  requires: [01-02, 02-02]
  provides: [settings-section, dedicated-settings-nav]
  affects: [future-settings-pages]
tech-stack:
  added: []
  patterns: [dedicated-section-sidebar, consistent-settings-layout]
key-files:
  created:
    - core/views/settings.py
    - core/templates/core/settings/general.html
    - core/templates/core/settings/user_management.html
    - core/templates/core/settings/audit_logs.html
    - core/templates/core/settings/api_tokens.html
    - core/templates/core/settings/notifications.html
  modified:
    - core/views/__init__.py
    - core/urls.py
    - pathfinder/urls.py
    - core/templates/core/components/nav.html
decisions:
  - id: Q007-01
    choice: Single Settings link in main nav, dedicated sidebar in Settings section
    rationale: Cleaner main navigation, focused settings experience
metrics:
  duration: 4 min
  completed: 2026-01-23
---

# Quick Task 007: UI Navigation Items Arrangement

**One-liner:** Settings consolidated into single nav link leading to dedicated section with 5-item sidebar (General, User Management, Audit & Logs, API & Tokens, Notifications)

## What Was Built

### Settings Section Architecture
- **Main navigation:** Single "Settings" link for admins, replaces nested Settings section
- **Settings sidebar:** Dedicated 5-item sidebar consistent across all settings pages
- **URL structure:** `/settings/`, `/settings/user-management/`, `/settings/audit-logs/`, etc.

### Views Created (`core/views/settings.py`)
1. `GeneralSettingsView` - Pathfinder URL configuration placeholder
2. `UserManagementView` - Links to Users and Groups pages
3. `AuditLogsSettingsView` - Links to audit log viewer
4. `ApiTokensView` - API token management placeholder
5. `NotificationsView` - Notification settings placeholder

### Templates Created (`core/templates/core/settings/`)
Each template features:
- Consistent sidebar navigation with 5 items
- Active section highlighting via `active_section` context variable
- Dark theme styling matching existing design system

**Specific content:**
- `general.html` - Placeholder for Pathfinder Internal/Public URL configuration
- `user_management.html` - Card links to Users and Groups pages with note about future LDAP/SSO
- `audit_logs.html` - Link to existing audit log viewer, placeholder for additional log viewers
- `api_tokens.html` - Placeholder for API token management
- `notifications.html` - Placeholder for notification settings

### URL Changes
- Added `settings_patterns` to `core/urls.py`
- Connected `/settings/` route in `pathfinder/urls.py` with `settings` namespace

### Main Nav Update
- Simplified from nested section (7 elements) to single link
- Maintained admin-only visibility with `{% if is_admin %}`
- Active state highlighting for `/settings/` paths

## Commits

| Commit | Description |
|--------|-------------|
| `e030dd1` | feat(quick-007): add Settings views and URL patterns |
| `0ae1c76` | feat(quick-007): create Settings templates with sidebar navigation |
| `5ea4142` | feat(quick-007): simplify main nav to single Settings link |

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| Q007-01 | Single Settings link in main nav | Reduces main nav clutter, creates focused settings experience |
| Q007-02 | Dedicated sidebar for settings | Consistent pattern with project context navigation (nav_project.html) |
| Q007-03 | active_section context variable | Simple highlighting mechanism without complex template logic |

## Verification

- [x] `python manage.py check` passes
- [x] Settings views created with AdminRequiredMixin
- [x] All 5 templates render with consistent sidebar
- [x] URL patterns defined and connected
- [x] Main nav simplified to single Settings link
- [x] Admin-only visibility preserved

## Deviations from Plan

None - plan executed exactly as written.
