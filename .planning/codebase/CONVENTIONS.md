# Coding Conventions

**Analysis Date:** 2026-01-21

## Project Stage

This is an early-stage Django 6.0 project (initial commit phase). The codebase currently contains only skeleton Django configuration files. Conventions documented here reflect Django defaults and the minimal patterns currently in use.

## Naming Patterns

**Files:**
- Django module files follow Django conventions: `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `manage.py`
- No custom apps have been created yet; only core Django project structure exists
- Lowercase with underscores: `pathfinder/settings.py`, `pathfinder/urls.py`

**Functions:**
- Python standard: `snake_case` for function names
- Django default examples in generated files: `main()` in `manage.py`, `get_asgi_application()` from Django core

**Variables:**
- Python standard: `snake_case` for variables and constants
- Django settings use `UPPER_CASE` for configuration constants (e.g., `DEBUG`, `ALLOWED_HOSTS`, `SECRET_KEY`)
- Example in `pathfinder/settings.py`: `BASE_DIR`, `INSTALLED_APPS`, `MIDDLEWARE`, `DATABASES`

**Types:**
- No type hints currently used in project code
- Project uses Python 3.13 (modern syntax support available)

## Code Style

**Formatting:**
- No explicit formatter configured (Black, autopep8, etc.)
- Django-generated code follows PEP 8 defaults
- Module docstrings present in all generated files

**Linting:**
- No linter configured (no `.pylintrc`, `.flake8`, etc.)
- No linting tool dependencies installed in venv (only Django 6.0.1)
- Code quality checks are not automated

**Comments and Docstrings:**
- Module-level docstrings included in auto-generated files
- Standard Python triple-quote format: `"""docstring"""`
- Django comments (e.g., `# SECURITY WARNING:`) used for important settings

## Import Organization

**Order:**
1. Standard library imports: `os`, `sys`, `pathlib.Path`
2. Django imports: `from django.*`
3. Project imports: (none yet, as no custom apps exist)

**Path Aliases:**
- Not in use; project uses direct imports only
- Example patterns from existing code:
  - `from pathlib import Path`
  - `from django.core.asgi import get_asgi_application`
  - `from django.urls import path, include`

## Error Handling

**Patterns:**
- Exception handling follows Django conventions
- `manage.py` uses try/except for ImportError with custom message
- No custom error handling implemented yet in application code

**Structure in manage.py:**
```python
try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc
```

## Logging

**Framework:** Not explicitly configured
- Uses Django's default logging (available but not customized)
- Entrypoint shell script uses `echo` for informational output
- No application logging framework configured yet

## Settings & Configuration

**Location:** `pathfinder/settings.py`

**Key Settings Patterns:**
- Database configuration uses dict format: `DATABASES = {'default': {...}}`
- List-based config for middleware and installed apps
- Path handling uses `pathlib.Path` (modern Django approach)
- Context processors pattern with list of strings

**Environment Variables:**
- None currently used; hardcoded for development
- Django DEBUG mode hardcoded to `True`
- SECRET_KEY hardcoded (development only)

## Django-Specific Patterns

**URL Configuration:**
- Located in `pathfinder/urls.py`
- Uses path-based routing (not re_path):
  ```python
  from django.urls import path
  urlpatterns = [
      path('admin/', admin.site.urls),
  ]
  ```

**WSGI/ASGI:**
- Both `wsgi.py` and `asgi.py` configured
- Standard Django boilerplate approach
- Appropriate for gunicorn (WSGI) deployment

**Admin Interface:**
- Enabled by default: `django.contrib.admin` in INSTALLED_APPS
- Default admin site at `/admin/`

## Future Conventions to Establish

When creating custom Django apps, establish these patterns:

**Models:**
- Use `models.Model` as base class
- Name model files in singular (model.py or models.py)
- Use snake_case for field names

**Views:**
- Use class-based views (CBV) as default unless function views are simpler
- Name files `views.py`
- Inherit from appropriate Django generic views

**Tests:**
- Create `tests/` directory or `tests.py` file per app
- Use Django's TestCase class
- Follow test naming: `test_*.py` or `*_test.py`

---

*Convention analysis: 2026-01-21*
