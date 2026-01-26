# Phase 5: Services - Research

**Researched:** 2026-01-26
**Domain:** Django wizard forms, HTMX dynamic updates, Git repository scaffolding, Service model design
**Confidence:** HIGH

## Summary

Phase 5 implements the service creation wizard and service management UI. The implementation builds on established patterns from prior phases: django-formtools SessionWizardView for multi-step wizard, django-htmx for dynamic updates, GitPython for repository scaffolding, and the existing context-replacing sidebar pattern for service detail pages.

The codebase already has all required dependencies installed (django-formtools>=2.5.0, django-htmx>=1.21.0, GitPython>=3.1.0) and proven patterns from Phases 3-4 (connection wizard, blueprint sync, git operations). The research confirms that building on these existing patterns minimizes risk and ensures consistency.

**Primary recommendation:** Use SessionWizardView with session storage for the 4-page wizard, leverage existing git_utils.py for repository scaffolding, and follow the project detail sidebar pattern for service detail pages.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| django-formtools | >=2.5.0 | Multi-step wizard forms | Already installed; SessionWizardView handles step navigation, data persistence, and conditional steps |
| django-htmx | >=1.21.0 | HTMX request detection, partial rendering | Already installed; used throughout codebase for dynamic updates |
| GitPython | >=3.1.0 | Git repository operations | Already installed; proven in Phase 4 for blueprint sync |
| PyGithub | >=2.5.0 | GitHub API operations | Already installed; Phase 3 plugin for repo creation, branch, PR |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-tasks | >=0.4.0 | Background task execution | Async repository scaffolding to avoid HTTP timeout |
| PyYAML | >=6.0.0 | ssp-template.yaml parsing | Reading blueprint manifest for template processing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SessionWizardView | CookieWizardView | Session is more secure for sensitive data, already standard in codebase |
| SessionWizardView | Custom multi-step views | More code, harder to maintain, SessionWizardView handles edge cases |
| GitPython local ops | GitHub API for all git | Git protocol is SCM-agnostic; GitHub API only works for GitHub |

**Installation:**
All dependencies already in requirements.txt. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
core/
├── views/
│   └── services.py          # Service wizard and detail views
├── forms/
│   └── services.py          # Wizard step forms (4 forms)
├── templates/core/services/
│   ├── wizard/
│   │   ├── base.html         # Wizard layout with step progress
│   │   ├── step_blueprint.html    # Page 1: project, blueprint, name
│   │   ├── step_repository.html   # Page 2: SCM connection, repo config
│   │   ├── step_configuration.html # Page 3: env vars
│   │   └── step_review.html       # Page 4: review and create
│   ├── list.html             # Services table within project
│   ├── detail.html           # Service detail with sidebar
│   ├── _details_tab.html     # Details/Settings combined
│   ├── _builds_tab.html      # Builds placeholder
│   └── _environments_tab.html # Environments placeholder
├── tasks.py                  # scaffold_repository task
└── git_utils.py              # Add scaffold functions to existing module
```

### Pattern 1: SessionWizardView for Multi-Step Wizard

**What:** Django-formtools SessionWizardView handles form progression, data persistence, and step navigation automatically.

**When to use:** Any multi-step form flow requiring data persistence across steps.

**Example:**
```python
# Source: Context7 /jazzband/django-formtools
from formtools.wizard.views import SessionWizardView

WIZARD_FORMS = [
    ('blueprint', BlueprintStepForm),
    ('repository', RepositoryStepForm),
    ('configuration', ConfigurationStepForm),
    ('review', ReviewStepForm),
]

class ServiceCreateWizard(LoginRequiredMixin, ProjectContributorMixin, SessionWizardView):
    template_name = 'core/services/wizard/base.html'

    def get_template_names(self):
        step_templates = {
            'blueprint': 'core/services/wizard/step_blueprint.html',
            'repository': 'core/services/wizard/step_repository.html',
            'configuration': 'core/services/wizard/step_configuration.html',
            'review': 'core/services/wizard/step_review.html',
        }
        return [step_templates[self.steps.current]]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        # Pass project and prior step data to forms
        kwargs['project'] = self.project
        if step == 'repository':
            kwargs['blueprint'] = self.get_cleaned_data_for_step('blueprint')['blueprint']
        return kwargs

    def done(self, form_list, form_dict, **kwargs):
        # Create service and trigger scaffolding
        service = self._create_service(form_dict)
        scaffold_repository.enqueue(service_id=service.id)
        return redirect('services:detail',
                       project_name=self.project.name,
                       service_name=service.name)
```

### Pattern 2: Context-Replacing Sidebar for Service Detail

**What:** Service detail page uses sidebar navigation like project detail, replacing main content on tab click.

**When to use:** Entity detail pages with multiple logical sections (details, builds, environments).

**Example:**
```python
# Follow existing pattern from core/views/projects.py
@method_decorator(vary_on_headers("HX-Request"), name='dispatch')
class ServiceDetailView(LoginRequiredMixin, ProjectViewerMixin, TemplateView):
    def get_template_names(self):
        tab = self.request.GET.get('tab', 'details')
        valid_tabs = ['details', 'builds', 'environments']
        if tab not in valid_tabs:
            tab = 'details'
        if self.request.htmx:
            return [f'core/services/_{tab}_tab.html']
        return ['core/services/detail.html']
