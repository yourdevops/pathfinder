---
phase: quick
plan: 005
type: execute
wave: 1
depends_on: []
files_modified:
  - pathfinder/settings.py
  - core/decorators.py
autonomous: true

must_haves:
  truths:
    - "Templates using {% load humanize %} render without error"
    - "has_system_role() correctly checks JSONField system_roles on SQLite"
    - "Admin users can access admin-protected views"
  artifacts:
    - path: "pathfinder/settings.py"
      provides: "django.contrib.humanize in INSTALLED_APPS"
      contains: "django.contrib.humanize"
    - path: "core/decorators.py"
      provides: "SQLite-compatible system role checking"
      exports: ["has_system_role", "admin_required", "operator_required", "AdminRequiredMixin"]
  key_links:
    - from: "core/templates/**"
      to: "django.contrib.humanize"
      via: "{% load humanize %} template tag"
    - from: "core/decorators.py"
      to: "core/models.py"
      via: "GroupMembership query with Python filtering"
---

<objective>
Fix two runtime errors preventing application from working correctly.

Purpose: Application throws errors on pages using humanize template tags and on any admin-protected view due to SQLite not supporting JSONField contains lookup.
Output: Working application with both issues resolved.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@pathfinder/settings.py
@core/decorators.py
@core/models.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add django.contrib.humanize to INSTALLED_APPS</name>
  <files>pathfinder/settings.py</files>
  <action>
    Add 'django.contrib.humanize' to INSTALLED_APPS list in settings.py.
    Place it with other django.contrib apps (after django.contrib.staticfiles is fine).
    This enables the {% load humanize %} template tag used in environment_detail.html and list.html.
  </action>
  <verify>grep -q "django.contrib.humanize" pathfinder/settings.py</verify>
  <done>django.contrib.humanize is in INSTALLED_APPS</done>
</task>

<task type="auto">
  <name>Task 2: Fix has_system_role for SQLite compatibility</name>
  <files>core/decorators.py</files>
  <action>
    Replace the ORM query using `system_roles__contains` (not supported by SQLite) with a Python-based approach:

    1. Query GroupMembership for user's active groups without the contains filter
    2. Filter in Python by checking if role is in each group's system_roles list

    Updated has_system_role function:
    ```python
    def has_system_role(user, role):
        """Check if user has a specific SystemRole through any group."""
        if not user.is_authenticated:
            return False
        memberships = GroupMembership.objects.filter(
            user=user,
            group__status='active'
        ).select_related('group')
        return any(role in m.group.system_roles for m in memberships)
    ```

    This approach:
    - Fetches all active group memberships for the user
    - Uses select_related to avoid N+1 queries
    - Checks system_roles in Python where list contains works correctly
  </action>
  <verify>
    Run Django shell test:
    python manage.py shell -c "from core.decorators import has_system_role; from core.models import User; u = User.objects.first(); print('Test passed' if has_system_role(u, 'admin') in [True, False] else 'Test failed')"
  </verify>
  <done>has_system_role() works without throwing "contains lookup is not supported on this database backend" error</done>
</task>

</tasks>

<verification>
1. Start dev server: `python manage.py runserver`
2. Login as admin user
3. Navigate to projects list page - should render without humanize error
4. Navigate to any admin-protected page (Users, Groups) - should work without contains lookup error
</verification>

<success_criteria>
- No "humanize is not a registered tag library" error
- No "contains lookup is not supported on this database backend" error
- Admin users can access admin-protected views
- Application runs without runtime errors
</success_criteria>

<output>
After completion, create `.planning/quick/005-fix-humanize-and-jsonfield-contains-errors/005-SUMMARY.md`
</output>
