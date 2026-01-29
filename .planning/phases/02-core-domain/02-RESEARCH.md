# Phase 2: Core Domain - Research

**Researched:** 2026-01-22
**Domain:** Django models (Projects, Environments, Membership), HTMX tabs, RBAC, sidebar navigation
**Confidence:** HIGH

## Summary

This research covers the technical foundation for implementing Phase 2: Core Domain, which introduces Projects and Environments with role-based membership and a restructured navigation sidebar with context-replacing patterns.

The standard approach uses Django models with ForeignKey relationships (Project -> Environment), a custom through model for project membership (ProjectMembership linking Groups to Projects with roles), and JSONField for storing env_vars as arrays of key-value-lock dictionaries. HTMX with django-htmx middleware enables partial content swaps for tabbed interfaces without full page reloads.

Key decisions from CONTEXT.md are locked: Groups (not users) assigned to projects, context-replacing sidebar pattern (AWS Console style), HTMX partial swaps for tabs, first environment becomes default, env vars inherit with override capability, and modal-based project creation.

**Primary recommendation:** Implement Project and Environment models with ForeignKey relationships, ProjectMembership as a through model with project_role field, use django-htmx for request detection and template partials for tab content, restructure sidebar with project-context navigation replacing main nav when viewing a project.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 6.0.1 | Web framework, ORM | Already installed |
| django-htmx | 1.27+ | HTMX request detection | Adds request.htmx, handles CSRF |
| htmx | 2.0+ | Frontend dynamic updates | Partial swaps, no JS framework needed |
| django-auditlog | 3.4.1 | Audit logging | Already installed from Phase 1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-template-partials | latest | Reusable template fragments | Alternative to separate partial files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| django-htmx | Manual header checking | django-htmx adds middleware, typed attributes, CSRF handling |
| htmx CDN | npm/bundled htmx | CDN is simpler for Django projects, no build step |
| JSONField env_vars | Separate EnvVar model | JSONField simpler for key-value-lock, no extra joins |

**Installation:**
```bash
pip install django-htmx
```

**htmx via CDN in base template:**
```html
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
```

## Architecture Patterns

### Recommended Project Structure
```
core/
├── models.py              # Add Project, Environment, ProjectMembership
├── views/
│   ├── projects.py        # Project CRUD, tabs, membership
│   └── environments.py    # Environment CRUD within projects
├── templates/
│   └── core/
│       ├── projects/
│       │   ├── list.html
│       │   ├── detail.html
│       │   ├── create_modal.html
│       │   ├── _services_tab.html
│       │   ├── _environments_tab.html
│       │   ├── _members_tab.html
│       │   └── _settings_tab.html
│       └── environments/
│           ├── create.html
│           ├── detail.html
│           └── _env_vars.html
└── urls.py                # Add project and environment URL patterns
```

### Pattern 1: Project Model with UUID and env_vars JSONField
**What:** Project model with DNS-compatible name, UUID for URLs, env_vars as JSONField
**When to use:** Primary organizational unit storing shared configuration
**Example:**
```python
# Source: Phase 1 patterns + docs/projects.md
import uuid
from django.db import models
from django.conf import settings

class Project(models.Model):
    """Project: primary organizational unit for services."""
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=20, unique=True)  # DNS-compatible
    description = models.TextField(blank=True)
    env_vars = models.JSONField(default=list)  # [{"key": "X", "value": "Y", "lock": true}]
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive'), ('archived', 'Archived')],
        default='active'
    )
    created_by = models.CharField(max_length=150, blank=True)  # Denormalized username
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_project'
        ordering = ['name']

    def __str__(self):
        return self.name
```