```

### Pattern 3: Background Task for Repository Scaffolding

**What:** Repository creation and scaffolding runs as background task to avoid HTTP timeout.

**When to use:** Operations that may take >5 seconds (git clone, push, PR creation).

**Example:**
```python
# Source: existing core/tasks.py pattern
@task(queue_name='repository_scaffolding')
def scaffold_repository(service_id: int) -> dict:
    """
    Scaffold repository from blueprint template.

    For new repos: create repo, push template to main.
    For existing repos: create feature branch, apply template, open PR.
    """
    from core.models import Service
    from core.git_utils import (
        clone_repo_shallow, apply_blueprint_template,
        push_changes, cleanup_repo
    )

    service = Service.objects.get(id=service_id)
    # ... scaffolding logic
```

### Anti-Patterns to Avoid

- **Synchronous scaffolding in view:** Git operations can take 10+ seconds; always use background task
- **Hardcoding GitHub API:** Use GitPython for local operations (clone, commit, push); only use plugin API for platform-specific operations (create repo, create PR)
- **Storing wizard state in cookies:** Session storage is more secure and handles larger data
- **Rebuilding navigation patterns:** Use existing sidebar pattern from project detail

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-step form persistence | Custom session handling | SessionWizardView | Handles step validation, back navigation, conditional steps |
| Step progress bar | Custom step tracking | `wizard.steps` in template | SessionWizardView provides step metadata |
| Service name validation | Custom AJAX endpoint | Form clean method + inline HTMX | Django forms handle validation; HTMX handles inline feedback |
| Repository scaffolding | Inline git commands | GitPython + existing git_utils | Proven patterns, error handling, cleanup |
| SCM-agnostic operations | GitHub-only API | GitPython for git, plugin for platform API | Git protocol works everywhere; plugin API for platform-specific |

**Key insight:** SessionWizardView solves 80% of wizard complexity (step management, data persistence, navigation). Fighting it or reimplementing leads to bugs.

## Common Pitfalls

### Pitfall 1: Wizard Form Data Loss on Back Navigation
**What goes wrong:** User goes back a step, data from future steps is lost.
**Why it happens:** Not using SessionWizardView properly or custom implementation.
**How to avoid:** Use SessionWizardView with session storage; it preserves all step data.
**Warning signs:** Users complain about lost data when clicking back.

### Pitfall 2: HTTP Timeout During Repository Scaffolding
**What goes wrong:** Browser shows error after 30-60 seconds during service creation.
**Why it happens:** Synchronous git operations in the view (clone, commit, push).
**How to avoid:** Use django-tasks background task; show "Creating..." status with polling.
**Warning signs:** Gunicorn worker timeouts in logs, 502 errors.

### Pitfall 3: Service Name Uniqueness Race Condition
**What goes wrong:** Two users create services with same name simultaneously.
**Why it happens:** Validation only at form level, not database constraint.
**How to avoid:** unique_together constraint in model, catch IntegrityError in view.
**Warning signs:** Duplicate key errors in production.

### Pitfall 4: Orphaned Wizard Sessions
**What goes wrong:** Session storage fills up with abandoned wizard data.
**Why it happens:** Users start wizard but don't complete it.
**How to avoid:** SessionWizardView uses session prefix; Django session cleanup handles it.
**Warning signs:** SESSION table grows; not usually a problem with default session settings.

### Pitfall 5: Blueprint Version Not Captured
**What goes wrong:** Service created without pinning blueprint version.
**Why it happens:** Only storing blueprint FK, not version FK.
**How to avoid:** Service model has both blueprint FK and blueprint_version FK.
**Warning signs:** Users can't tell which version their service was created from.

## Code Examples

Verified patterns from official sources:

### SessionWizardView with Step-Specific Templates
```python
# Source: Context7 /jazzband/django-formtools
from formtools.wizard.views import SessionWizardView

FORMS = [
    ("blueprint", BlueprintStepForm),
    ("repository", RepositoryStepForm),
    ("configuration", ConfigurationStepForm),
    ("review", ReviewStepForm),
]

TEMPLATES = {
    "blueprint": "core/services/wizard/step_blueprint.html",
    "repository": "core/services/wizard/step_repository.html",
    "configuration": "core/services/wizard/step_configuration.html",
    "review": "core/services/wizard/step_review.html",
}

class ServiceCreateWizard(SessionWizardView):
    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def done(self, form_list, form_dict, **kwargs):
        # All forms valid, create service
        return HttpResponseRedirect('/service/created/')
```

### Wizard Template with Step Progress and Navigation
```html
<!-- Source: Context7 /jazzband/django-formtools -->
{% extends "base.html" %}

