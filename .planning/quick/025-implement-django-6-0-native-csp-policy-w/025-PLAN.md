---
phase: quick-025
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
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
autonomous: true

must_haves:
  truths:
    - "All pages return Content-Security-Policy header"
    - "External CDN scripts (htmx, Alpine.js) load without CSP violations"
    - "All inline scripts execute without CSP violations"
    - "HTMX CSRF configuration and dark mode scripts work correctly"
  artifacts:
    - path: "pathfinder/settings.py"
      provides: "SECURE_CSP config and CSP middleware + context processor"
      contains: "SECURE_CSP"
    - path: "theme/templates/base.html"
      provides: "nonce attributes on all script tags"
      contains: "csp_nonce"
  key_links:
    - from: "django.middleware.csp.ContentSecurityPolicyMiddleware"
      to: "SECURE_CSP setting"
      via: "middleware reads config, generates header with nonce"
    - from: "django.template.context_processors.csp"
      to: "{{ csp_nonce }} in templates"
      via: "context processor provides nonce from request._csp_nonce"
---

<objective>
Enable Django 6.0 native Content-Security-Policy using `django.middleware.csp.ContentSecurityPolicyMiddleware` with nonce-based script execution for all external CDN scripts (htmx, Alpine.js, Alpine Persist) and inline scripts across all templates.

Purpose: Enforce CSP to prevent XSS attacks while allowing legitimate scripts via nonce.
Output: All pages served with CSP header; all scripts tagged with nonce attribute.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@pathfinder/settings.py
@theme/templates/base.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Configure Django 6.0 CSP middleware and policy settings</name>
  <files>pathfinder/settings.py</files>
  <action>
1. Add `"django.middleware.csp.ContentSecurityPolicyMiddleware"` to MIDDLEWARE list. Place it right after `"django.middleware.security.SecurityMiddleware"` (first position after SecurityMiddleware).

2. Add `"django.template.context_processors.csp"` to the TEMPLATES context_processors list (add as last entry). This provides `{{ csp_nonce }}` in all templates.

3. Add SECURE_CSP configuration at the end of the settings file (before the HEALTH_CHECK_INTERVAL line). Import CSP enum at top of file:
   ```python
   from django.utils.csp import CSP
   ```

   Then define the policy:
   ```python
   # Content Security Policy (Django 6.0 native)
   SECURE_CSP = {
       "default-src": [CSP.SELF],
       "script-src": [CSP.SELF, CSP.NONCE, "https://unpkg.com", "https://cdn.jsdelivr.net"],
       "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
       "img-src": [CSP.SELF, "data:"],
       "connect-src": [CSP.SELF],
       "font-src": [CSP.SELF],
       "frame-src": [CSP.NONE],
       "object-src": [CSP.NONE],
       "base-uri": [CSP.SELF],
       "form-action": [CSP.SELF, "https://github.com"],
   }
   ```

   Notes on the policy:
   - `script-src`: NONCE for inline scripts + CDN hosts for external scripts. Both unpkg.com (htmx, Alpine) and cdn.jsdelivr.net (Alpine Persist) needed.
   - `style-src`: UNSAFE_INLINE needed because Tailwind uses inline styles and `[x-cloak]` style is inline.
   - `img-src`: data: needed for potential inline SVGs or data URIs.
   - `form-action`: github.com needed because the GitHub manifest redirect page submits a form to github.com.
   - `frame-src` and `object-src`: NONE to block embedding.
  </action>
  <verify>Run `uv run python -c "import django; import os; os.environ['DJANGO_SETTINGS_MODULE']='pathfinder.settings'; django.setup(); from django.conf import settings; print('CSP:', settings.SECURE_CSP); print('Middleware:', [m for m in settings.MIDDLEWARE if 'csp' in m.lower()]); print('Context processors:', [c for c in settings.TEMPLATES[0]['OPTIONS']['context_processors'] if 'csp' in c])"` -- should print the SECURE_CSP dict, show the CSP middleware, and show the csp context processor.</verify>
  <done>SECURE_CSP setting configured with nonce support, CSP middleware in MIDDLEWARE list, csp context processor in TEMPLATES.</done>
</task>