### Pattern 2: Environment Model with Project ForeignKey
**What:** Environment belonging to a Project with inherited env_vars
**When to use:** Deployment target configuration within a project
**Example:**
```python
# Source: docs/environments.md
class Environment(models.Model):
    """Environment: deployment target within a Project."""
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='environments'
    )
    name = models.CharField(max_length=20)  # DNS-compatible, unique within project
    description = models.TextField(blank=True)
    env_vars = models.JSONField(default=list)  # Override/extend project env_vars
    is_production = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active'
    )
    order = models.IntegerField(default=10)  # dev=10, staging=20, prod=30
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_environment'
        unique_together = ['project', 'name']
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.project.name}/{self.name}"
```

### Pattern 3: ProjectMembership Through Model
**What:** Links Groups to Projects with a project_role
**When to use:** Project access control via group assignment
**Example:**
```python
# Source: docs/rbac.md, django-organizations pattern
class ProjectMembership(models.Model):
    """Assigns a Group to a Project with a specific role."""
    PROJECT_ROLES = [
        ('owner', 'Owner'),
        ('contributor', 'Contributor'),
        ('viewer', 'Viewer'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    group = models.ForeignKey(
        'core.Group',
        on_delete=models.CASCADE,
        related_name='project_memberships'
    )
    project_role = models.CharField(max_length=20, choices=PROJECT_ROLES)
    added_by = models.CharField(max_length=150, blank=True)  # Denormalized username
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_project_membership'
        unique_together = ['project', 'group']

    def __str__(self):
        return f"{self.group.name} -> {self.project.name} ({self.project_role})"
```

### Pattern 4: HTMX Tab Navigation with Partial Templates
**What:** Tabbed interface using HTMX to swap content without full page reload
**When to use:** Project detail page with Services/Environments/Members/Settings tabs
**Example:**
```python
# Source: django-htmx patterns, spookylukey/django-htmx-patterns
# views/projects.py
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET

def project_detail(request, project_uuid):
    """Main project detail view - renders full page."""
    project = get_object_or_404(Project, uuid=project_uuid)
    tab = request.GET.get('tab', 'services')

    # For htmx requests, return only the partial
    if request.htmx:
        template = f'core/projects/_{tab}_tab.html'
        return render(request, template, {'project': project})

    # Full page with all context
    return render(request, 'core/projects/detail.html', {
        'project': project,
        'active_tab': tab,
    })
```

```html
<!-- Source: HTMX documentation + django-htmx patterns -->
<!-- core/projects/detail.html -->
{% extends "base.html" %}
{% block content %}
<div class="p-6">
    <!-- Project Header -->
    <h1 class="text-2xl font-bold">{{ project.name }}</h1>
    <p class="text-dark-muted">{{ project.description }}</p>

    <!-- Tab Navigation -->
    <nav class="flex space-x-4 border-b border-dark-border mt-6">
        <button hx-get="{% url 'projects:detail' project.uuid %}?tab=services"
                hx-target="#tab-content"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="tab-btn {% if active_tab == 'services' %}active{% endif %}">
            Services
        </button>
        <button hx-get="{% url 'projects:detail' project.uuid %}?tab=environments"
                hx-target="#tab-content"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="tab-btn {% if active_tab == 'environments' %}active{% endif %}">
            Environments
        </button>
        <button hx-get="{% url 'projects:detail' project.uuid %}?tab=members"
                hx-target="#tab-content"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="tab-btn {% if active_tab == 'members' %}active{% endif %}">
            Members
        </button>
        <button hx-get="{% url 'projects:detail' project.uuid %}?tab=settings"
                hx-target="#tab-content"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="tab-btn {% if active_tab == 'settings' %}active{% endif %}">
            Settings
        </button>
    </nav>

    <!-- Tab Content -->
    <div id="tab-content" class="mt-6">
        {% include "core/projects/_"|add:active_tab|add:"_tab.html" %}
    </div>
</div>
{% endblock %}
```

