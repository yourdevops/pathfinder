---
phase: quick-011
plan: 01
subsystem: ui-navigation
tags: [alpine.js, sidebar, navigation, plugins, connections]
key-files:
  modified:
    - core/templates/core/components/nav.html
    - core/templates/core/connections/list.html
    - core/views/connections.py
    - core/views/__init__.py
    - core/urls.py
  created:
    - core/templates/core/connections/plugins.html
decisions:
  - id: quick-011-01
    decision: "Expandable sidebar with Alpine.js x-data toggle"
    rationale: "Simple, no additional plugins needed, auto-expands on relevant pages"
  - id: quick-011-02
    decision: "Add Connection redirects to Plugins page instead of dropdown"
    rationale: "More discoverable, shows all plugins with connection counts, cleaner UX"
metrics:
  duration: "4 min"
  completed: "2026-01-23"
---

# Quick Task 011: Integrations Sidebar Expansion with Plugins Page Summary

**One-liner:** Expandable Integrations nav section with Connections/Plugins sub-items, plus new Plugins management page with search/filter.

## What Was Built

### 1. Expandable Integrations Navigation (nav.html)
- Converted static Integrations link to expandable section using Alpine.js `x-data`
- Parent button toggles expansion with rotating chevron icon
- Two sub-items: Connections and Plugins with proper indentation (pl-11)
- Auto-expands when on any `/connections/*` path
- Active sub-item highlighted with `bg-dark-border/50`

### 2. Plugins List Page (plugins.html + PluginListView)
- New PluginListView in connections.py with plugin data and connection counts
- Search input for filtering plugins by name (Alpine.js client-side)
- Category filter dropdown (All, SCM, Deploy, CI)
- Plugin cards showing:
  - Display name and category badge (color-coded)
  - Connection count
  - "Add Connection" button linking to plugin-specific create
  - "Remove" button (disabled when plugin has active connections)
- Empty state for when no plugins installed

### 3. Connections Page Enhancements (list.html)
- Added search input for filtering connections by name
- Added category filter dropdown (All, SCM, Deploy, Other)
- Connection cards wrapped in Alpine.js x-show for filtering
- "Add Connection" button changed from dropdown to direct link to Plugins page
- Empty state also redirects to Plugins page

## Key Files Modified

| File | Changes |
|------|---------|
| `core/templates/core/components/nav.html` | Expandable Integrations section with sub-items |
| `core/templates/core/connections/list.html` | Search/filter bar, redirect Add Connection |
| `core/templates/core/connections/plugins.html` | New Plugins list page template |
| `core/views/connections.py` | Added PluginListView |
| `core/views/__init__.py` | Export PluginListView |
| `core/urls.py` | Added `connections:plugins` route |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 99c7be3 | feat | Add expandable Integrations nav section |
| 51fad62 | feat | Create Plugins list page with search/filter |
| 6f82061 | feat | Add search/filter to Connections page and redirect Add button |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- [x] Integrations sidebar expands/collapses with chevron animation
- [x] Connections sub-item highlighted when on connections path (not plugins)
- [x] Plugins sub-item highlighted when on plugins path
- [x] Plugins page shows all installed plugins with connection counts
- [x] Search filters plugins by name in real-time
- [x] Category filter shows only matching categories
- [x] Add Connection button on Connections page goes to Plugins page
- [x] Remove button grayed out when plugin has active connections
- [x] Django check passes

## UX Flow

1. User clicks "Integrations" in sidebar -> section expands showing Connections and Plugins
2. Click "Connections" -> shows list with search/filter
3. Click "Add Connection" -> goes to Plugins page
4. Select plugin -> click "Add Connection" -> goes to plugin-specific create wizard
5. Click "Plugins" in sidebar -> shows plugin management with connection counts
