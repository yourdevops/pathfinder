---
phase: quick-024
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - uv.lock
  - Makefile
  - Dockerfile
  - docker-compose.yml
  - CLAUDE.md
  - README.md
  - .gitignore
  - .python-version
autonomous: true

must_haves:
  truths:
    - "uv sync installs all dependencies correctly"
    - "make run still starts the dev server and worker"
    - "Docker build succeeds with uv instead of pip"
    - "requirements.txt is removed, pyproject.toml is the single source of truth"
    - "CLAUDE.md and README.md reflect uv workflow"
  artifacts:
    - path: "pyproject.toml"
      provides: "Project metadata and dependencies"
      contains: "[project]"
    - path: "uv.lock"
      provides: "Locked dependency versions"
    - path: "Makefile"
      provides: "Updated dev commands using uv"
    - path: "Dockerfile"
      provides: "Container build using uv"
  key_links:
    - from: "Makefile"
      to: "uv"
      via: "uv run / uv sync commands"
      pattern: "uv (run|sync)"
    - from: "Dockerfile"
      to: "pyproject.toml"
      via: "uv sync --frozen"
      pattern: "uv sync"
---

<objective>
Migrate from pip + requirements.txt to uv package management.

Purpose: uv is dramatically faster than pip, provides lockfile support, and replaces the need for manual venv management. This simplifies the developer workflow and container builds.
Output: pyproject.toml with all deps, uv.lock, updated Makefile/Dockerfile/docs
</objective>

<execution_context>
@/Users/fandruhin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fandruhin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@requirements.txt
@Makefile
@Dockerfile
@docker-compose.yml
@CLAUDE.md
@README.md
@.gitignore
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create pyproject.toml, generate uv.lock, remove requirements.txt</name>
  <files>pyproject.toml, uv.lock, .python-version, .gitignore</files>
  <action>
1. Create `pyproject.toml` with:
   - `[project]` section: name="pathfinder", version="0.1.0", requires-python=">=3.13"
   - `dependencies` array with ALL packages from requirements.txt (preserve version constraints as-is)
   - Group deps logically with inline comments matching current requirements.txt sections

2. Create `.python-version` file containing `3.13` (uv uses this for python version management)

3. Run `uv sync` to generate `uv.lock` and create the `.venv` directory

4. Verify all packages install correctly: `uv run python -c "import django; print(django.VERSION)"`

5. Delete `requirements.txt`

6. Update `.gitignore`:
   - Keep existing `.venv` / `venv` entries (uv uses `.venv` by default)
   - No other gitignore changes needed (uv.lock SHOULD be committed)
  </action>
  <verify>
    - `uv sync` completes without errors
    - `uv run python -c "import django; import auditlog; import github; import docker; import semver; import jinja2; print('all imports ok')"` succeeds
    - `requirements.txt` no longer exists
    - `pyproject.toml` exists with all dependencies
    - `uv.lock` exists
  </verify>
  <done>pyproject.toml is the single source of truth for dependencies, uv.lock is generated, requirements.txt is removed</done>
</task>

<task type="auto">
  <name>Task 2: Update Makefile, Dockerfile, and docker-compose.yml for uv</name>
  <files>Makefile, Dockerfile, docker-compose.yml</files>
  <action>
1. Update `Makefile`:
   - Remove the `VENV` and `PYTHON` variables (no more manual venv)
   - Replace `$(PYTHON)` calls with `uv run python`
   - Update `venv` target to run `uv sync` instead of creating venv + pip install
   - Keep the same target names (run, stop, clean, migrate, build, venv) for compatibility
   - The `run` target should still call `./scripts/run-dev.sh` but pass `uv run python` as the PYTHON arg

2. Update `Dockerfile`:
   - Use multi-stage build or install uv via `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`
   - Remove `PIP_NO_CACHE_DIR` and `PIP_DISABLE_PIP_VERSION_CHECK` env vars
   - Add `UV_COMPILE_BYTECODE=1` and `UV_LINK_MODE=copy` env vars
   - Copy `pyproject.toml` and `uv.lock` (instead of requirements.txt)
   - Replace `pip install --no-cache-dir -r requirements.txt` with `uv sync --frozen --no-dev`
   - Keep the rest of the Dockerfile unchanged (user setup, collectstatic, entrypoint, healthcheck)
   - For collectstatic, use `uv run python manage.py collectstatic --noinput`

3. `docker-compose.yml`: No changes needed (it references the Dockerfile, which handles the build).
  </action>
  <verify>
    - `make migrate` runs successfully (uses uv run)
    - `make build` runs successfully (tailwind build via uv run)
    - `docker build -t pathfinder-test .` succeeds (do NOT run this, just verify Dockerfile syntax is valid)
  </verify>
  <done>Makefile uses uv commands, Dockerfile builds with uv, all make targets work</done>
</task>

<task type="auto">
  <name>Task 3: Update CLAUDE.md and README.md to reflect uv workflow</name>
  <files>CLAUDE.md, README.md</files>
  <action>
1. Update `CLAUDE.md`:
   - Replace the "activate venv first" section with uv workflow:
     ```
     When running locally, use uv (no manual venv activation needed):
     ```bash
     # Install/sync dependencies
     uv sync

     # Rebuild UI
     uv run python manage.py tailwind build

     # Collect static files
     uv run python manage.py collectstatic
     ```
   - Keep the "USE Makefile" instruction as-is (Makefile still works)
   - Add note: **Package Management**: uv (pyproject.toml + uv.lock). Do NOT use pip or requirements.txt.

2. Update `README.md`:
   - Replace the Quick Start local section:
     ```
     # Install uv (if not already installed)
     curl -LsSf https://astral.sh/uv/install.sh | sh

     # Install dependencies
     uv sync

     # Rebuild UI
     uv run python manage.py tailwind build

     # Collect static files
     uv run python manage.py collectstatic

     # Run database migrations
     uv run python manage.py migrate

     # Start development server
     make run
     ```
   - Remove any references to `pip install -r requirements.txt` or `python -m venv venv`
   - Keep the rest of README.md unchanged
  </action>
  <verify>
    - CLAUDE.md references uv, not pip/venv activation
    - README.md Quick Start uses uv sync, not pip install
    - No remaining references to `requirements.txt` in either file
  </verify>
  <done>All documentation reflects uv as the package manager, no references to pip/requirements.txt remain</done>
</task>

</tasks>

<verification>
- `uv sync` installs all dependencies
- `uv run python manage.py check` passes (Django system check)
- `make migrate` works
- `make build` works
- No references to `requirements.txt` remain in tracked files (grep -r "requirements.txt" --include="*.md" --include="Makefile" --include="Dockerfile")
- `pyproject.toml` contains all original dependencies
</verification>

<success_criteria>
- pyproject.toml is the single source of truth for Python dependencies
- uv.lock provides reproducible installs
- requirements.txt is deleted
- Makefile, Dockerfile, CLAUDE.md, README.md all updated for uv workflow
- `uv run python manage.py check` passes
- `make run` still works for local development
</success_criteria>

<output>
After completion, create `.planning/quick/024-migrate-to-uv-package-management-from-pi/024-SUMMARY.md`
</output>
