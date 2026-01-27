---
quick: 021
type: execute
autonomous: true
files_modified:
  - core/templates/core/connections/detail.html
  - docker-compose.yml
---

<objective>
Fix connection detail page URL errors and worker task execution issue.

Purpose: The connection detail page crashes due to Phase 4.1 slug URL migration leaving stale `project_uuid` references. Additionally, the worker container only listens to `default` queue but tasks use named queues (`health_checks`, `blueprint_sync`, `repository_scaffolding`).

Output: Working connection detail page with correct project/environment URLs and worker processing all task queues.
</objective>

<context>
@.planning/STATE.md - Phase 4.1 replaced UUID URLs with slug-based URLs
@core/urls.py - Current URL patterns use `project_name` and `env_name` not UUIDs
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix connection detail template URL references</name>
  <files>core/templates/core/connections/detail.html</files>
  <action>
    Update the Usage section links to use slug-based URL parameters instead of UUIDs:

    Line 257: Change `projects:detail` from `project_uuid=attachment.project.uuid` to `project_name=attachment.project.name`

    Line 276: Change `projects:environment_detail` from `project_uuid=attachment.environment.project.uuid env_uuid=attachment.environment.uuid` to `project_name=attachment.environment.project.name env_name=attachment.environment.name`

    The URL patterns in core/urls.py now expect:
    - projects:detail -> `<dns:project_name>/`
    - projects:environment_detail -> `<dns:project_name>/environments/<dns:env_name>/`
  </action>
  <verify>
    Navigate to `/connections/github-yourdevops/` - page should render without NoReverseMatch error.
    Project and environment links in Usage section should be clickable and navigate correctly.
  </verify>
  <done>Connection detail page renders successfully, project/environment links resolve to correct slug-based URLs</done>
</task>

<task type="auto">
  <name>Task 2: Fix worker to process all task queues</name>
  <files>docker-compose.yml</files>
  <action>
    Update the worker service command to listen on all queues instead of just `default`:

    Change:
    ```yaml
    command: python manage.py db_worker
    ```

    To:
    ```yaml
    command: python manage.py db_worker --queue-name "*"
    ```

    The `--queue-name "*"` flag tells the worker to process tasks from all configured queues (`default`, `health_checks`, `blueprint_sync`, `repository_scaffolding`).

    Alternative explicit approach (not recommended as it requires maintenance):
    ```yaml
    command: python manage.py db_worker --queue-name "default,health_checks,blueprint_sync,repository_scaffolding"
    ```
  </action>
  <verify>
    1. Restart containers: `docker compose down && docker compose up -d`
    2. Check worker logs: `docker logs ssp-worker --tail 20`
    3. Confirm log shows `queues=*` instead of `queues=default`
    4. Trigger a blueprint sync or connection health check
    5. Verify task executes (check logs for task processing messages)
  </verify>
  <done>Worker starts with `queues=*` and processes tasks from all queue types</done>
</task>

</tasks>

<verification>
1. Visit `/connections/github-yourdevops/` - no errors, page renders
2. Click project links in Usage section - navigate to correct project pages
3. Worker logs show `queues=*` on startup
4. Background tasks (health checks, blueprint sync) execute successfully
</verification>

<success_criteria>
- NoReverseMatch error on connection detail page is resolved
- Worker processes tasks from all queues
- No regressions to other connection or project pages
</success_criteria>

<output>
After completion, update `.planning/STATE.md` to add quick-021 to completed tasks table.
</output>
