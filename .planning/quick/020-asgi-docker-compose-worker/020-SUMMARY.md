---
phase: quick
plan: 020
subsystem: deployment
tags: [asgi, uvicorn, docker-compose, worker]
dependency-graph:
  requires: []
  provides: [asgi-server, background-worker, docker-orchestration]
  affects: [deployment, container-builds]
tech-stack:
  added: [uvicorn[standard], gunicorn]
  patterns: [asgi, multi-container, background-tasks]
key-files:
  created: [.env.example]
  modified: [pathfinder/settings.py, requirements.txt, entrypoint.sh, docker-compose.yml, .gitignore]
decisions:
  - id: data-dir-location
    choice: "Database in data/db.sqlite3 subdirectory"
    reason: "Clean separation, easy volume mounting"
  - id: uvicorn-workers
    choice: "2 workers for uvicorn"
    reason: "Match previous gunicorn worker count"
  - id: bind-mount-volume
    choice: "Bind mount ./data instead of named volume"
    reason: "Easier local development and backup"
metrics:
  duration: 3 min
  completed: 2026-01-27
---

# Quick Task 020: ASGI Docker Compose Worker Summary

**One-liner:** Switched from Gunicorn WSGI to Uvicorn ASGI with multi-container docker-compose for web and background worker services.

## What Was Built

### 1. ASGI Server Configuration
- Updated `pathfinder/settings.py` to use `data/db.sqlite3` path with auto-directory creation
- Added `uvicorn[standard]` and `gunicorn` to requirements.txt
- Updated `entrypoint.sh` to run `uvicorn pathfinder.asgi:application` instead of gunicorn

### 2. Multi-Container Docker Compose
- Renamed `ssp` service to `web` for clarity
- Added `worker` service running `python manage.py db_worker` for background tasks
- Both services share `./data` volume for SQLite database consistency
- Added `PTF_ENCRYPTION_KEY` environment variable to both services

### 3. Environment Configuration
- Created `.env.example` with documentation for required environment variables
- Added `data/` to `.gitignore` to exclude database from version control

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database location | `data/db.sqlite3` | Clean separation, volume-mount friendly |
| Volume type | Bind mount (./data) | Easier for local dev and backups vs named volume |
| Worker command | `python manage.py db_worker` | Uses django-tasks database backend |
| Keep gunicorn | Yes | Flexibility for WSGI fallback if needed |

## Files Changed

| File | Change |
|------|--------|
| `pathfinder/settings.py` | DATA_DIR setup, database path to data/ |
| `requirements.txt` | Added uvicorn[standard], gunicorn |
| `entrypoint.sh` | Replaced gunicorn with uvicorn ASGI |
| `docker-compose.yml` | Added worker service, bind mount data/ |
| `.env.example` | New file with PTF_ENCRYPTION_KEY template |
| `.gitignore` | Added data/ directory |

## Commits

| Hash | Message |
|------|---------|
| 995454a | chore(quick-020): update settings and requirements for ASGI |
| 5134409 | chore(quick-020): update entrypoint for uvicorn ASGI server |
| 1552dd8 | chore(quick-020): add docker-compose with web and worker services |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated existing docker-compose.yml instead of creating new**
- **Found during:** Task 3
- **Issue:** docker-compose.yml already existed with different structure (ssp service, named volume)
- **Fix:** Updated existing file, renamed service to web, changed to bind mount
- **Files modified:** docker-compose.yml

**2. [Rule 2 - Missing Critical] Added data/ to .gitignore**
- **Found during:** Verification
- **Issue:** data/ directory would be committed with database
- **Fix:** Added data/ to .gitignore
- **Files modified:** .gitignore

## Verification Results

- [x] uvicorn installs successfully in venv
- [x] `python manage.py check` passes (0 issues)
- [x] data/ directory created on settings import
- [x] `docker-compose config` validates successfully

## Usage

```bash
# Local development with docker-compose
cp .env.example .env
# Edit .env and add PTF_ENCRYPTION_KEY
docker-compose up -d

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
