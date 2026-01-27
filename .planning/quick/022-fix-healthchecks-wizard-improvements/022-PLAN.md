---
phase: quick-022
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/views/connections.py
  - core/urls.py
  - core/views/services.py
  - core/forms/services.py
  - core/templates/core/services/list.html
  - core/templates/core/services/wizard/base.html
autonomous: true

must_haves:
  truths:
    - "Health checks run automatically when worker is running"
    - "User can create service from Services list page with one click"
    - "All synced blueprints appear in wizard selector"
    - "Wizard content has proper padding from sidebar"
  artifacts:
    - path: "core/views/connections.py"
      provides: "Startup health check scheduling"
    - path: "core/urls.py"
      provides: "Global wizard URL"
    - path: "core/templates/core/services/list.html"
      provides: "Create Service button"
    - path: "core/templates/core/services/wizard/base.html"
      provides: "Fixed padding"
---

<objective>
Fix four issues: healthcheck scheduling, wizard accessibility, blueprint visibility, and wizard padding.

Purpose: Improve UX by making service creation easier and fixing background task scheduling
Output: Working healthchecks, one-click wizard access, visible blueprints, proper UI padding
</objective>

<context>
@.planning/STATE.md
@core/views/connections.py
@core/views/services.py
@core/forms/services.py
@core/urls.py
@core/templates/core/services/list.html
@core/templates/core/services/wizard/base.html
@core/tasks.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix healthcheck scheduling on worker startup</name>
  <files>core/views/connections.py, core/tasks.py</files>
  <action>
The health checks are not being scheduled because `schedule_health_checks()` is never called.
The django-tasks library doesn't have built-in periodic scheduling.

Solution: Schedule health checks when connection detail page is viewed (lazy scheduling).
Add a utility function that schedules health checks if not recently scheduled.

In core/tasks.py, add a function that:
1. Checks if health checks have been scheduled in the last HEALTH_CHECK_INTERVAL seconds
2. Uses a SiteConfiguration field or simple cache check
3. If not scheduled, calls schedule_health_checks.enqueue()

Better approach: Add to ConnectionListView.get_queryset() or a middleware to schedule on first connection view.

Actually, simplest fix: When ConnectionListView or ConnectionDetailView is accessed, check if any connection needs health check (last_health_check is None or older than HEALTH_CHECK_INTERVAL), and enqueue a check for those connections.

In core/views/connections.py ConnectionListView.get_context_data():
- Import check_connection_health from core.tasks
- Query connections where last_health_check is None or older than 15 minutes (HEALTH_CHECK_INTERVAL)
- For each such connection, enqueue check_connection_health(connection.id)
- Limit to first 5 to avoid flooding on initial page load

This provides "lazy" health check scheduling without needing cron/periodic tasks.
  </action>
  <verify>
1. Navigate to connections list page
2. Check worker logs - should see health check tasks being processed
3. Refresh page - connections should show updated health status
  </verify>
  <done>Health checks are automatically enqueued when connections page is viewed</done>
</task>

<task type="auto">
  <name>Task 2: Add global wizard URL and Create Service button</name>
  <files>core/urls.py, core/templates/core/services/list.html, core/views/services.py</files>
  <action>
Add a global service creation wizard URL that doesn't require project_name:

1. In core/urls.py services_patterns, add:
   path('create/', ServiceCreateWizard.as_view(), name='create'),
   This maps /services/create/ to the wizard without a project context.

2. In ServiceCreateWizard.dispatch(), the project is already set to None when no project_name in kwargs.
   The form already handles this - project field is not disabled when no project is passed.
   No changes needed to the view.

3. In core/templates/core/services/list.html, add a "Create Service" button in the header:
   In the header div (after the description), add:
   ```html
   <a href="{% url 'services:create' %}"
      class="px-4 py-2 bg-dark-accent hover:bg-dark-accent/80 text-white rounded-lg transition-colors inline-flex items-center gap-2">
       <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
       </svg>
       Create Service
   </a>
   ```

4. Also update empty state to link directly to wizard instead of projects list.
  </action>
  <verify>
1. Navigate to /services/
2. Click "Create Service" button
3. Wizard opens at /services/create/
4. Project dropdown is enabled and shows all active projects
5. Complete wizard - service created successfully
  </verify>
  <done>Users can create services from Services list page with one click</done>
</task>

