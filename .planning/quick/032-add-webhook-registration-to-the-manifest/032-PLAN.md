---
phase: quick
plan: 032
type: execute
wave: 1
depends_on: []
files_modified:
  - core/models.py
  - core/tasks.py
  - core/views/services.py
  - core/urls.py
  - core/templates/core/services/_settings_tab.html
autonomous: true

must_haves:
  truths:
    - "Webhook is registered when pushing CI manifest to repository"
    - "Service settings show webhook configuration status"
    - "Users can manually trigger webhook registration for existing services"
  artifacts:
    - path: "core/models.py"
      provides: "webhook_registered field on Service model"
    - path: "core/tasks.py"
      provides: "Webhook registration in push_ci_manifest task"
    - path: "core/views/services.py"
      provides: "ServiceRegisterWebhookView for manual registration"
    - path: "core/templates/core/services/_settings_tab.html"
      provides: "Webhook status display and configure button"
  key_links:
    - from: "core/tasks.py"
      to: "plugins/github/plugin.py"
      via: "plugin.configure_webhook call"
      pattern: "configure_webhook"
    - from: "_settings_tab.html"
      to: "ServiceRegisterWebhookView"
      via: "form POST to register webhook"
---

<objective>
Add webhook registration to the CI manifest push flow. Show webhook status in Service Settings. Allow manual webhook registration for services without a configured webhook.

Purpose: Build status updates rely on webhooks. Currently webhooks must be configured manually. Integrating webhook registration into the manifest push flow (and providing a manual trigger) improves the developer experience.

Output: Service model tracks webhook_registered status; push_ci_manifest registers webhook; Settings tab shows status with manual configure button.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@core/models.py (Service model, lines 376-493)
@core/tasks.py (push_ci_manifest task)
@plugins/github/plugin.py (configure_webhook method)
@core/templates/core/services/_settings_tab.html
@core/views/services.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add webhook_registered field and update push_ci_manifest task</name>
  <files>core/models.py, core/tasks.py</files>
  <action>
1. In core/models.py, add to Service model (after ci_manifest_pr_url field, around line 436):
   ```python
   webhook_registered = models.BooleanField(default=False)
   ```

2. Create and run migration:
   ```bash
   uv run python manage.py makemigrations core --name add_service_webhook_registered
   uv run python manage.py migrate
   ```

3. In core/tasks.py push_ci_manifest function, after successfully pushing the manifest and creating PR (around line 579), add webhook registration:
   ```python
   # Register webhook for build notifications
   from core.models import SiteConfiguration

   site_config = SiteConfiguration.get_instance()
   if site_config and site_config.external_url:
       webhook_url = f"{site_config.external_url.rstrip('/')}/webhooks/build/"
       try:
           plugin.configure_webhook(
               config,
               repo_name,
               webhook_url,
               events=["workflow_run"],
           )
           service.webhook_registered = True
           logger.info(f"Registered webhook for service {service.name}")
       except Exception as e:
           # Log but don't fail the manifest push
           logger.warning(f"Failed to register webhook for service {service.name}: {e}")
   else:
       logger.warning(f"External URL not configured, skipping webhook registration for {service.name}")
   ```

4. Update the service.save() call to include webhook_registered in update_fields.
  </action>
  <verify>
- Migration created and applied: `uv run python manage.py showmigrations core | grep webhook`
- Field exists: `uv run python manage.py shell -c "from core.models import Service; print([f.name for f in Service._meta.fields if 'webhook' in f.name])"`
  </verify>
  <done>Service model has webhook_registered field; push_ci_manifest registers webhook after manifest push</done>
</task>

<task type="auto">
  <name>Task 2: Add manual webhook registration view and update Settings tab</name>
  <files>core/views/services.py, core/urls.py, core/templates/core/services/_settings_tab.html</files>
  <action>
