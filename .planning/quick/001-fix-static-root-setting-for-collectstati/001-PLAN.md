---
phase: quick-001
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [devssp/settings.py]
autonomous: true

must_haves:
  truths:
    - "collectstatic command runs without ImproperlyConfigured error"
    - "Static files are collected to staticfiles/ directory"
  artifacts:
    - path: "devssp/settings.py"
      provides: "STATIC_ROOT configuration"
      contains: "STATIC_ROOT"
  key_links:
    - from: "devssp/settings.py"
      to: "staticfiles/"
      via: "STATIC_ROOT = BASE_DIR / 'staticfiles'"
---

<objective>
Fix the STATIC_ROOT Django setting to enable collectstatic command.

Purpose: The `collectstatic` command fails with `ImproperlyConfigured` error because STATIC_ROOT is not set. This is required for production deployments.
Output: Working collectstatic command that collects static files to staticfiles/ directory.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@devssp/settings.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add STATIC_ROOT setting</name>
  <files>devssp/settings.py</files>
  <action>
    Add STATIC_ROOT setting to devssp/settings.py after the existing STATIC_URL line (line 132).

    Add:
    ```python
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    ```

    This follows Django convention: STATIC_URL is the URL prefix, STATIC_ROOT is the filesystem path where collectstatic gathers files.

    Also add 'staticfiles/' to .gitignore if not already present (collected static files should not be committed).
  </action>
  <verify>
    Run: `source venv/bin/activate && python manage.py collectstatic --dry-run --noinput`
    Should complete without ImproperlyConfigured error.
  </verify>
  <done>
    - STATIC_ROOT = BASE_DIR / 'staticfiles' is set in settings.py
    - collectstatic --dry-run completes successfully
    - staticfiles/ is in .gitignore
  </done>
</task>

</tasks>

<verification>
```bash
source venv/bin/activate && python manage.py collectstatic --dry-run --noinput
```
Should output list of files that would be collected, no errors.
</verification>

<success_criteria>
- collectstatic command runs without ImproperlyConfigured error
- STATIC_ROOT points to BASE_DIR / 'staticfiles'
- staticfiles/ directory is gitignored
</success_criteria>

<output>
After completion, create `.planning/quick/001-fix-static-root-setting-for-collectstati/001-SUMMARY.md`
</output>
