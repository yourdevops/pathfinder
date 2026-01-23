---
phase: 010-fix-integrations-page-permissions-and-ac
plan: 010
type: execute
wave: 1
depends_on: []
files_modified:
  - core/permissions.py
  - core/views/connections.py
  - core/templates/core/connections/list.html
  - core/templates/core/connections/_connection_card.html
  - theme/static_src/src/styles.css
  - theme/templates/base.html
autonomous: true

must_haves:
  truths:
    - "Error messages display with red border and background for visibility"
    - "Admin users can access all connection pages (list, detail, manage)"
    - "Operator users can access all connection pages (list, detail, manage)"
    - "Auditor users can view connection pages (list, detail) but NOT manage"
    - "Authenticated users can view connections list but NOT detail pages"
    - "Authenticated users see connection tiles but tile links are disabled for non-privileged users"
  artifacts:
    - path: "core/permissions.py"
      provides: "Updated OperatorRequiredMixin with admin fallback, new read-only mixins"
    - path: "core/views/connections.py"
      provides: "Views with proper permission mixins"
    - path: "theme/static_src/src/styles.css"
      provides: "Error message styling class"
  key_links:
    - from: "core/permissions.py"
      to: "core/views/connections.py"
      via: "mixin import and usage"
---

<objective>
Fix integrations page (connections) permissions and access control with proper error styling.

Purpose: Currently the OperatorRequiredMixin blocks admins (only checks operator role) and all connection views require operator access. Need to implement tiered access where any authenticated user can see the list, but management requires operator/admin.

Output: Updated permission mixins, connection views with proper access control, and styled error messages.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@core/permissions.py
@core/views/connections.py
@core/templates/core/connections/list.html
@core/templates/core/connections/_connection_card.html
@theme/static_src/src/styles.css
@theme/templates/base.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add error message styling and fix OperatorRequiredMixin</name>
  <files>
    - theme/static_src/src/styles.css
    - core/permissions.py
  </files>
  <action>
1. In `theme/static_src/src/styles.css`, add error message styling class in the @layer components section:

```css
.message-error {
  @apply bg-red-500/20 border-red-500 text-red-400;
}
```

2. In `core/permissions.py`, fix `OperatorRequiredMixin` to also allow admin role (matching the decorator pattern from decorators.py):

```python
class OperatorRequiredMixin:
    """Mixin that requires user to have 'operator' or 'admin' system role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (has_system_role(request.user, 'admin') or has_system_role(request.user, 'operator')):
            messages.error(request, 'You need operator permissions to access this page.')
            return redirect('projects:list')
        return super().dispatch(request, *args, **kwargs)
```

3. Add new permission mixins in `core/permissions.py` for the tiered access model:

```python
class IntegrationsReadMixin:
    """Mixin for read-only integrations access (admin, operator, or auditor)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (has_system_role(request.user, 'admin') or
                has_system_role(request.user, 'operator') or
                has_system_role(request.user, 'auditor')):
            messages.error(request, 'You need operator or auditor permissions to view connection details.')
            return redirect('connections:list')
        return super().dispatch(request, *args, **kwargs)
```
  </action>
  <verify>
    source venv/bin/activate && python -c "from core.permissions import OperatorRequiredMixin, IntegrationsReadMixin; print('Imports OK')"
  </verify>
  <done>
    - OperatorRequiredMixin allows both admin and operator roles
    - IntegrationsReadMixin exists for read-only access (admin, operator, auditor)
    - Error message CSS class defined
  </done>
</task>

<task type="auto">
  <name>Task 2: Update connection views with tiered permission model</name>
  <files>
    - core/views/connections.py
    - core/templates/core/connections/list.html
    - core/templates/core/connections/_connection_card.html
  </files>
  <action>
1. In `core/views/connections.py`, update imports and view mixins:

```python
from core.permissions import OperatorRequiredMixin, IntegrationsReadMixin, has_system_role
```

2. Update views with tiered permissions:
   - `ConnectionListView`: Remove OperatorRequiredMixin (keep only LoginRequiredMixin)
     - Any authenticated user can see the list
   - `ConnectionDetailView`: Use IntegrationsReadMixin instead of OperatorRequiredMixin
     - Admin, operator, auditor can see details
   - `ConnectionTestView`, `ConnectionDeleteView`, `ConnectionCreateDispatchView`: Keep OperatorRequiredMixin
     - Only admin/operator can manage