### Pattern 5: Environment Variables Inheritance
**What:** Merge env_vars from Project -> Environment with lock override
**When to use:** Computing effective env_vars for display or deployment
**Example:**
```python
# Source: docs/projects.md env var merge behavior
def get_merged_env_vars(project, environment=None):
    """
    Merge env_vars: Project -> Environment
    Locked vars cannot be overridden downstream.
    Returns: list of {"key": str, "value": str, "lock": bool, "source": str}
    """
    merged = {}

    # Start with project vars
    for var in project.env_vars:
        merged[var['key']] = {
            'value': var['value'],
            'lock': var.get('lock', False),
            'source': 'project'
        }

    if environment:
        for var in environment.env_vars:
            key = var['key']
            if key in merged and merged[key]['lock']:
                # Locked at project level - keep project value, mark as inherited
                merged[key]['inherited'] = True
            else:
                # Can override
                merged[key] = {
                    'value': var['value'],
                    'lock': var.get('lock', False),
                    'source': 'environment'
                }

    # Convert to list format
    return [
        {'key': k, **v}
        for k, v in merged.items()
    ]
```

### Pattern 6: Context-Replacing Sidebar Navigation
**What:** When viewing a project, replace main nav with project-specific nav + back button
**When to use:** AWS Console / Jenkins style nested navigation
**Example:**
```python
# Source: CONTEXT.md decision + AWS Console pattern
# context_processors.py - add project context
def navigation_context(request):
    """Provide navigation context including active project."""
    context = {
        'in_project_context': False,
        'current_project': None,
    }

    # Check if we're in a project-scoped URL
    if hasattr(request, 'resolver_match') and request.resolver_match:
        if 'project_uuid' in request.resolver_match.kwargs:
            from core.models import Project
            try:
                project = Project.objects.get(
                    uuid=request.resolver_match.kwargs['project_uuid']
                )
                context['in_project_context'] = True
                context['current_project'] = project
            except Project.DoesNotExist:
                pass

    return context
```

```html
<!-- Source: CONTEXT.md sidebar restructure decision -->
<!-- core/components/nav.html - conditional nav based on context -->
{% if in_project_context %}
    <!-- Project-scoped navigation -->
    <aside class="fixed left-0 top-0 h-full w-64 bg-dark-surface border-r border-dark-border flex flex-col">
        <!-- Back to main nav -->
        <div class="p-4 border-b border-dark-border">
            <a href="{% url 'projects:list' %}" class="flex items-center text-dark-muted hover:text-dark-text">
                <svg class="w-5 h-5 mr-2"><!-- back arrow --></svg>
                Back to Projects
            </a>
            <h2 class="text-lg font-bold text-dark-text mt-2">{{ current_project.name }}</h2>
        </div>

        <!-- Project tabs as nav items -->
        <nav class="flex-1 p-4 space-y-1">
            <a href="{% url 'projects:detail' current_project.uuid %}?tab=services" class="nav-item">Services</a>
            <a href="{% url 'projects:detail' current_project.uuid %}?tab=environments" class="nav-item">Environments</a>
            <a href="{% url 'projects:detail' current_project.uuid %}?tab=members" class="nav-item">Members</a>
            <a href="{% url 'projects:detail' current_project.uuid %}?tab=settings" class="nav-item">Settings</a>
        </nav>
    </aside>
{% else %}
    <!-- Main navigation (restructured per CONTEXT.md) -->
    <aside class="fixed left-0 top-0 h-full w-64 bg-dark-surface border-r border-dark-border flex flex-col">
        <!-- Logo as home -->
        <div class="p-4 border-b border-dark-border">
            <a href="/" class="text-xl font-bold text-dark-text">Pathfinder</a>
        </div>

        <nav class="flex-1 p-4 space-y-1">
            <a href="{% url 'projects:list' %}" class="nav-item">Projects</a>
            <a href="{% url 'blueprints:list' %}" class="nav-item">Blueprints</a>
            <a href="{% url 'connections:list' %}" class="nav-item">Integrations</a>

            {% if is_admin %}
            <div class="mt-6">
                <h3 class="text-xs font-semibold text-dark-muted uppercase">Settings</h3>
                <a href="#" class="nav-item">General</a>
                <a href="{% url 'users:list' %}" class="nav-item">Users</a>
                <a href="{% url 'groups:list' %}" class="nav-item">Groups</a>
                <a href="{% url 'audit:list' %}" class="nav-item">Audit Log</a>
            </div>
            {% endif %}
        </nav>

        <!-- User profile at bottom (slide-out panel trigger) -->
        <div class="p-4 border-t border-dark-border">
            <!-- User info + logout -->
        </div>
    </aside>
{% endif %}
```

