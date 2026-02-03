---
phase: quick-035
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/models.py
  - plugins/github/plugin.py
  - pathfinder/settings.py
  - .gitignore
  - core/views/services.py
  - core/urls.py
  - core/templates/core/services/_build_row_expanded.html
  - core/templates/core/services/_build_logs_partial.html
autonomous: true

must_haves:
  truths:
    - "Failed builds display the failed job and step names"
    - "Build logs are fetched from GitHub API on-demand"
    - "Build logs are cached for 60 minutes to avoid repeated API calls"
    - "Expanded build rows show logs in a scrollable container"
    - "Logs highlight error lines for failed builds"
  artifacts:
    - path: "core/models.py"
      provides: "Build model with failed_job_name and failed_step_name fields"
      contains: "failed_job_name"
    - path: "plugins/github/plugin.py"
      provides: "get_workflow_run_jobs and get_job_logs methods"
      exports: ["get_workflow_run_jobs", "get_job_logs"]
    - path: "pathfinder/settings.py"
      provides: "File-based cache configuration"
      contains: "FileBasedCache"
    - path: "core/views/services.py"
      provides: "BuildLogsView for fetching and caching logs"
      contains: "BuildLogsView"
    - path: "core/templates/core/services/_build_logs_partial.html"
      provides: "HTML partial for rendering logs"
  key_links:
    - from: "core/views/services.py"
      to: "plugins/github/plugin.py"
      via: "get_job_logs API call"
      pattern: "plugin\\.get_job_logs"
    - from: "core/templates/core/services/_build_row_expanded.html"
      to: "core/views/services.py"
      via: "HTMX hx-get for lazy loading"
      pattern: "hx-get.*logs"
---

<objective>
Add build logs with failed step detection to the builds tab.

Purpose: When builds fail, developers need to quickly identify which job and step failed, and view the logs without leaving Pathfinder. This improves debugging workflow.

Output:
- Build model extended with failed_job_name and failed_step_name fields
- GitHubPlugin methods to fetch jobs and logs
- File-based cache for logs (5 min TTL)
- HTMX endpoint to lazy-load logs in expanded build rows
- Visual highlighting of failed step info and error lines
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/models.py (Build model at line 739+)
@plugins/github/plugin.py (existing GitHub methods)
@core/views/services.py (ServiceDetailView for builds tab)
@core/urls.py (URL patterns for services)
@core/templates/core/services/_build_row_expanded.html (expanded row template)
@pathfinder/settings.py (Django settings)
@.gitignore (for adding .cache/)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add GitHubPlugin methods for jobs and logs</name>
  <files>plugins/github/plugin.py</files>
  <action>
Add two new methods to GitHubPlugin:

1. `get_workflow_run_jobs(config, repo_name, run_id)`:
   - Use `repo.get_workflow_run(run_id).jobs()` to get jobs
   - Return list of dicts with: id, name, status, conclusion, started_at, completed_at, steps
   - Each step has: name, status, conclusion, number
   - This allows detecting which job/step failed

