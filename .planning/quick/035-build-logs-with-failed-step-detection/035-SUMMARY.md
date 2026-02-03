# Quick Task 035: Build Logs with Failed Step Detection

## Summary

Added server-side cached build log fetching with automatic failed step detection for the Builds UI.

## Changes

### 1. GitHubPlugin Methods (`plugins/github/plugin.py`)

- `get_workflow_run_jobs(config, repo_name, run_id)` - Fetches jobs with steps array, each step has `conclusion` field for failure detection
- `get_job_logs(config, repo_name, job_id)` - Fetches raw text logs for a specific job via GitHub API

### 2. Build Model Fields (`core/models.py`)

- Added `failed_job_name` CharField - stores the name of the failed job
- Added `failed_step_name` CharField - stores the name of the failed step
- Migration: `0019_add_build_failed_step_fields`

### 3. Django File-Based Cache (`pathfinder/settings.py`)

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": DATA_DIR / "cache",  # data/cache/
        "TIMEOUT": 3600,  # 60 minutes
    }
}
```

### 4. BuildLogsView (`core/views/services.py`)

- URL: `/projects/<project>/services/<service>/builds/<build_uuid>/logs/`
- Checks cache first (60 min TTL)
- Fetches jobs from GitHub to detect failed job/step
- Updates Build model with `failed_job_name` and `failed_step_name` if not set
- Fetches and caches logs for the failed job (or first job)
- Returns `_build_logs_partial.html` template

### 5. Templates

**`_build_row_expanded.html`**
- Added lazy-loading logs section with `hx-get` and `hx-trigger="intersect once"`
- Shows loading spinner while fetching

**`_build_logs_partial.html`** (new)
- Displays "Failed at: {job} → {step}" for failed builds
- Shows logs in scrollable pre block with monospace font
- Handles errors and "logs unavailable" state

## Technical Notes

- Cache key format: `build_logs_{build_uuid}`
- Logs fetched via raw HTTP request (PyGithub doesn't expose logs endpoint directly)
- Cache can be migrated to ValKey later by changing `BACKEND` setting
- CSP-compliant: all JS via HTMX attributes, no inline scripts

## Commits

- `b4dfba1` - feat(quick-035): add GitHubPlugin methods for workflow jobs and logs
- `a665132` - feat(quick-035): add Build model fields and file-based cache config
- `23c5ec4` - feat(quick-035): add BuildLogsView and lazy-load logs in expanded rows
- `d85d6e6` - feat(quick-035): update cache location to data/cache with 60min TTL