<task type="auto">
  <name>Task 2: Add nonce attributes to all script tags across all templates</name>
  <files>
    theme/templates/base.html
    core/templates/core/setup/unlock.html
    core/templates/core/auth/login.html
    core/templates/core/services/wizard/step_configuration.html
    core/templates/core/services/wizard/step_repository.html
    core/templates/core/services/wizard/base.html
    core/templates/core/ci_workflows/workflow_detail.html
    core/templates/core/connections/list.html
    core/templates/core/connections/plugins.html
    plugins/github/templates/github/manifest_redirect.html
    plugins/docker/templates/docker/create.html
  </files>
  <action>
Add `nonce="{{ csp_nonce }}"` to every `<script>` tag (both external src and inline) across all templates.

**base.html** (extends nothing, has csp_nonce from context processor):
- Line 10: `<script defer src="https://cdn.jsdelivr.net/npm/@alpinejs/persist@3.x.x/dist/cdn.min.js" nonce="{{ csp_nonce }}"></script>`
- Line 12: `<script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" nonce="{{ csp_nonce }}"></script>`
- Line 15: `<script src="https://unpkg.com/htmx.org@2.0.4" nonce="{{ csp_nonce }}"></script>`
- Line 18: `<script nonce="{{ csp_nonce }}">` (CSRF config)
- Line 23: `<script nonce="{{ csp_nonce }}">` (dark mode)

**Templates that extend base.html** (inherit csp_nonce from context processor automatically):
- `core/services/wizard/step_configuration.html` line 63: `<script nonce="{{ csp_nonce }}">`
- `core/services/wizard/step_repository.html` line 62: `<script nonce="{{ csp_nonce }}">`
- `core/services/wizard/base.html` line 94: `<script nonce="{{ csp_nonce }}">`
- `core/ci_workflows/workflow_detail.html` line 103: `<script nonce="{{ csp_nonce }}">`
- `plugins/github/templates/github/manifest_redirect.html` line 35: `<script nonce="{{ csp_nonce }}">`

**Templates with duplicate Alpine.js CDN loads** (these extend base.html which already loads Alpine, but they load it again in `{% block scripts %}`):
- `plugins/docker/templates/docker/create.html` line 121: `<script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" nonce="{{ csp_nonce }}"></script>`
- `core/connections/list.html` line 163: `<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer nonce="{{ csp_nonce }}"></script>`
- `core/connections/plugins.html` line 104: `<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer nonce="{{ csp_nonce }}"></script>`

**Standalone templates** (do NOT extend base.html, have their own html/head -- csp_nonce is still available from context processor):
- `core/setup/unlock.html` line 9: `<script nonce="{{ csp_nonce }}">document.documentElement.classList.add('dark');</script>`
- `core/auth/login.html` line 9: `<script nonce="{{ csp_nonce }}">document.documentElement.classList.add('dark');</script>`

IMPORTANT: Do NOT change anything else in these files. Only add the `nonce="{{ csp_nonce }}"` attribute to existing script tags.
  </action>
  <verify>
1. Run `uv run python manage.py check` to verify no template syntax errors.
2. Run `uv run python manage.py runserver 0:8111 &` then `curl -sI http://localhost:8111/setup/ | grep -i content-security-policy` to verify CSP header is present and contains a nonce value.
3. Check that the response body contains nonce attributes: `curl -s http://localhost:8111/setup/ | grep -o 'nonce="[^"]*"' | head -3` should show nonce values.
4. Kill the test server.
  </verify>
  <done>All script tags across all templates have nonce="{{ csp_nonce }}" attribute. CSP header is returned with nonce in script-src directive. Pages load without CSP violations.</done>
</task>

</tasks>

<verification>
1. `uv run python manage.py check` passes with no errors
2. Start dev server and verify CSP header present on responses
3. Verify nonce appears in both the CSP header and script tags
4. Verify external scripts (htmx, Alpine) load correctly (CDN hosts whitelisted in script-src)
5. Verify inline scripts execute (nonce matches between header and tag)
</verification>

<success_criteria>
- Content-Security-Policy header present on all HTTP responses
- script-src includes nonce and CDN host allowlist
- All 5 script tags in base.html have nonce attribute
- All inline scripts in child templates have nonce attribute
- All standalone templates (login, unlock) have nonce on their script tags
- Application functions normally with no CSP console errors
</success_criteria>

<output>
After completion, create `.planning/quick/025-implement-django-6-0-native-csp-policy-w/025-SUMMARY.md`
</output>