2. `get_job_logs(config, repo_name, job_id)`:
   - Use GitHub API directly (PyGithub doesn't have logs endpoint)
   - Make authenticated request to `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs`
   - Returns plain text log content
   - Handle 410 Gone (logs expired) gracefully by returning None
   - Note: GitHub returns redirect to Azure blob, follow it

Implementation pattern (for get_job_logs):
```python
def get_job_logs(self, config: dict[str, Any], repo_name: str, job_id: int) -> str | None:
    """Fetch job logs from GitHub Actions."""
    import requests
    g = self._get_github_client(config)
    # Get token from client
    token = g._Github__requester._Requester__auth.token
    base_url = config.get("base_url", "https://api.github.com")
    url = f"{base_url}/repos/{repo_name}/actions/jobs/{job_id}/logs"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        resp = requests.get(url, headers=headers, allow_redirects=True, timeout=30)
        if resp.status_code == 200:
            return resp.text
        return None
    except Exception:
        return None
```
  </action>
  <verify>
Run Python to verify methods exist and are callable:
```bash
uv run python -c "from plugins.github.plugin import GitHubPlugin; p = GitHubPlugin(); print('get_workflow_run_jobs' in dir(p), 'get_job_logs' in dir(p))"
```
Should print: True True
  </verify>
  <done>GitHubPlugin has get_workflow_run_jobs and get_job_logs methods</done>
</task>

<task type="auto">
  <name>Task 2: Add Build model fields and cache configuration</name>
  <files>core/models.py, pathfinder/settings.py, .gitignore</files>
  <action>
1. In `core/models.py`, add two fields to the Build model (after line 776 ci_job_url):
```python
# Failed step information (populated when build fails)
failed_job_name = models.CharField(max_length=255, blank=True)
failed_step_name = models.CharField(max_length=255, blank=True)
```

2. In `pathfinder/settings.py`, add file-based cache configuration after the TEMPLATES section:
```python
# Cache configuration (for build logs)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / '.cache',
        'TIMEOUT': 300,  # 5 minutes
    }
}
```

3. In `.gitignore`, add `.cache/` directory:
```
# Django file cache
.cache/
```

4. Create and run migration:
```bash
uv run python manage.py makemigrations core --name add_build_failed_step_fields
uv run python manage.py migrate
```
  </action>
  <verify>
```bash
uv run python manage.py shell -c "from core.models import Build; b = Build(); print(hasattr(b, 'failed_job_name'), hasattr(b, 'failed_step_name'))"
```
Should print: True True

Check cache config:
```bash
uv run python manage.py shell -c "from django.conf import settings; print(settings.CACHES['default']['BACKEND'])"
```
Should print: django.core.cache.backends.filebased.FileBasedCache
  </verify>
  <done>Build model has failed_job_name and failed_step_name fields, cache configured</done>
</task>

<task type="auto">
  <name>Task 3: Add BuildLogsView and update expanded row template</name>
  <files>core/views/services.py, core/urls.py, core/templates/core/services/_build_logs_partial.html, core/templates/core/services/_build_row_expanded.html</files>
  <action>
1. Create `BuildLogsView` in `core/views/services.py`:
```python
class BuildLogsView(LoginRequiredMixin, View):
    """HTMX endpoint to fetch and cache build logs."""

    def get(self, request, project_name, service_name, build_uuid):
        from django.core.cache import cache
        from core.git_utils import parse_git_url
        from core.models import ProjectConnection

        project = get_object_or_404(Project, name=project_name, status="active")
        service = get_object_or_404(Service, project=project, name=service_name)
        build = get_object_or_404(Build, uuid=build_uuid, service=service)

        # Check permissions
        role = get_user_project_role(request.user, project)
        if not role:
            return HttpResponse("Access denied", status=403)

        # Check cache first
        cache_key = f"build_logs_{build_uuid}"
        cached = cache.get(cache_key)
        if cached:
            return render(request, "core/services/_build_logs_partial.html", {
                "logs": cached["logs"],
                "failed_job_name": build.failed_job_name,
                "failed_step_name": build.failed_step_name,
                "build": build,
            })

        # Need to fetch from GitHub
        if not service.repo_url:
            return render(request, "core/services/_build_logs_partial.html", {
                "error": "No repository configured"
            })

        project_connection = (
            ProjectConnection.objects.filter(project=project, is_default=True)
            .select_related("connection")
            .first()
        )
        if not project_connection:
            return render(request, "core/services/_build_logs_partial.html", {
                "error": "No SCM connection configured"
            })

        connection = project_connection.connection
        plugin = connection.get_plugin()
        config = connection.get_config()

        parsed = parse_git_url(service.repo_url)
        if not parsed:
            return render(request, "core/services/_build_logs_partial.html", {
                "error": "Invalid repository URL"
            })

        repo_name = f"{parsed['owner']}/{parsed['repo']}"

        # Fetch jobs to find failed one and get job_id for logs
        try:
            jobs = plugin.get_workflow_run_jobs(config, repo_name, build.github_run_id)
        except Exception as e:
            return render(request, "core/services/_build_logs_partial.html", {
                "error": f"Failed to fetch jobs: {e}"
            })

        # Find failed job/step and update build if not already set
        failed_job = None
        failed_step = None
        job_id_for_logs = None

        for job in jobs:
            if job["conclusion"] == "failure":
                failed_job = job["name"]
                job_id_for_logs = job["id"]
                for step in job.get("steps", []):
                    if step["conclusion"] == "failure":
                        failed_step = step["name"]
                        break
                break
            # Also capture the first job for logs if no failure
            if job_id_for_logs is None:
                job_id_for_logs = job["id"]

        # Update build with failed info if not set
        if build.status == "failed" and not build.failed_job_name and failed_job:
            build.failed_job_name = failed_job
            build.failed_step_name = failed_step or ""
            build.save(update_fields=["failed_job_name", "failed_step_name", "updated_at"])

        # Fetch logs
        logs = None
        if job_id_for_logs:
            try:
                logs = plugin.get_job_logs(config, repo_name, job_id_for_logs)
            except Exception:
                pass

        # Cache result
        cache.set(cache_key, {"logs": logs}, 300)

        return render(request, "core/services/_build_logs_partial.html", {
            "logs": logs,
            "failed_job_name": build.failed_job_name,
            "failed_step_name": build.failed_step_name,
            "build": build,
        })
```

2. Add import for `render` at top of services.py and add to url imports.

3. Add URL pattern in `core/urls.py` (in projects_patterns, after service_sync_builds):
```python
path(
    "<dns:project_name>/services/<dns:service_name>/builds/<uuid:build_uuid>/logs/",
    BuildLogsView.as_view(),
    name="service_build_logs",
),
```

Add import: `from .views.services import BuildLogsView`

4. Create `core/templates/core/services/_build_logs_partial.html`:
```html
{% if error %}
<div class="p-4 text-dark-muted text-sm">
    {{ error }}
</div>
{% elif logs %}
<div class="space-y-2">
    {% if build.status == 'failed' and failed_job_name %}
    <div class="flex items-center gap-2 text-sm text-red-300 mb-2">
        <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <span>
            Failed at: <span class="font-medium">{{ failed_job_name }}</span>
            {% if failed_step_name %}
            <svg class="w-3 h-3 inline mx-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/></svg>
            <span class="font-medium">{{ failed_step_name }}</span>
            {% endif %}
        </span>
    </div>
    {% endif %}
    <div class="bg-gray-950 rounded-lg p-3 max-h-96 overflow-auto">
        <pre class="text-xs text-gray-300 whitespace-pre-wrap font-mono">{{ logs }}</pre>
    </div>
</div>
{% else %}
<div class="p-4 text-dark-muted text-sm">
    Logs unavailable or expired.
</div>
{% endif %}
```

5. Update `_build_row_expanded.html` to add HTMX lazy-load for logs.

After the "Status-specific content" section (after the final `{% endif %}` for status checks around line 93), add:
```html
<!-- Build logs section (lazy loaded) -->
<div class="mt-4 border-t border-dark-border pt-4">
    <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-dark-text">Build Logs</span>
    </div>
    <div id="logs-{{ build.uuid }}"
         hx-get="{% url 'projects:service_build_logs' project.name service.name build.uuid %}"
         hx-trigger="intersect once"
         hx-swap="innerHTML"
         class="min-h-[100px]">
        <div class="flex items-center justify-center py-8 text-dark-muted">
            <svg class="w-5 h-5 animate-spin mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Loading logs...
        </div>
    </div>
</div>
```

Note: The `hx-trigger="intersect once"` means logs load when the expanded row becomes visible, and only once.
  </action>
  <verify>
1. Check URL is registered:
```bash
uv run python manage.py shell -c "from django.urls import reverse; print(reverse('projects:service_build_logs', args=['test', 'test', '00000000-0000-0000-0000-000000000000']))"
```

2. Check template exists:
```bash
ls -la core/templates/core/services/_build_logs_partial.html
```

3. Visual check: Navigate to a service builds tab, expand a build row, verify logs section appears.
  </verify>
  <done>BuildLogsView endpoint works, expanded rows lazy-load logs via HTMX</done>
</task>

</tasks>

<verification>
1. GitHubPlugin methods exist:
   ```bash
   uv run python -c "from plugins.github.plugin import GitHubPlugin; p = GitHubPlugin(); print(hasattr(p, 'get_workflow_run_jobs'), hasattr(p, 'get_job_logs'))"
   ```

2. Build model has new fields:
   ```bash
   uv run python manage.py shell -c "from core.models import Build; print([f.name for f in Build._meta.fields if 'failed' in f.name])"
   ```

3. Cache is configured:
   ```bash
   uv run python manage.py shell -c "from django.conf import settings; print('FileBasedCache' in settings.CACHES['default']['BACKEND'])"
   ```

4. URL route exists:
   ```bash
   uv run python manage.py show_urls | grep build_logs
   ```

5. Run tests:
   ```bash
   uv run pytest core/tests/ -v -k "build" --tb=short
   ```
</verification>

<success_criteria>
- Build model has failed_job_name and failed_step_name fields
- GitHubPlugin can fetch workflow jobs and job logs
- File-based cache configured with 5 min TTL
- BuildLogsView fetches logs on-demand, caches them
- Expanded build rows lazy-load logs when visible
- Failed builds show "Failed at: job -> step" indicator
- Logs display in scrollable pre block
- All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/035-build-logs-with-failed-step-detection/035-SUMMARY.md`
</output>