1. In core/views/services.py, add ServiceRegisterWebhookView class (after ServicePushManifestView):
   ```python
   class ServiceRegisterWebhookView(LoginRequiredMixin, View):
       """Manually register webhook for a service."""

       def post(self, request, project_name, service_name):
           from core.models import ProjectConnection, SiteConfiguration
           from core.git_utils import parse_git_url

           project = get_object_or_404(Project, name=project_name, status="active")
           service = get_object_or_404(Service, project=project, name=service_name)

           # Check permissions
           role = get_user_project_role(request.user, project)
           if role not in ["owner", "contributor"]:
               messages.error(request, "You don't have permission to configure webhooks.")
               return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

           # Get site config for webhook URL
           site_config = SiteConfiguration.get_instance()
           if not site_config or not site_config.external_url:
               messages.error(request, "External URL not configured. Go to Settings > General to configure it.")
               return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

           # Get SCM connection
           project_connection = (
               ProjectConnection.objects.filter(project=project, is_default=True)
               .select_related("connection")
               .first()
           )
           if not project_connection:
               messages.error(request, "No SCM connection configured for this project.")
               return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

           connection = project_connection.connection
           plugin = connection.get_plugin()
           config = connection.get_config()

           if not plugin:
               messages.error(request, "SCM plugin not available.")
               return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

           # Parse repo URL
           parsed = parse_git_url(service.repo_url)
           if not parsed:
               messages.error(request, "Invalid repository URL.")
               return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

           repo_name = f"{parsed['owner']}/{parsed['repo']}"
           webhook_url = f"{site_config.external_url.rstrip('/')}/webhooks/build/"

           try:
               plugin.configure_webhook(
                   config,
                   repo_name,
                   webhook_url,
                   events=["workflow_run"],
               )
               service.webhook_registered = True
               service.save(update_fields=["webhook_registered", "updated_at"])
               messages.success(request, "Webhook registered successfully.")
           except Exception as e:
               messages.error(request, f"Failed to register webhook: {e}")

           return redirect("projects:service_detail", project_name=project_name, service_name=service_name)
   ```

2. In core/urls.py, import the new view and add URL pattern (around line 87, add to imports):
   ```python
   from .views.services import (
       ServiceAssignWorkflowView,
       ServiceCreateWizard,
       ServiceDeleteView,
       ServiceDetailView,
       ServiceListView,
       ServicePushManifestView,
       ServiceRegisterWebhookView,  # Add this
       ServiceScaffoldStatusView,
   )
   ```

   Add URL pattern in projects_patterns (after service_push_manifest, around line 342):
   ```python
   path(
       "<dns:project_name>/services/<dns:service_name>/register-webhook/",
       ServiceRegisterWebhookView.as_view(),
       name="service_register_webhook",
   ),
   ```

3. In core/templates/core/services/_settings_tab.html, add Webhook Configuration section after Environment Variables section (before Danger Zone):
   ```html
   <!-- Webhook Configuration -->
   <div class="bg-dark-surface border border-dark-border rounded-lg">
       <div class="p-4 border-b border-dark-border flex items-center justify-between">
           <h2 class="text-lg font-semibold text-dark-text">Webhook Configuration</h2>
           {% if service.webhook_registered %}
           <span class="px-2 py-1 text-xs rounded bg-green-500/20 text-green-300">Configured</span>
           {% else %}
           <span class="px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-300">Not Configured</span>
           {% endif %}
       </div>
       <div class="p-4">
           {% if service.webhook_registered %}
           <p class="text-dark-muted">Webhook is configured. Build status updates will be received automatically.</p>
           {% else %}
           <p class="text-dark-muted mb-4">Webhook is not configured. Build status updates will not be received until the webhook is registered.</p>
           {% if can_edit %}
           <form method="post" action="{% url 'projects:service_register_webhook' project_name=project.name service_name=service.name %}">
               {% csrf_token %}
               <button type="submit"
                       {% if not service.repo_url %}disabled{% endif %}
                       class="px-4 py-2 rounded-lg transition-colors
                           {% if service.repo_url %}bg-dark-accent hover:bg-dark-accent/80 text-white{% else %}bg-gray-600 text-gray-400 cursor-not-allowed{% endif %}">
                   Register Webhook
               </button>
               {% if not service.repo_url %}
               <span class="text-sm text-dark-muted ml-3">Repository URL required.</span>
               {% endif %}
           </form>
           {% endif %}
           {% endif %}
       </div>
   </div>
   ```
  </action>
  <verify>
- Server starts: `uv run python manage.py check`
- URL resolves: `uv run python manage.py shell -c "from django.urls import reverse; print(reverse('projects:service_register_webhook', kwargs={'project_name': 'test', 'service_name': 'svc'}))"`
  </verify>
  <done>Settings tab shows webhook status (Configured/Not Configured); users can manually register webhook via button</done>
</task>

</tasks>

<verification>
1. Run Django checks: `uv run python manage.py check`
2. Verify migration applied: `uv run python manage.py showmigrations core`
3. Start server and navigate to a service's Settings tab to verify webhook status appears
</verification>

<success_criteria>
- Service model has webhook_registered BooleanField
- push_ci_manifest task registers webhook after pushing manifest (when external_url configured)
- Service Settings tab shows webhook status badge
- "Register Webhook" button appears for services without configured webhook
- Manual webhook registration works via the button
</success_criteria>

<output>
After completion, create `.planning/quick/032-add-webhook-registration-to-the-manifest/032-SUMMARY.md`
</output>
