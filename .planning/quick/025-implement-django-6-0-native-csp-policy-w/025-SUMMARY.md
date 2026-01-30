---
phase: quick-025
plan: 01
status: complete
duration: 3 min
completed: 2026-01-30
subsystem: security
tags: [csp, django-6, security-headers, xss-prevention]
dependency-graph:
  requires: []
  provides: [content-security-policy, nonce-based-script-execution]
  affects: [any-new-template-with-script-tags]
tech-stack:
  added: []
  patterns: [nonce-based-csp, django-native-csp-middleware]
key-files:
  created: []
  modified:
    - pathfinder/settings.py
    - theme/templates/base.html
    - core/templates/core/setup/unlock.html
    - core/templates/core/auth/login.html
    - core/templates/core/services/wizard/step_configuration.html
    - core/templates/core/services/wizard/step_repository.html
    - core/templates/core/services/wizard/base.html
    - core/templates/core/ci_workflows/workflow_detail.html
    - core/templates/core/connections/list.html
    - core/templates/core/connections/plugins.html
    - plugins/github/templates/github/manifest_redirect.html
    - plugins/docker/templates/docker/create.html
decisions:
  - id: quick-025-01
    description: "Nonce-based CSP with CDN allowlist for script-src"
    rationale: "Nonce provides per-request script authorization; CDN hosts needed for htmx, Alpine.js, Alpine Persist"
metrics:
  tasks: 2/2
  commits: 2
---

# Quick Task 025: Implement Django 6.0 Native CSP Policy Summary

Django 6.0 native CSP middleware with nonce-based script execution for all templates, allowing htmx/Alpine.js CDN scripts and inline scripts via per-request nonce.

## Completed Tasks

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Configure Django 6.0 CSP middleware and policy settings | d7a889c | SECURE_CSP config, CSP middleware, csp context processor |
| 2 | Add nonce attributes to all script tags across templates | cab6d38 | nonce="{{ csp_nonce }}" on all 15+ script tags in 11 templates |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Nonce-based script-src with CDN host allowlist | Nonce authorizes inline scripts per-request; CDN hosts (unpkg.com, cdn.jsdelivr.net) needed for external libraries |
| style-src uses unsafe-inline | Tailwind uses inline styles; [x-cloak] requires inline style rule |
| form-action includes github.com | GitHub manifest redirect page submits form to github.com |
| frame-src and object-src set to 'none' | Block embedding to prevent clickjacking and plugin-based attacks |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- Django system check: passed (0 issues)
- CSP header present on HTTP responses with nonce in script-src directive
- Nonce value appears in both CSP header and script tag attributes
- CDN hosts (unpkg.com, cdn.jsdelivr.net) whitelisted in script-src

## Important Notes for Future Development

Any new template that includes `<script>` tags MUST include `nonce="{{ csp_nonce }}"` on the script tag. The `csp_nonce` variable is available in all templates via the `django.template.context_processors.csp` context processor.