### Pattern 7: Modal Form with HTMX
**What:** Project creation via modal dialog
**When to use:** Quick creation without leaving list page
**Example:**
```html
<!-- Source: spookylukey/django-htmx-patterns modals.rst -->
<!-- Button to open modal -->
<button hx-get="{% url 'projects:create_modal' %}"
        hx-target="body"
        hx-swap="beforeend"
        class="btn-primary">
    Create Project
</button>

<!-- Modal template: core/projects/create_modal.html -->
<dialog id="project-modal" data-onload-showmodal>
    <form hx-post="{% url 'projects:create' %}"
          hx-target="#project-modal"
          hx-swap="innerHTML">
        {% csrf_token %}
        <h2>Create Project</h2>
        {{ form.as_p }}
        <div class="flex justify-end space-x-2">
            <button type="button" onclick="this.closest('dialog').close()" class="btn-secondary">
                Cancel
            </button>
            <button type="submit" class="btn-primary">Create</button>
        </div>
    </form>
</dialog>

<script>
document.body.addEventListener('htmx:afterSettle', function(evt) {
    const dialog = evt.target.querySelector('dialog[data-onload-showmodal]');
    if (dialog) dialog.showModal();
});
</script>
```

### Anti-Patterns to Avoid
- **Individual user-to-project membership:** Use Groups for all project access (AD-compatible)
- **Separate env var model with ForeignKey:** JSONField is simpler for key-value storage
- **Full page reloads for tabs:** Use HTMX partial swaps
- **Nested JSON `__contains` on SQLite:** SQLite has limited JSONField query support
- **Hardcoding project context detection:** Use URL resolver kwargs

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTMX request detection | Custom header parsing | django-htmx middleware | Handles all HX-* headers, typed attributes |
| Tab state in URL | JavaScript history manipulation | hx-push-url="true" | HTMX handles browser history |
| Modal show/hide | Custom JavaScript | HTML5 `<dialog>` element | Native accessibility, focus management |
| CSRF with HTMX | Manual token injection | django-htmx template tag | Automatic CSRF handling |
| Project role checking | Inline permission checks | Permission helper functions | Reusable, testable, consistent |

**Key insight:** HTMX with django-htmx handles most interactivity needs. The HTML5 `<dialog>` element provides native modal behavior with accessibility built in.

## Common Pitfalls

### Pitfall 1: JSONField Queries on SQLite
**What goes wrong:** `__contains` lookup on nested arrays fails silently or returns wrong results
**Why it happens:** SQLite's JSON support is limited; `__contains` doesn't work for nested structures
**How to avoid:** For searching within env_vars, filter in Python or use exact key lookups
**Warning signs:** Queries returning unexpected empty results

### Pitfall 2: N+1 Queries in Project List
**What goes wrong:** One query per project to count environments/members
**Why it happens:** Accessing related objects in template loop
**How to avoid:** Use `annotate()` with `Count()` or `prefetch_related()`
**Warning signs:** Many similar queries in debug toolbar

```python
# Good: Single query with counts
projects = Project.objects.annotate(
    env_count=Count('environments'),
    member_count=Count('memberships')
)
```

### Pitfall 3: Race Condition on Default Environment
**What goes wrong:** Two environments created simultaneously both marked as default
**Why it happens:** Check-then-set without transaction
**How to avoid:** Use `select_for_update()` or handle in model save with transaction
**Warning signs:** Multiple is_default=True environments in same project

