---
phase: quick-012
plan: 01
subsystem: integrations
tags: [github, plugin, authentication, pat, repositories]

dependency-graph:
  requires:
    - Phase 3 plugin infrastructure
  provides:
    - GitHub PAT authentication support
    - Repository listing functionality
    - Dual auth type wizard UI
  affects:
    - Future GitHub-based blueprints
    - Repository selection in deployments

tech-stack:
  added: []
  patterns:
    - Alpine.js conditional form fields
    - Dual authentication routing

key-files:
  created:
    - plugins/github/templates/github/repositories.html
  modified:
    - plugins/github/plugin.py
    - plugins/github/views.py
    - plugins/github/forms.py
    - plugins/github/urls.py
    - plugins/github/templates/github/wizard_auth.html

decisions:
  - id: Q012-01
    title: PAT vs App auth routing in single method
    choice: Route in _get_github_client based on auth_type config key
    rationale: Backwards compatible, single entry point for all operations

metrics:
  duration: 4 min
  completed: 2026-01-23
---

# Quick Task 012: Add Missing GitHub Plugin Functionality

**One-liner:** GitHub plugin now supports both GitHub App and PAT authentication with repository listing UI.

## What Was Built

### 1. PAT Authentication Support

Added Personal Access Token authentication as alternative to GitHub App:

- `_get_github_client_pat()` method for PAT-based authentication
- `_get_github_client()` now routes based on `auth_type` config
- Config schema updated with `auth_type` and `personal_token` fields

### 2. Repository Listing

Implemented repository listing capability:

- `list_repositories()` method returns repo metadata (name, description, language, visibility, etc.)
- `RepositoryListView` displays repos for a connection
- Table view with visibility badges and GitHub links
- Route at `/<uuid>/repositories/`

### 3. Dual Auth Wizard UI

Updated connection wizard for auth type selection:

- Radio button cards for App vs PAT selection
- Alpine.js conditional field visibility
- Separate form sections for each auth type
- Conditional validation based on selected type

## Commits

| Hash | Description |
|------|-------------|
| 0a68366 | Add list_repositories and PAT auth support to GitHub plugin |
| 936c452 | Add RepositoryListView and URL route |
| 9e79581 | Create repository list template |
| db03f8c | Add auth type selection to GitHubAuthForm |
| c2f1bd4 | Update wizard to handle both auth types |
| 30993a6 | Add conditional auth type fields to wizard template |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Status

- [x] Config schema includes auth_type and personal_token fields
- [x] list_repositories method exists on GitHubPlugin
- [x] RepositoryListView accessible at correct URL
- [x] Wizard form has auth_type field with conditional validation
- [x] Template shows/hides fields based on auth type selection

## Files Changed

```
plugins/github/plugin.py          (+73/-5)  - PAT auth, list_repositories
plugins/github/views.py           (+45/-6)  - RepositoryListView, wizard auth handling
plugins/github/forms.py           (+41/-1)  - auth_type field, conditional validation
plugins/github/urls.py            (+1/-0)   - repositories URL
plugins/github/templates/github/repositories.html  (+91 new)
plugins/github/templates/github/wizard_auth.html   (+91/-29)
```

## Usage

### Create PAT Connection

1. Navigate to /integrations/github/create/
2. Select "Personal Access Token" auth type
3. Enter connection name and PAT
4. Complete wizard

### View Repositories

1. Go to connection detail page
2. Click "View Repositories" (once link is added)
3. Or navigate directly to `/integrations/github/<uuid>/repositories/`
