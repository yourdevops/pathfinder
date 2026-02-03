---
phase: quick
plan: 033
type: execute
wave: 1
depends_on: []
files_modified:
  - plugins/github/plugin.py
  - core/views/services.py
  - core/templates/core/services/_builds_tab.html
  - core/urls.py
autonomous: true

must_haves:
  truths:
    - "User can manually trigger fetching workflow runs from GitHub"
    - "Builds tab shows sync button when webhook is not registered"
    - "Polling fetches recent workflow runs and creates/updates Build records"
  artifacts:
    - path: "plugins/github/plugin.py"
      provides: "list_workflow_runs method"
      contains: "def list_workflow_runs"
    - path: "core/views/services.py"
      provides: "ServiceSyncBuildsView endpoint"
      contains: "class ServiceSyncBuildsView"
    - path: "core/templates/core/services/_builds_tab.html"
      provides: "Sync Builds button"
      contains: "Sync Builds"
  key_links:
    - from: "ServiceSyncBuildsView"
      to: "poll_build_details task"
      via: "enqueue for each workflow run"
      pattern: "poll_build_details\\.enqueue"
---

<objective>
Add manual polling for build jobs when webhooks are unavailable.

Purpose: Local development and non-public Pathfinder installations cannot receive webhooks from GitHub. Users need a way to manually fetch workflow run statuses.

Output: "Sync Builds" button in builds tab that fetches recent workflow runs from GitHub API and updates Build records.
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@core/views/services.py
@core/tasks.py
@core/templates/core/services/_builds_tab.html
@plugins/github/plugin.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add list_workflow_runs method to GitHub plugin</name>
  <files>plugins/github/plugin.py</files>
  <action>
Add a new method `list_workflow_runs` to GitHubPlugin class (after `get_workflow_run`):

```python
def list_workflow_runs(
    self, config: dict[str, Any], repo_name: str, per_page: int = 10
) -> list[dict[str, Any]]:
    """
    List recent workflow runs for a repository.

    Used for manual polling when webhooks are unavailable.

    Args:
        config: The decrypted configuration dictionary.
        repo_name: Full repository name (owner/repo).
        per_page: Number of runs to fetch (default 10).

    Returns:
        List of workflow run dictionaries.
    """
    g = self._get_github_client(config)
    repo = g.get_repo(repo_name)
    runs = repo.get_workflow_runs()[:per_page]

    result = []
    for run in runs:
        result.append({
            "id": run.id,
            "run_number": run.run_number,
            "head_sha": run.head_sha,
            "head_branch": run.head_branch,
            "status": run.status,
            "conclusion": run.conclusion,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "html_url": run.html_url,
            "name": run.name,
            "event": run.event,
            "actor": {
                "login": run.actor.login if run.actor else None,
                "avatar_url": run.actor.avatar_url if run.actor else None,
            },
        })
    return result
```
  </action>
  <verify>Python syntax check: `python -c "import plugins.github.plugin"`</verify>
  <done>GitHubPlugin has list_workflow_runs method that returns recent runs</done>
</task>

<task type="auto">
  <name>Task 2: Add ServiceSyncBuildsView and URL</name>
  <files>core/views/services.py, core/urls.py</files>
  <action>
1. In `core/views/services.py`, add a new view class (after ServiceRegisterWebhookView):