```python
# Safe default environment handling
from django.db import transaction

@transaction.atomic
def create_environment(project, name, **kwargs):
    # Lock the project row
    project = Project.objects.select_for_update().get(pk=project.pk)
    is_first = not Environment.objects.filter(project=project).exists()
    env = Environment.objects.create(
        project=project,
        name=name,
        is_default=is_first,
        **kwargs
    )
    return env
```

### Pitfall 4: Forgetting HtmxMiddleware
**What goes wrong:** `request.htmx` is undefined
**Why it happens:** Middleware not added to settings
**How to avoid:** Add `django_htmx.middleware.HtmxMiddleware` to MIDDLEWARE
**Warning signs:** AttributeError on request.htmx

### Pitfall 5: HTMX Caching Issues
**What goes wrong:** Same content served for htmx and non-htmx requests
**Why it happens:** HTTP caching ignores HX-Request header
**How to avoid:** Use `@vary_on_headers("HX-Request")` decorator
**Warning signs:** Stale content after navigation

### Pitfall 6: Project Role Hierarchy Not Computed
**What goes wrong:** User in multiple groups gets lowest role instead of highest
**Why it happens:** Checking first matching membership only
**How to avoid:** Query all memberships, select max role
**Warning signs:** Owner-level user denied access as contributor

```python
# Compute highest project role for user
def get_user_project_role(user, project):
    """Return highest project role for user, or None."""
    ROLE_PRIORITY = {'owner': 3, 'contributor': 2, 'viewer': 1}

    # Check SystemRoles first
    if has_system_role(user, 'admin') or has_system_role(user, 'operator'):
        return 'owner'

    # Get all memberships through user's groups
    memberships = ProjectMembership.objects.filter(
        project=project,
        group__memberships__user=user,
        group__status='active'
    )

    if not memberships.exists():
        return None

    # Return highest role
    roles = [m.project_role for m in memberships]
    return max(roles, key=lambda r: ROLE_PRIORITY.get(r, 0))
```

## Code Examples

Verified patterns from official sources:

### django-htmx Middleware Setup
```python
# Source: django-htmx.readthedocs.io
# settings.py
MIDDLEWARE = [
    # ... existing middleware ...
    'django_htmx.middleware.HtmxMiddleware',
]
```

### HTMX Script and CSRF Setup in Base Template
```html
<!-- Source: django-htmx docs + htmx.org -->
{% load static %}
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Pathfinder{% endblock %}</title>
    {% tailwind_css %}
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <!-- CSRF for HTMX -->
    <meta name="csrf-token" content="{{ csrf_token }}">
    <script>
        document.body.addEventListener('htmx:configRequest', (event) => {
            event.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content;
        });
    </script>
</head>
```

### Project Permission Mixins
```python
# Source: Phase 1 patterns + docs/rbac.md
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

class ProjectPermissionMixin:
    """Base mixin for project-scoped views."""
    required_role = None  # Set in subclass: 'viewer', 'contributor', 'owner'

    def dispatch(self, request, *args, **kwargs):
        project = get_object_or_404(Project, uuid=kwargs.get('project_uuid'))
        user_role = get_user_project_role(request.user, project)

        if not user_role:
            messages.error(request, 'You do not have access to this project.')
            return redirect('projects:list')

        role_hierarchy = ['viewer', 'contributor', 'owner']
        if role_hierarchy.index(user_role) < role_hierarchy.index(self.required_role):
            messages.error(request, 'You do not have permission for this action.')
            return redirect('projects:detail', project_uuid=project.uuid)

        self.project = project
        self.user_project_role = user_role
        return super().dispatch(request, *args, **kwargs)

class ProjectViewerMixin(ProjectPermissionMixin):
    required_role = 'viewer'

class ProjectContributorMixin(ProjectPermissionMixin):
    required_role = 'contributor'

class ProjectOwnerMixin(ProjectPermissionMixin):
    required_role = 'owner'
```

