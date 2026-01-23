---
phase: quick-007
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templates/core/components/nav.html
  - core/templates/core/settings/general.html
  - core/templates/core/settings/user_management.html
  - core/templates/core/settings/audit_logs.html
  - core/templates/core/settings/api_tokens.html
  - core/templates/core/settings/notifications.html
  - core/views/settings.py
  - core/views/__init__.py
  - core/urls.py
autonomous: true

must_haves:
  truths:
    - "Admin users see Settings link in navbar that navigates to /settings/"
    - "Settings page has sidebar with 5 items: General, User Management, Audit & Logs, API & Tokens, Notifications"
    - "Each settings sub-page renders with correct sidebar highlighting"
    - "User Management page shows Users/Groups links or tabs"
  artifacts:
    - path: "core/views/settings.py"
      provides: "Settings views for all sub-pages"
      exports: ["GeneralSettingsView", "UserManagementView", "AuditLogsSettingsView", "ApiTokensView", "NotificationsView"]
    - path: "core/templates/core/settings/general.html"
      provides: "General settings placeholder page"
    - path: "core/urls.py"
      provides: "Settings URL patterns"
      contains: "settings_patterns"
  key_links:
    - from: "core/templates/core/components/nav.html"
      to: "/settings/"
      via: "href link"
      pattern: "url 'settings:general'"
---

<objective>
Restructure UI navigation to make Settings a top-level navbar item leading to a dedicated Settings section with its own sidebar navigation.

Purpose: Improve navigation UX by consolidating settings into a dedicated area with consistent sidebar navigation, rather than nesting under main nav.

Output: Settings page structure with General, User Management, Audit & Logs, API & Tokens, and Notifications sub-pages.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@core/templates/core/components/nav.html
@core/views/placeholders.py
@core/urls.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Settings views and URL patterns</name>
  <files>
    core/views/settings.py
    core/views/__init__.py
    core/urls.py
  </files>
  <action>
Create `core/views/settings.py` with:
- `GeneralSettingsView` - renders general.html with placeholder content for "DevSSP Internal/Public URLs" settings
- `UserManagementView` - renders user_management.html with links to existing Users and Groups pages
- `AuditLogsSettingsView` - renders audit_logs.html (can link to existing audit:list or be placeholder)
- `ApiTokensView` - renders api_tokens.html placeholder
- `NotificationsView` - renders notifications.html placeholder

All views should:
- Inherit from LoginRequiredMixin and AdminRequiredMixin
- Use template pattern `core/settings/{name}.html`

Add to `core/views/__init__.py`:
- Import and export all 5 settings views

Add to `core/urls.py`:
- Create `settings_patterns` list with routes:
  - `''` -> GeneralSettingsView (name='general')
  - `'user-management/'` -> UserManagementView (name='user_management')
  - `'audit-logs/'` -> AuditLogsSettingsView (name='audit_logs')
  - `'api-tokens/'` -> ApiTokensView (name='api_tokens')
  - `'notifications/'` -> NotificationsView (name='notifications')
  </action>
  <verify>
Run: `python manage.py check` - no errors
Grep for `settings_patterns` in urls.py confirms it exists
  </verify>
  <done>Settings views module exists with 5 views, URL patterns defined</done>
</task>

<task type="auto">
  <name>Task 2: Create Settings templates with sidebar navigation</name>
  <files>
    core/templates/core/settings/general.html
    core/templates/core/settings/user_management.html
    core/templates/core/settings/audit_logs.html
    core/templates/core/settings/api_tokens.html
    core/templates/core/settings/notifications.html
  </files>
  <action>
Create `core/templates/core/settings/` directory.

Create base structure for each template that:
1. Extends "base.html"
2. Includes a settings-specific sidebar with 5 navigation items:
   - General (links to settings:general)
   - User Management (links to settings:user_management)
   - Audit & Logs (links to settings:audit_logs)
   - API & Tokens (links to settings:api_tokens)
   - Notifications (links to settings:notifications)
3. Uses same sidebar styling as nav_project.html (fixed left sidebar, content offset)
4. Highlights current section based on active page

Template content:

**general.html**:
- Title: "General Settings"
- Placeholder card: "DevSSP URLs configuration coming soon"
- Note about Internal URL and Public URL settings

**user_management.html**:
- Title: "User Management"
- Two cards or sections linking to:
  - Users page ({% url 'users:list' %}) with user icon
  - Groups page ({% url 'groups:list' %}) with group icon
- Note: "LDAP/SSO configuration coming in future updates"

**audit_logs.html**:
- Title: "Audit & Logs"
- Either embed audit list or link to {% url 'audit:list' %}
- Placeholder for additional log viewers

**api_tokens.html**:
- Title: "API & Tokens"
- Placeholder: "API token management coming soon"

**notifications.html**:
- Title: "Notifications"
- Placeholder: "Notification settings coming soon"

Use consistent Tailwind styling matching existing dark theme (bg-dark-surface, text-dark-text, etc.)
  </action>
  <verify>
All 5 template files exist in core/templates/core/settings/
Templates contain sidebar navigation structure
  </verify>
  <done>Settings templates created with sidebar navigation</done>
</task>

<task type="auto">
  <name>Task 3: Update main nav.html to link Settings to dedicated page</name>
  <files>
    core/templates/core/components/nav.html
    ssp/urls.py
  </files>
  <action>
Update `core/templates/core/components/nav.html`:

Replace the entire "Settings Section (admin-only)" block (lines 36-93) with a single Settings link:

```html
<!-- Settings (admin-only) -->
{% if is_admin %}
<div class="mt-6 pt-6 border-t border-dark-border">
    <a href="{% url 'settings:general' %}" class="flex items-center px-3 py-2 rounded-lg text-dark-text hover:bg-dark-border/50 transition-colors {% if 'settings' in request.path %}bg-dark-border{% endif %}">
        <svg class="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        Settings
    </a>
</div>
{% endif %}
```

Update `ssp/urls.py` (main project URLs):
- Import settings_patterns from core.urls
- Add path: `path('settings/', include((settings_patterns, 'settings')))`
  </action>
  <verify>
Run local server: `python manage.py runserver`
- As admin, see single "Settings" link in sidebar
- Click Settings -> navigates to /settings/
- Settings page shows sidebar with 5 items
  </verify>
  <done>Main nav simplified, Settings routes to dedicated page with its own sidebar</done>
</task>

</tasks>

<verification>
1. `python manage.py check` passes
2. As admin user:
   - Main sidebar shows single "Settings" link (not nested items)
   - Clicking Settings goes to /settings/ (General Settings page)
   - Settings page has sidebar with: General, User Management, Audit & Logs, API & Tokens, Notifications
   - Each settings sub-page highlights correct sidebar item
   - User Management page links to existing Users and Groups pages
3. As non-admin user:
   - Settings link not visible in main sidebar
</verification>

<success_criteria>
- Settings is a top-level navbar item for admins
- Settings section has its own dedicated sidebar navigation
- All 5 settings sub-pages accessible and render correctly
- User Management provides access to existing Users/Groups functionality
- Navigation state (highlighting) works correctly on all pages
</success_criteria>

<output>
After completion, create `.planning/quick/007-ui-navigation-items-arrangement/007-SUMMARY.md`
</output>
