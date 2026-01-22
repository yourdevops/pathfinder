---
phase: quick
plan: 006
type: execute
wave: 1
depends_on: []
files_modified:
  - core/permissions.py
  - core/decorators.py
autonomous: true

must_haves:
  truths:
    - "has_system_role works with SQLite JSONField"
    - "Single source of truth for has_system_role function"
    - "All existing imports continue to work"
  artifacts:
    - path: "core/permissions.py"
      provides: "Canonical has_system_role implementation"
      contains: "def has_system_role"
    - path: "core/decorators.py"
      provides: "Decorators importing from permissions"
      contains: "from .permissions import has_system_role"
  key_links:
    - from: "core/decorators.py"
      to: "core/permissions.py"
      via: "import statement"
      pattern: "from \\.permissions import has_system_role"
---

<objective>
Consolidate duplicate `has_system_role` functions into single SQLite-compatible implementation.

Purpose: Fix the broken `__contains` ORM lookup in permissions.py and eliminate code duplication between decorators.py and permissions.py.

Output: Single `has_system_role` function in `core/permissions.py` using Python filtering (SQLite-compatible), imported by `core/decorators.py`.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@core/permissions.py
@core/decorators.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update permissions.py with SQLite-compatible implementation</name>
  <files>core/permissions.py</files>
  <action>
Replace the current `has_system_role` function (lines 7-15) with the SQLite-compatible version:

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

Key changes:
- Remove `__contains=[role]` lookup (broken on SQLite)
- Use `select_related('group')` for efficiency
- Filter in Python with `any(role in m.group.system_roles for m in memberships)`
  </action>
  <verify>python manage.py shell -c "from core.permissions import has_system_role; from core.models import User; u = User.objects.first(); print('has_system_role test:', has_system_role(u, 'admin') in [True, False])"</verify>
  <done>has_system_role in permissions.py uses Python filtering instead of __contains ORM lookup</done>
</task>

<task type="auto">
  <name>Task 2: Update decorators.py to import from permissions</name>
  <files>core/decorators.py</files>
  <action>
1. Remove the local `has_system_role` function definition (lines 9-17)
2. Add import: `from .permissions import has_system_role`

The file should:
- Keep imports: functools.wraps, django.shortcuts.redirect, django.contrib.messages, django.contrib.auth.decorators.login_required
- Add: `from .permissions import has_system_role`
- Remove: local `has_system_role` function
- Remove: `from .models import GroupMembership` (no longer needed since has_system_role handles it)
- Keep: admin_required, operator_required decorators, AdminRequiredMixin class (they use has_system_role)
  </action>
  <verify>python manage.py shell -c "from core.decorators import has_system_role, admin_required, AdminRequiredMixin; print('decorators import test: OK')"</verify>
  <done>decorators.py imports has_system_role from permissions.py instead of defining its own</done>
</task>

<task type="auto">
  <name>Task 3: Verify integration</name>
  <files></files>
  <action>
Run verification commands to ensure:
1. The has_system_role function works correctly with SQLite
2. All existing imports continue to work
3. The admin role check functions properly

Test with actual database query to confirm no SQLite errors.
  </action>
  <verify>
python manage.py shell -c "
from core.decorators import has_system_role, AdminRequiredMixin
from core.permissions import has_system_role as perm_has_system_role
from core.models import User, Group, GroupMembership

# Verify same function
assert has_system_role is perm_has_system_role, 'Functions should be the same'

# Test with actual query (no SQLite error)
user = User.objects.first()
if user:
    result = has_system_role(user, 'admin')
    print(f'has_system_role(user, admin) = {result}')
print('All integration tests passed')
"
  </verify>
  <done>Integration verified: single has_system_role function works across decorators and permissions modules</done>
</task>

</tasks>

<verification>
1. `python manage.py shell -c "from core.permissions import has_system_role; print('OK')"` - imports without error
2. `python manage.py shell -c "from core.decorators import has_system_role; print('OK')"` - imports without error
3. Both imports refer to the same function
4. No SQLite `__contains` errors when checking system roles
</verification>

<success_criteria>
- Single `has_system_role` implementation in `core/permissions.py`
- `core/decorators.py` imports from `core/permissions.py`
- All existing imports continue to work (backwards compatible)
- No SQLite errors when checking system roles via JSONField
</success_criteria>

<output>
After completion, create `.planning/quick/006-consolidate-has-system-role-sqlite-compat/006-SUMMARY.md`
</output>
