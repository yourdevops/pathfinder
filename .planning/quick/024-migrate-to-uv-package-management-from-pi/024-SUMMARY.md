---
phase: quick-024
plan: 01
subsystem: tooling
tags: [uv, package-management, pyproject-toml, dockerfile, makefile]
dependency-graph:
  requires: []
  provides: [uv-package-management, pyproject-toml, uv-lock]
  affects: [all-phases]
tech-stack:
  added: [uv]
  removed: [pip, venv, requirements.txt]
  patterns: [uv-sync, uv-run]
key-files:
  created: [pyproject.toml, uv.lock, .python-version]
  modified: [Makefile, Dockerfile, CLAUDE.md, README.md, pathfinder/urls.py]
  removed: [requirements.txt]
decisions:
  - id: q024-01
    description: "uv replaces pip+venv for all package management"
    rationale: "Faster installs, lockfile support, no manual venv management"
metrics:
  duration: "2 min"
  completed: "2026-01-30"
  tasks: 3/3
---

# Quick Task 024: Migrate to uv Package Management Summary

**One-liner:** Replaced pip + requirements.txt with uv (pyproject.toml + uv.lock) across Makefile, Dockerfile, and docs.

## What Was Done

### Task 1: Create pyproject.toml, generate uv.lock, remove requirements.txt
- Created `pyproject.toml` with all dependencies from requirements.txt organized by phase
- Created `.python-version` file (3.13) for uv python version management
- Generated `uv.lock` via `uv sync`
- Verified all imports work correctly
- Deleted `requirements.txt`
- **Commit:** 1b58676

### Task 2: Update Makefile, Dockerfile, and docker-compose.yml for uv
- Removed VENV/PYTHON variables from Makefile, replaced with `uv run python` / `uv sync`
- Updated Dockerfile to install uv via `COPY --from=ghcr.io/astral-sh/uv:latest`
- Replaced pip env vars with `UV_COMPILE_BYTECODE=1` and `UV_LINK_MODE=copy`
- Replaced `pip install -r requirements.txt` with `uv sync --frozen --no-dev`
- docker-compose.yml unchanged (references Dockerfile which handles the build)
- **Commit:** f43f2e6

### Task 3: Update CLAUDE.md and README.md to reflect uv workflow
- Replaced venv activation instructions with uv workflow in CLAUDE.md
- Added "Package Management" note warning against pip/requirements.txt
- Updated Quick Start section in README.md with uv install and sync commands
- **Commit:** 110bb86

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed URL converter registration order in pathfinder/urls.py**
- **Found during:** Task 2 verification (make migrate)
- **Issue:** `register_converter(DnsLabelConverter, "dns")` was called AFTER `from core.urls import ...` which uses `<dns:...>` patterns at module-level, causing `ImproperlyConfigured` error
- **Fix:** Moved `register_converter` call before the `core.urls` import
- **Files modified:** pathfinder/urls.py
- **Commit:** f43f2e6

## Verification Results

| Check | Result |
|-------|--------|
| `uv sync` completes | PASS |
| All imports work | PASS |
| `requirements.txt` removed | PASS |
| `pyproject.toml` has all deps | PASS |
| `uv.lock` generated | PASS |
| `make migrate` works | PASS |
| `make build` works | PASS |
| `uv run python manage.py check` | PASS (0 issues) |
| No requirements.txt refs in tracked files | PASS (only in .planning history and blueprint templates) |
