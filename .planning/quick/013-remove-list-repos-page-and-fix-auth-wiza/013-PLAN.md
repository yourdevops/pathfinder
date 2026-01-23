---
phase: quick
plan: 013
type: execute
wave: 1
depends_on: []
files_modified:
  - plugins/github/views.py
  - plugins/github/urls.py
  - plugins/github/templates/github/repositories.html
  - plugins/github/templates/github/wizard_auth.html
autonomous: true

must_haves:
  truths:
    - "Repository list page no longer accessible"
    - "Auth wizard shows only one radio button selected by default"
    - "Switching auth type updates visual selection correctly"
  artifacts:
    - path: "plugins/github/views.py"
      provides: "GitHubConnectionWizard only (RepositoryListView removed)"
    - path: "plugins/github/urls.py"
      provides: "Only create route (repositories route removed)"
    - path: "plugins/github/templates/github/wizard_auth.html"
      provides: "Fixed Alpine.js initialization for auth_type"
  key_links:
    - from: "wizard_auth.html"
      to: "Alpine.js x-model"
      via: "JavaScript initialization"
      pattern: "x-data.*authType"
---

<objective>
Remove the repositories listing page added in quick-012 and fix the auth wizard radio button issue where both options appear selected.

Purpose: Clean up unwanted feature and fix UI bug in GitHub connection wizard
Output: Working auth wizard with correct radio button selection behavior
</objective>

<context>
@.planning/STATE.md
@plugins/github/views.py
@plugins/github/urls.py
@plugins/github/templates/github/wizard_auth.html
@plugins/github/forms.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove repositories listing page</name>
  <files>
    plugins/github/views.py
    plugins/github/urls.py
    plugins/github/templates/github/repositories.html
  </files>
  <action>
    1. In `plugins/github/views.py`:
       - Remove the entire `RepositoryListView` class (lines 89-111)

    2. In `plugins/github/urls.py`:
       - Remove the repositories URL pattern: `path('<uuid:uuid>/repositories/', views.RepositoryListView.as_view(), name='repositories')`
       - Keep only the `create/` route

    3. Delete the template file:
       - Remove `plugins/github/templates/github/repositories.html`
  </action>
  <verify>
    - `grep -r "RepositoryListView" plugins/github/` returns no results
    - `grep -r "repositories" plugins/github/urls.py` returns no results
    - `ls plugins/github/templates/github/repositories.html` fails (file deleted)
  </verify>
  <done>Repository listing page completely removed from GitHub plugin</done>
</task>

<task type="auto">
  <name>Task 2: Fix auth wizard radio button selection issue</name>
  <files>plugins/github/templates/github/wizard_auth.html</files>
  <action>
    The issue is that Django's RadioSelect widget renders HTML radio inputs with `checked` attribute based on form initial value, but the template uses custom radio buttons with Alpine.js `x-model`. The conflict causes both to appear selected.

    Fix line 34: The Alpine.js initialization `x-data="{ authType: '{{ form.auth_type.value|default:'app' }}' }"` should work, but the real issue is the hidden `<input type="radio">` elements inside the labels. These are sr-only (screen reader only) but still participate in form submission.

    The problem: When form loads fresh, `form.auth_type.value` may return empty string `""` not `None`, so the `|default` filter doesn't trigger. Also, the actual HTML radio inputs at lines 65 and 80 have `x-model="authType"` which two-way binds, but on initial load before Alpine initializes, the radio with value matching form's initial could have `checked` attribute from Django.

    Solution: Ensure a reliable initial value by checking both bound value and form initial:

    Change line 34 from:
    ```html
    <div class="card" x-data="{ authType: '{{ form.auth_type.value|default:'app' }}' }">
    ```

    To use the form's initial value reliably. Since `form.auth_type.value` could be empty string on GET request (not None), use a conditional that handles empty string:
    ```html
    <div class="card" x-data="{ authType: '{% if form.auth_type.value %}{{ form.auth_type.value }}{% else %}app{% endif %}' }">
    ```

    This explicitly checks if the value is truthy (not empty string or None) and falls back to 'app'.
  </action>
  <verify>
    - Navigate to http://localhost:8000/integrations/github/create/
    - On initial page load, only the "GitHub App" option shows the checkmark
    - Clicking "Personal Access Token" switches selection (checkmark moves, PAT fields appear)
    - Clicking back to "GitHub App" switches selection back (App fields appear)
  </verify>
  <done>Auth wizard radio buttons show single selection on load and switch correctly</done>
</task>

</tasks>

<verification>
1. GitHub plugin URLs only have `create/` route
2. No references to RepositoryListView in codebase
3. Auth wizard at /integrations/github/create/ loads with single radio selected
4. Auth type switching works correctly with Alpine.js
</verification>

<success_criteria>
- Repository listing page completely removed (view, URL, template)
- Auth wizard shows "GitHub App" selected by default (single selection)
- Switching between auth types updates visual selection correctly
- Form submission still works for both auth types
</success_criteria>

<output>
After completion, create `.planning/quick/013-remove-list-repos-page-and-fix-auth-wiza/013-SUMMARY.md`
</output>