### Environment Default Handling on Save
```python
# Source: docs/environments.md default environment rules
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Environment)
def handle_environment_default(sender, instance, created, **kwargs):
    """Ensure exactly one default environment per project."""
    if created and instance.is_default:
        # New environment marked as default - unmark others
        Environment.objects.filter(
            project=instance.project,
            is_default=True
        ).exclude(pk=instance.pk).update(is_default=False)
    elif created and not instance.is_default:
        # Check if this is the first environment
        if not Environment.objects.filter(
            project=instance.project,
            is_default=True
        ).exists():
            instance.is_default = True
            instance.save(update_fields=['is_default'])

@receiver(post_delete, sender=Environment)
def handle_default_deletion(sender, instance, **kwargs):
    """If default is deleted, promote next environment."""
    if instance.is_default:
        next_env = Environment.objects.filter(
            project=instance.project
        ).order_by('order', 'name').first()
        if next_env:
            next_env.is_default = True
            next_env.save(update_fields=['is_default'])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jQuery AJAX for dynamic UI | HTMX declarative attributes | 2020+ | Less JavaScript, server-rendered HTML |
| Custom modal JavaScript | HTML5 `<dialog>` element | 2022+ | Native accessibility, focus trapping |
| Separate permission tables | JSONField for simple lists | Django 3.1+ | Simpler schema for key-value data |
| Alpine.js for interactions | HTMX + minimal JS | 2024+ | Even less client JS, progressive enhancement |

**Deprecated/outdated:**
- Manual HTMX header checking: Use django-htmx middleware
- Custom modal implementations: Use native `<dialog>` element
- Storing env vars in separate table: JSONField simpler unless you need complex queries

## Open Questions

Things that couldn't be fully resolved:

1. **SCM Connection Attachment to Project (PROJ-05)**
   - What we know: Projects can have SCM connections attached
   - What's unclear: Model relationship not fully defined in docs (ForeignKey? M2M?)
   - Recommendation: Likely M2M via EnvironmentConnection model in Phase 3; for Phase 2, note placeholder

2. **User Profile Slide-out Panel**
   - What we know: CONTEXT.md specifies slide-out panel for user profile
   - What's unclear: Best implementation (CSS only vs HTMX)
   - Recommendation: CSS transition + toggle class; minimal JS

3. **Column Sorting/Filtering on Project List**
   - What we know: Marked as Claude's discretion
   - What's unclear: Whether to implement in Phase 2 or defer
   - Recommendation: Basic name sort; advanced filtering in later phase

## Sources

### Primary (HIGH confidence)
- [django-htmx 1.27.0 documentation](https://django-htmx.readthedocs.io/en/latest/) - Middleware, request.htmx attributes
- [HTMX Documentation](https://htmx.org/docs/) - Attributes, events, partial swaps
- [Django 6.0 Models Documentation](https://docs.djangoproject.com/en/6.0/topics/db/models/) - ForeignKey, JSONField, related_name
- [spookylukey/django-htmx-patterns](https://github.com/spookylukey/django-htmx-patterns) - Partial templates, modals

### Secondary (MEDIUM confidence)
- [Django Ticket #31836](https://code.djangoproject.com/ticket/31836) - SQLite JSONField contains limitations
- [django-organizations pattern](https://pypi.org/project/django-organizations/) - Through model for membership

### Tertiary (LOW confidence)
- WebSearch results on context-replacing sidebar patterns - implementation varies

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Based on installed Django version, official django-htmx docs
- Architecture: HIGH - Standard Django patterns, verified with project docs
- HTMX patterns: HIGH - Official documentation and established community patterns
- Pitfalls: HIGH - SQLite limitation documented in Django tracker
- Sidebar restructure: MEDIUM - Pattern clear but implementation details are discretionary

**Research date:** 2026-01-22
**Valid until:** 2026-02-22 (30 days - stable domain, mature frameworks)