<task type="auto">
  <name>Task 3: Fix blueprint visibility in wizard</name>
  <files>core/forms/services.py</files>
  <action>
The issue is that BlueprintStepForm filters blueprints by sync_status='synced'.
If a blueprint was recently added but sync hasn't completed, it won't show.

However, if sync completed successfully and blueprint still doesn't show, check:
1. is_available_for_project() returns False when no project context
2. _filter_blueprints_for_project() is called even when project is None

Fix in core/forms/services.py BlueprintStepForm.__init__():

Currently the code does:
```python
if project:
    self._filter_blueprints_for_project(project)
```

When project is None (global wizard), the queryset is ALL synced blueprints.
But _filter_blueprints_for_project checks is_available_for_project(project).

The real issue is likely that when opening from global context:
- No filtering happens (good)
- But if user later selects a project, we should ideally re-filter

For now, when project is None, show ALL synced blueprints (which is current behavior).
The form already does this correctly.

The actual fix needed: Check if is_available_globally() should be used instead of
is_available_for_project() when there's no project context.

In _filter_blueprints_for_project, only filter if project is provided.
When project is None in global wizard, show all blueprints that pass is_available_globally().

Update BlueprintStepForm.__init__():
```python
if project:
    self._filter_blueprints_for_project(project)
else:
    # Global wizard - show blueprints available with any active connection
    available_blueprints = []
    for blueprint in Blueprint.objects.filter(sync_status='synced'):
        if blueprint.is_available_globally():
            available_blueprints.append(blueprint.pk)
    self.fields['blueprint'].queryset = Blueprint.objects.filter(pk__in=available_blueprints)
```

This ensures only blueprints that CAN be used (have matching deploy connections) are shown.
  </action>
  <verify>
1. Register a blueprint and wait for sync to complete
2. Open wizard from /services/create/
3. Blueprint appears in dropdown
4. Select project - blueprint list should update (HTMX enhancement - future)
  </verify>
  <done>All synced and available blueprints appear in the wizard selector</done>
</task>

<task type="auto">
  <name>Task 4: Fix wizard padding</name>
  <files>core/templates/core/services/wizard/base.html</files>
  <action>
The wizard base.html extends base.html but doesn't account for sidebar offset.
The base.html has ml-64 on main content wrapper, but wizard content starts too close to edge.

Looking at wizard/base.html:
- Uses {% block content %} which goes into base.html's main area
- Has "max-w-3xl mx-auto" but no left padding for sidebar

The issue is that wizard base.html's content block doesn't have proper padding.

Fix: Add p-8 padding wrapper to match other pages like services/list.html.

In core/templates/core/services/wizard/base.html, wrap the content in proper padding:

Change:
```html
{% block content %}
<div class="max-w-3xl mx-auto">
```

To:
```html
{% block content %}
<div class="p-8">
<div class="max-w-3xl mx-auto">
```

And add closing </div> at the end before {% endblock %}.

Actually, looking at the template, the content is already in a div.
The issue might be missing the outer padding div.

Current structure:
```html
{% block content %}
<div class="max-w-3xl mx-auto">
    ...
</div>
...
{% endblock %}
```

Change to:
```html
{% block content %}
<div class="p-8">
    <div class="max-w-3xl mx-auto">
        ...
    </div>
</div>
...
{% endblock %}
```
  </action>
  <verify>
1. Open wizard at /services/create/
2. Wizard content should have proper padding from sidebar
3. Text should not start right where sidebar ends
4. Compare with other pages like /services/ for consistent padding
  </verify>
  <done>Wizard has proper padding matching other pages</done>
</task>

</tasks>

<verification>
1. Start worker: `make run` (or `python manage.py db_worker --queue-name "*"`)
2. Navigate to /connections/ - health checks should be enqueued
3. Navigate to /services/ - "Create Service" button visible
4. Click button - wizard opens with project dropdown
5. Select project and blueprint - all synced blueprints visible
6. Wizard content properly padded from sidebar
</verification>

<success_criteria>
- [ ] Health checks enqueued automatically when viewing connections
- [ ] /services/ page has "Create Service" button
- [ ] /services/create/ URL works without project context
- [ ] All synced blueprints with available connections shown in wizard
- [ ] Wizard content has p-8 padding wrapper
</success_criteria>

<output>
After completion, create `.planning/quick/022-fix-healthchecks-wizard-improvements/022-SUMMARY.md`
</output>
