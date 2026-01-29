---
id: quick-002
type: quick
status: planned
created: 2026-01-22
---

# Quick Task: Fix Input Text Color and Merge Unlock/Register Pages

## Objective

Fix unreadable input text in setup forms and consolidate the two-step setup flow (/setup/unlock/ and /setup/register/) into a single page experience. Also remove the permanent /setup/register/ URL endpoint.

## Context

**Problem 1 - Input text color:**
The `input-field` CSS class in `theme/static_src/src/styles.css` uses `text-dark-text` (light color #f1f5f9). The `@tailwindcss/forms` plugin sets default light backgrounds on form inputs, making light text nearly invisible. Need to explicitly set dark text color for readability.

**Problem 2 - Two-step setup flow:**
Currently the setup flow requires navigating to two separate URLs:
1. `/setup/unlock/` - Enter unlock token
2. `/setup/register/` - Create admin account (after token validated)

This should be a single-page experience where the registration form appears after token validation, without a URL change.

**Problem 3 - Permanent register URL:**
User creation should be admin-only or via AD/SSO. The `/setup/register/` URL should not exist as a permanent endpoint.

## Tasks

<task type="auto">
  <name>Task 1: Fix input text color for dark mode compatibility</name>
  <files>
    - /Users/fandruhin/work/yourdevops/pathfinder/theme/static_src/src/styles.css
  </files>
  <action>
Update the `input-field` component class to use explicit dark text color that works with the form plugin's default light background:

Change from:
```css
.input-field {
  @apply bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text placeholder-dark-muted focus:outline-none focus:ring-2 focus:ring-dark-accent focus:border-transparent;
}
```

To:
```css
.input-field {
  @apply bg-white border border-dark-border rounded-lg px-3 py-2 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-dark-accent focus:border-transparent;
}
```

This uses:
- `bg-white` - explicit white background (matches @tailwindcss/forms default)
- `text-gray-900` - dark text color for readability
- `placeholder-gray-500` - visible but muted placeholder text

After CSS change, rebuild Tailwind:
```bash
cd /Users/fandruhin/work/yourdevops/pathfinder && source venv/bin/activate && python manage.py tailwind build
```
  </action>
  <verify>
Run dev server and verify input fields on /setup/unlock/ and /auth/login/ show black text on white background.
```bash
cd /Users/fandruhin/work/yourdevops/pathfinder && source venv/bin/activate && python manage.py runserver &
sleep 2 && curl -s http://localhost:8000/setup/unlock/ | grep -o 'input-field\|text-gray-900'
```
  </verify>
  <done>Input fields display dark text on light background across all forms (unlock, login, user management).</done>
</task>

<task type="auto">
  <name>Task 2: Merge unlock and register into single-page flow</name>
  <files>
    - /Users/fandruhin/work/yourdevops/pathfinder/core/views/setup.py
    - /Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/setup/unlock.html
    - /Users/fandruhin/work/yourdevops/pathfinder/core/urls.py
  </files>
  <action>
1. **Update UnlockView** to handle both unlock token validation AND admin registration:
   - Add AdminRegistrationForm import
   - On successful token validation (POST), don't redirect - instead re-render the page with registration form
   - Use session variable `unlock_verified` to track state
   - Handle registration POST (detect via form field presence)
   - Move registration logic from AdminRegistrationView into UnlockView

2. **Update unlock.html template** to show conditional forms:
   - If not `unlock_verified`: show unlock token form (current behavior)
   - If `unlock_verified`: show admin registration form (copy from register.html)
   - Keep same visual styling, same card layout

3. **Remove AdminRegistrationView** class from setup.py

4. **Update core/urls.py**:
   - Remove the `path('register/', AdminRegistrationView.as_view(), name='register')` line
   - Remove AdminRegistrationView from imports

5. **Delete register.html template** (no longer needed):
   - /Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/setup/register.html
  </action>
  <verify>
Test the merged flow:
```bash
cd /Users/fandruhin/work/yourdevops/pathfinder && source venv/bin/activate
# Reset database for fresh setup state
rm -f db.sqlite3
python manage.py migrate
# Generate unlock token
mkdir -p secrets && python -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/initialUnlockToken
cat secrets/initialUnlockToken
# Start server and manually test flow at http://localhost:8000/setup/unlock/
python manage.py runserver
```
Verify:
- `/setup/unlock/` shows token form initially
- After valid token, same URL shows registration form
- After registration, redirects to /users/
- `/setup/register/` returns 404
  </verify>
  <done>
- Single URL `/setup/unlock/` handles entire setup flow
- Token validation shows registration form inline (no redirect)
- `/setup/register/` URL no longer exists (404)
- register.html template deleted
  </done>
</task>

<task type="auto">
  <name>Task 3: Update planning docs about user registration</name>
  <files>
    - /Users/fandruhin/work/yourdevops/pathfinder/.planning/PROJECT.md
  </files>
  <action>
Add a note to the Key Decisions table in PROJECT.md:

| Phase | Decision | Rationale |
|-------|----------|-----------|
| quick-002 | No permanent user registration URL | User creation is admin-only via /users/create/ or via AD/SSO integration. Initial admin created during one-time setup flow at /setup/unlock/. |

Also update any mentions of setup flow if they reference /setup/register/.
  </action>
  <verify>
```bash
grep -i "register" /Users/fandruhin/work/yourdevops/pathfinder/.planning/PROJECT.md
grep -i "user.*creation" /Users/fandruhin/work/yourdevops/pathfinder/.planning/PROJECT.md
```
Verify the decision is documented.
  </verify>
  <done>PROJECT.md updated with decision about no permanent user registration URL.</done>
</task>

## Success Criteria

1. Input text in all forms is readable (dark text on light background)
2. Setup flow works entirely at `/setup/unlock/` without any redirect to `/setup/register/`
3. `/setup/register/` URL returns 404
4. Planning docs note that user creation is admin-only (no public registration)

## Files Modified

- `/Users/fandruhin/work/yourdevops/pathfinder/theme/static_src/src/styles.css`
- `/Users/fandruhin/work/yourdevops/pathfinder/core/views/setup.py`
- `/Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/setup/unlock.html`
- `/Users/fandruhin/work/yourdevops/pathfinder/core/urls.py`
- `/Users/fandruhin/work/yourdevops/pathfinder/.planning/PROJECT.md`

## Files Deleted

- `/Users/fandruhin/work/yourdevops/pathfinder/core/templates/core/setup/register.html`
