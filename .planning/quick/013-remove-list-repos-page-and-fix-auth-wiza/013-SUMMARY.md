---
phase: quick-013
plan: 01
subsystem: integrations
tags: [github, plugin, wizard, alpine.js, cleanup]

dependency-graph:
  requires:
    - quick-012 (GitHub plugin functionality)
  provides:
    - Fixed GitHub auth wizard UI
    - Cleaned up unused repository listing feature
  affects:
    - GitHub connection creation flow

tech-stack:
  added: []
  patterns:
    - Django template conditional syntax for Alpine.js initialization

key-files:
  created: []
  modified:
    - plugins/github/views.py
    - plugins/github/urls.py
    - plugins/github/templates/github/wizard_auth.html
  deleted:
    - plugins/github/templates/github/repositories.html

decisions:
  - id: Q013-01
    title: Alpine.js initialization for radio button default
    choice: Use explicit {% if %} template tag instead of |default filter
    rationale: Django |default filter does not treat empty string as falsy, causing both options to appear selected

metrics:
  duration: 2 min
  completed: 2026-01-23
---

# Quick Task 013: Remove List Repos Page and Fix Auth Wizard

**One-liner:** Removed unwanted repository listing page and fixed Alpine.js radio button initialization bug in GitHub auth wizard.

## What Was Fixed

### 1. Removed Repository Listing Page

The repository listing page added in quick-012 was not needed and has been removed:

- Deleted `RepositoryListView` class from `views.py`
- Removed `<uuid>/repositories/` URL pattern from `urls.py`
- Deleted `repositories.html` template
- Removed unused `TemplateView` import

### 2. Fixed Auth Wizard Radio Button Bug

The authentication type radio buttons appeared to have both options selected on initial load:

**Root cause:** Django's `|default` filter does not treat empty string as falsy. When `form.auth_type.value` returns `""` (empty string) on GET request, the filter passes it through instead of falling back to `'app'`.

**Fix:** Changed from:
```html
x-data="{ authType: '{{ form.auth_type.value|default:'app' }}' }"
```

To explicit conditional:
```html
x-data="{ authType: '{% if form.auth_type.value %}{{ form.auth_type.value }}{% else %}app{% endif %}' }"
```

This ensures Alpine.js initializes with `'app'` when the form value is empty, resulting in only the GitHub App option showing the checkmark on initial load.

## Commits

| Hash | Description |
|------|-------------|
| 11d6e7c | Remove repositories listing page (view, URL, template) |
| 1f50cda | Fix auth wizard radio button selection issue |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Status

- [x] `RepositoryListView` removed from views.py
- [x] `repositories` URL pattern removed from urls.py
- [x] `repositories.html` template deleted
- [x] Auth wizard uses explicit conditional for Alpine.js initialization
- [x] Django check passes

## Files Changed

```
plugins/github/views.py           (-24 lines)  - Removed RepositoryListView
plugins/github/urls.py            (-1 line)    - Removed repositories URL
plugins/github/templates/github/repositories.html  (deleted)
plugins/github/templates/github/wizard_auth.html   (1 line changed)
```