{% block content %}
<!-- Step Progress Bar -->
<div class="flex items-center gap-4 mb-8">
    {% for step in wizard.steps.all %}
    <div class="flex items-center">
        <div class="{% if forloop.counter <= wizard.steps.step1 %}bg-dark-accent{% else %}bg-dark-border{% endif %} rounded-full w-8 h-8 flex items-center justify-center text-white">
            {{ forloop.counter }}
        </div>
        <span class="ml-2 {% if step == wizard.steps.current %}text-dark-text font-medium{% else %}text-dark-muted{% endif %}">
            {{ step|title }}
        </span>
    </div>
    {% endfor %}
</div>

<!-- Form -->
<form method="post">
    {% csrf_token %}
    {{ wizard.management_form }}
    {{ wizard.form }}

    <!-- Navigation -->
    <div class="flex justify-between mt-6">
        {% if wizard.steps.prev %}
        <button name="wizard_goto_step" type="submit" formnovalidate
                value="{{ wizard.steps.prev }}" class="btn-secondary">
            Back
        </button>
        {% else %}
        <div></div>
        {% endif %}

        <button type="submit" class="btn-primary">
            {% if wizard.steps.current == wizard.steps.last %}
            Create Service
            {% else %}
            Next
            {% endif %}
        </button>
    </div>
</form>
{% endblock %}
```

### HTMX Request Detection for Tab Navigation
```python
# Source: Context7 /websites/django-htmx_readthedocs_io_en
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers

@method_decorator(vary_on_headers("HX-Request"), name='dispatch')
class ServiceDetailView(TemplateView):
    def get_template_names(self):
        if self.request.htmx:
            # Return partial template for tab content
            return [f'core/services/_{self.get_active_tab()}_tab.html']
        # Return full page template
        return ['core/services/detail.html']
```

### Repository Scaffolding with GitPython
```python
# Source: existing core/git_utils.py patterns
import git
import tempfile
import shutil

def scaffold_new_repository(repo_path: str, blueprint_path: str, variables: dict) -> None:
    """
    Apply blueprint template to empty repository.

    Copies files from blueprint, applies variable substitution,
    and stages all changes.
    """
    import os
    import jinja2

    # Copy blueprint files (excluding manifest and .git)
    exclude = ['ssp-template.yaml', '.git']
    for item in os.listdir(blueprint_path):
        if item not in exclude:
            src = os.path.join(blueprint_path, item)
            dst = os.path.join(repo_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    # Apply variable substitution to templated files
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(repo_path))
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(('.yaml', '.yml', '.json', '.md', '.txt')):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                template = jinja2.Template(content)
                rendered = template.render(**variables)
                with open(filepath, 'w') as f:
                    f.write(rendered)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FormWizard (function-based) | SessionWizardView (class-based) | Django 1.4+ | Use CBV pattern, cleaner code |
| Manual session handling | SessionWizardView storage | django-formtools 2.0+ | Automatic data persistence |
| Full page reloads | HTMX partial updates | 2023+ adoption | Better UX, less JS |

**Deprecated/outdated:**
- `django.contrib.formtools`: Moved to django-formtools package (already using correct package)
- `FormWizard` class: Replaced by `WizardView` subclasses

## Open Questions

Things that couldn't be fully resolved:

1. **Blueprint Template Variable Substitution**
   - What we know: Blueprints can contain Jinja-style variables ({{ service_name }}, {{ project_name }})
   - What's unclear: Exact list of built-in variables; whether blueprints can define custom variables
   - Recommendation: Start with fixed set (service_name, project_name, service_handler); defer custom variables

2. **Existing Repository PR Workflow**
   - What we know: Feature branch + PR for existing repos (per CONTEXT.md)
   - What's unclear: PR template, auto-merge settings, branch protection handling
   - Recommendation: Create minimal PR with description; let repository settings control merge

3. **Service Status Initial Value**
   - What we know: draft -> active on first build (Phase 6)
   - What's unclear: Whether wizard completion sets "draft" or "pending"
   - Recommendation: Use "draft" immediately after wizard; Phase 6 transitions to "active"

## Sources

### Primary (HIGH confidence)
- Context7 `/jazzband/django-formtools` - SessionWizardView usage, templates, navigation
- Context7 `/websites/django-htmx_readthedocs_io_en` - HTMX request detection, client redirect
- Context7 `/websites/djangoproject_en_6_0` - Django forms, class-based views
- Existing codebase: `core/views/projects.py`, `core/views/blueprints.py`, `core/git_utils.py`, `core/tasks.py`

### Secondary (MEDIUM confidence)
- Existing codebase patterns verified working in Phases 1-4
- requirements.txt confirming installed dependencies

### Tertiary (LOW confidence)
- None - all findings verified with primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies already installed and proven in prior phases
- Architecture: HIGH - Following existing patterns from project detail, blueprint sync
- Pitfalls: HIGH - Based on known issues with multi-step forms and git operations

**Research date:** 2026-01-26
**Valid until:** 60 days (stable patterns, no fast-moving dependencies)