3. In `ConnectionListView.get_context_data()`, add context variable for template permission checks:
```python
# Add permission context
context['can_manage'] = (
    has_system_role(self.request.user, 'admin') or
    has_system_role(self.request.user, 'operator')
)
context['can_view_details'] = (
    context['can_manage'] or
    has_system_role(self.request.user, 'auditor')
)
```

4. In `core/templates/core/connections/list.html`:
   - Wrap "Add Connection" dropdown button in `{% if can_manage %}...{% endif %}`
   - Keep both instances of the button (header and empty state) wrapped

5. In `core/templates/core/connections/_connection_card.html`:
   - Conditionally render the link based on `can_view_details`:
     - If can_view_details: Link to detail page as before
     - If NOT can_view_details: Show connection name as plain text (no link)
   - Hide "Test" and "View" action buttons if NOT can_manage (Test) / can_view_details (View)

Replace the connection name anchor tag:
```html
{% if can_view_details %}
<a href="{% url 'connections:detail' uuid=connection.uuid %}" class="font-medium text-dark-text hover:text-dark-accent transition-colors">
    {{ connection.name }}
</a>
{% else %}
<span class="font-medium text-dark-text">{{ connection.name }}</span>
{% endif %}
```

For action buttons at bottom:
```html
<div class="flex items-center gap-2">
    {% if can_manage %}
    <button hx-post="{% url 'connections:test' uuid=connection.uuid %}"
            hx-target="#health-status-{{ connection.uuid }}"
            hx-swap="outerHTML"
            class="text-xs px-2 py-1 text-dark-muted hover:text-dark-text hover:bg-dark-border/50 rounded transition-colors">
        Test
    </button>
    {% endif %}
    {% if can_view_details %}
    <a href="{% url 'connections:detail' uuid=connection.uuid %}"
       class="text-xs px-2 py-1 text-dark-muted hover:text-dark-text hover:bg-dark-border/50 rounded transition-colors">
        View
    </a>
    {% endif %}
</div>
```
  </action>
  <verify>
    source venv/bin/activate && python manage.py check && python -c "from core.views.connections import ConnectionListView, ConnectionDetailView; print('Views OK')"
  </verify>
  <done>
    - ConnectionListView accessible to all authenticated users
    - ConnectionDetailView accessible to admin, operator, auditor
    - Management views (test, delete, create) restricted to admin/operator
    - Templates conditionally show/hide links and actions based on permissions
  </done>
</task>

<task type="auto">
  <name>Task 3: Build CSS and update base template</name>
  <files>
    - theme/static/css/dist/styles.css (generated)
    - theme/templates/base.html
  </files>
  <action>
1. In `theme/templates/base.html`, update the messages rendering to use the new error styling. Change the message div class from:
```html
<div class="card mb-2 {% if message.tags %}{{ message.tags }}{% endif %}">
```
To:
```html
<div class="card mb-2 {% if message.tags == 'error' %}message-error{% endif %}">
```

2. Rebuild Tailwind CSS:
```bash
python manage.py tailwind build
```

3. Collect static files:
```bash
python manage.py collectstatic --noinput
```
  </action>
  <verify>
    grep -q "message-error" theme/static/css/dist/styles.css && echo "CSS built with message-error class"
  </verify>
  <done>
    - Error messages display with red background/border styling
    - CSS rebuilt with new component class
    - Static files collected
  </done>
</task>

</tasks>

<verification>
1. Run Django checks: `python manage.py check`
2. Import verification: `python -c "from core.permissions import OperatorRequiredMixin, IntegrationsReadMixin; from core.views.connections import ConnectionListView"`
3. CSS includes message-error class: `grep "message-error" theme/static/css/dist/styles.css`
</verification>

<success_criteria>
- OperatorRequiredMixin allows admin users (admin beats operator)
- Authenticated users can view connections list page
- Only admin/operator/auditor can view connection details
- Only admin/operator can manage connections (test, delete, create)
- Connection cards show plain text names for non-privileged users (no detail links)
- Error messages display with red border and background
</success_criteria>

<output>
After completion, create `.planning/quick/010-fix-integrations-page-permissions-and-ac/010-SUMMARY.md`
</output>