```python
class ServiceSyncBuildsView(LoginRequiredMixin, View):
    """Manually poll GitHub for recent workflow runs."""

    def post(self, request, project_name, service_name):
        from core.git_utils import parse_git_url
        from core.models import ProjectConnection
        from core.tasks import poll_build_details

        project = get_object_or_404(Project, name=project_name, status="active")
        service = get_object_or_404(Service, project=project, name=service_name)

        # Check permissions (viewer can trigger sync)
        role = get_user_project_role(request.user, project)
        if not role:
            messages.error(request, "You don't have permission to access this service.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        # Guard: service must have a repo_url
        if not service.repo_url:
            messages.error(request, "Service has no repository URL.")
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

        try:
            # Fetch recent workflow runs
            runs = plugin.list_workflow_runs(config, repo_name, per_page=10)

            # Filter to runs matching our CI workflow naming convention
            workflow_name_prefix = f"CI - {service.ci_workflow.name}" if service.ci_workflow else None

            queued = 0
            for run_data in runs:
                # Skip if workflow name doesn't match (when CI workflow is assigned)
                if workflow_name_prefix and not run_data["name"].startswith("CI - "):
                    continue

                # Enqueue polling task for each run
                poll_build_details.enqueue(
                    run_id=run_data["id"],
                    repo_name=repo_name,
                    connection_id=connection.id,
                    service_id=service.id,
                    artifact_ref="",  # Will be fetched by the task
                )
                queued += 1

            if queued > 0:
                messages.success(request, f"Syncing {queued} workflow run(s) from GitHub...")
            else:
                messages.info(request, "No matching workflow runs found.")

        except Exception as e:
            messages.error(request, f"Failed to fetch workflow runs: {e}")

        return redirect(f"/projects/{project_name}/services/{service_name}/?tab=builds")
```

2. In `core/urls.py`, add URL pattern for the new view. Find the services URL section (near service_detail) and add:

```python
path(
    "projects/<dns:project_name>/services/<dns:service_name>/sync-builds/",
    services.ServiceSyncBuildsView.as_view(),
    name="service_sync_builds",
),
```

Import ServiceSyncBuildsView in the services import if needed.
  </action>
  <verify>
- Check URL resolution: `uv run python -c "from django.urls import reverse; print(reverse('projects:service_sync_builds', kwargs={'project_name': 'test', 'service_name': 'svc'}))"`
- Verify view loads: `uv run python -c "from core.views.services import ServiceSyncBuildsView"`
  </verify>
  <done>POST to /projects/{project}/services/{service}/sync-builds/ enqueues polling tasks</done>
</task>

<task type="auto">
  <name>Task 3: Add Sync Builds button to builds tab UI</name>
  <files>core/templates/core/services/_builds_tab.html</files>
  <action>
Update the builds tab header section to include a "Sync Builds" button. Replace the header div (lines 2-22) to add the sync button next to the status filter:

In the `<div class="flex items-center justify-between">` section:
1. Keep the h1 title on the left
2. Add a flex container on the right with:
   - The existing status filter dropdown (when builds exist)
   - A new "Sync Builds" button that POSTs to the sync endpoint

The button should:
- Use HTMX to POST to {% url 'projects:service_sync_builds' project.name service.name %}
- Show a refresh/sync icon (SVG)
- Have hover state and appropriate styling
- Work regardless of whether builds exist (user may want to sync when empty)

Updated header structure:
```html
<div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold text-dark-text">Builds</h1>

    <div class="flex items-center gap-4">
        <!-- Sync button - always visible -->
        <form method="post" action="{% url 'projects:service_sync_builds' project.name service.name %}">
            {% csrf_token %}
            <button type="submit"
                    class="flex items-center gap-2 px-3 py-1.5 bg-dark-surface border border-dark-border rounded text-sm text-dark-text hover:bg-gray-800 transition-colors"
                    title="Fetch recent builds from GitHub">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync Builds
            </button>
        </form>

        {% if has_any_builds %}
        <div class="flex items-center gap-2">
            <label for="status-filter" class="text-sm text-dark-muted">Status:</label>
            <select id="status-filter" ...>
                ...
            </select>
        </div>
        {% endif %}
    </div>
</div>
```
  </action>
  <verify>Visual check: Navigate to a service's builds tab and verify the "Sync Builds" button appears</verify>
  <done>Builds tab shows "Sync Builds" button that triggers manual polling</done>
</task>

</tasks>

<verification>
1. Navigate to a service's builds tab
2. Click "Sync Builds" button
3. Verify success message appears
4. Verify builds appear in the table (after background task processes)
5. Verify button works even when no builds exist (empty state)
</verification>

<success_criteria>
- Sync Builds button visible in builds tab header
- Clicking button fetches recent workflow runs from GitHub
- Build records created/updated for each workflow run
- Works for local development without webhooks
</success_criteria>

<output>
After completion, create `.planning/quick/033-add-manual-poll-for-build-jobs-when-webh/033-SUMMARY.md`
</output>
