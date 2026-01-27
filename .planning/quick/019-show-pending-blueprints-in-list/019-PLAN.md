---
type: quick
task: 019
title: Show pending blueprints in list view
files_modified:
  - core/views/blueprints.py
  - core/templates/core/blueprints/list.html
  - core/urls.py
---

<objective>
Make pending blueprints visible and manageable in the blueprint list view.

Purpose: Stuck blueprint registrations (where sync failed or never completed) block re-registration with the same URL and are invisible to users. This change makes them visible and deletable.

Output: Updated list view showing pending blueprints with delete capability for operators.
</objective>

<context>
@core/views/blueprints.py
@core/templates/core/blueprints/list.html
@core/urls.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update view and add delete endpoint</name>
  <files>core/views/blueprints.py, core/urls.py</files>
  <action>
1. In BlueprintListView.get():
   - Remove the `.exclude(sync_status='pending')` filter (line 27-28)
   - Keep the rest of the query as-is

2. Add BlueprintDeleteView class:
```python
class BlueprintDeleteView(OperatorRequiredMixin, View):
    """Delete a blueprint (used for stuck pending registrations)."""

    def post(self, request, pk):
        blueprint = get_object_or_404(Blueprint, pk=pk)
        blueprint_name = blueprint.name or blueprint.git_url
        blueprint.delete()
        messages.success(request, f'Blueprint "{blueprint_name}" deleted.')
        return redirect('blueprints:list')
```

3. In core/urls.py, add import for BlueprintDeleteView and add URL pattern:
   - Add to imports: `BlueprintDeleteView`
   - Add to blueprints_patterns before the `<dns:blueprint_name>/` pattern:
   ```python
   path('<int:pk>/delete/', BlueprintDeleteView.as_view(), name='delete'),
   ```

Note: Use pk (int) not blueprint_name because pending blueprints have empty names.
  </action>
  <verify>
Run: `python manage.py check` - no errors
Verify import added and URL pattern resolves
  </verify>
  <done>BlueprintDeleteView exists and accepts POST to /blueprints/{pk}/delete/</done>
</task>

<task type="auto">
  <name>Task 2: Update list template for pending blueprints</name>
  <files>core/templates/core/blueprints/list.html</files>
  <action>
Update the template to handle pending blueprints gracefully:

1. In the Name column (line ~99-112), handle empty names and pending state:
```html
<td class="px-4 py-3">
    <div class="flex items-center gap-2">
        {% if item.blueprint.name %}
        <a href="{% url 'blueprints:detail' blueprint_name=item.blueprint.name %}"
           class="font-medium text-dark-text hover:text-dark-accent transition-colors"
           {% if not item.is_available %}title="Requires {{ item.required_plugins|join:', ' }} connection"{% endif %}>
            {{ item.blueprint.name }}
        </a>
        {% else %}
        <span class="font-medium text-dark-muted italic">Registering...</span>
        {% endif %}
    </div>
    {% if item.blueprint.description %}
    <div class="text-sm text-dark-muted mt-0.5 truncate max-w-md">
        {{ item.blueprint.description|truncatechars:80 }}
    </div>
    {% elif item.blueprint.sync_status == 'pending' %}
    <div class="text-sm text-dark-muted mt-0.5 truncate max-w-md">
        {{ item.blueprint.git_url }}
    </div>
    {% endif %}
</td>
```

2. Add delete button in the Status column for pending/error blueprints (operators only):
After the sync status badges (line ~142-165), add a delete form:
```html
{% if can_manage and item.blueprint.sync_status in 'pending,error' %}
<form method="post" action="{% url 'blueprints:delete' pk=item.blueprint.pk %}"
      class="inline-block ml-2"
      onsubmit="return confirm('Delete this blueprint registration?');">
    {% csrf_token %}
    <button type="submit"
            class="text-red-400 hover:text-red-300 transition-colors"
            title="Delete blueprint">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
    </button>
</form>
{% endif %}
```

3. For the x-show filter (line ~91-96), pending blueprints should show when showUnavailable is true:
Update the data-available attribute assignment (line 90):
- Pending blueprints are "unavailable" so they only show with the toggle
Change line 90:
```html
data-available="{{ item.is_available|yesno:'true,false' }}"
```
to also mark pending as unavailable (handled automatically since pending blueprints have no deploy_plugins synced, so is_available_globally returns False - no change needed here)

4. Add visual distinction for pending rows - update line 87:
```html
<tr class="table-row align-top {% if not item.is_available %}opacity-50{% endif %} {% if item.blueprint.sync_status == 'pending' %}bg-yellow-500/5{% endif %}"
```
  </action>
  <verify>
Run dev server, navigate to /blueprints/
- Any pending blueprints should appear (with "Show unavailable" toggle or visible by default)
- Pending blueprints show "Registering..." instead of empty name
- Pending blueprints show git_url as description
- Delete button appears for pending/error blueprints (operator only)
  </verify>
  <done>
- Pending blueprints visible in list with muted "Registering..." label
- Git URL shown for context on pending entries
- Delete button available for operators to clean up stuck registrations
  </done>
</task>

</tasks>

<verification>
1. `python manage.py check` passes
2. Create a stuck pending blueprint manually (or have one from failed registration)
3. Visit /blueprints/ - pending blueprint visible
4. Click delete on pending blueprint - redirects to list with success message
5. Verify normal blueprints still work (click through to detail page)
</verification>

<success_criteria>
- Pending blueprints appear in list view (visible when "Show unavailable" toggled)
- Pending blueprints display "Registering..." with git_url for identification
- Operators can delete pending/error blueprints via delete button
- Normal blueprint functionality unchanged
</success_criteria>
