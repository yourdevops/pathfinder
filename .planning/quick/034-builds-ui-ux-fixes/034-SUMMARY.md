---
phase: quick-034
plan: 01
subsystem: builds-ui
tags: [ui, ux, htmx, alpine, builds]

dependency_graph:
  requires:
    - 06-02 (Build History UI)
  provides:
    - Sortable builds table
    - Search by commit SHA/message
    - Expandable build details rows
  affects:
    - Phase 7 deployment views (may reuse patterns)

tech_stack:
  patterns:
    - Alpine.js expandable rows with x-data scope per tbody
    - HTMX search with 300ms debounce and hx-include
    - Sortable table headers with visual indicators

file_tracking:
  modified:
    - core/templates/core/services/_builds_tab.html
    - core/templates/core/services/_build_row.html
    - core/views/services.py
  created:
    - core/templates/core/services/_build_row_expanded.html

decisions:
  - key: "per-build-tbody-alpine"
    choice: "Wrap each build in separate tbody with x-data for Alpine.js scope"
    rationale: "Allows expand/collapse state per row without complex parent scope management"
  - key: "author-avatar-alt-empty"
    choice: "Set img alt='' for avatar instead of author name"
    rationale: "Author name already displayed as text; prevents visual duplication if alt renders"
  - key: "expand-collapses-on-refresh"
    choice: "Auto-refresh (5s) resets expansion state"
    rationale: "Acceptable UX for changing data; morph extension could preserve but adds complexity"

metrics:
  duration: 4 min
  completed: 2026-02-03
---

# Quick Task 034: Builds UI/UX Fixes Summary

Sortable, searchable builds table with expandable rows showing status-specific details.

## What Changed

### View Changes (core/views/services.py)

Added sorting and search support to the builds tab:

```python
# Search filter
search_query = self.request.GET.get("q", "").strip()
if search_query:
    builds_qs = builds_qs.filter(
        Q(commit_sha__icontains=search_query) | Q(commit_message__icontains=search_query)
    )

# Sorting (default: newest first)
sort_by = self.request.GET.get("sort", "-started_at")
valid_sorts = ["started_at", "-started_at", "status", "-status", "duration_seconds", "-duration_seconds"]
```

### Template Changes

**_builds_tab.html:**
- Added search input with 300ms debounce
- Made Status, Started, Duration headers clickable for sorting
- Added sort direction indicators (up/down arrows)
- Removed Actions column (7 -> 6 columns)
- Changed tbody structure to per-build for Alpine.js scope
- Updated auto-refresh to include sort and search params

**_build_row.html:**
- Made row clickable (`@click="expanded = !expanded"`)
- Added cursor-pointer class
- Added chevron indicator that rotates when expanded
- Removed Actions column td
- Fixed author avatar alt attribute (was showing name twice)

**_build_row_expanded.html (new):**
- Expandable details section with `x-show="expanded" x-collapse`
- Status-specific content:
  - Failed: Red alert box with link to GitHub logs
  - Cancelled: Gray alert box with context
  - Running/Pending: Blue alert with progress indicator
  - Success: Green alert with artifact info
- Timing details grid (Started, Completed, Commit)
- GitHub link moved here from Actions column

## Deviations from Plan

None - plan executed exactly as written.

## Verification

All success criteria met:
- [x] Author name appears exactly once per build row
- [x] Table has 6 columns (Actions removed)
- [x] Default sort is newest first (started_at descending)
- [x] Clicking column headers toggles sort with visual indicator
- [x] Search field filters by commit SHA or message
- [x] Clicking any row expands to show build details
- [x] Expanded section shows: external link, artifact ref (if any), timing details
- [x] Failed/cancelled builds show status context in expanded section
- [x] All filters (status, sort, search) work together and persist through pagination
