"""Service views including creation wizard and detail pages."""
from django.http import HttpResponse
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers

from formtools.wizard.views import SessionWizardView

from core.models import Project, Service, BlueprintVersion
from core.forms.services import (
    BlueprintStepForm, RepositoryStepForm, ConfigurationStepForm, ReviewStepForm
)
from core.permissions import can_access_project
from core.tasks import scaffold_repository


WIZARD_FORMS = [
    ('blueprint', BlueprintStepForm),
    ('repository', RepositoryStepForm),
    ('configuration', ConfigurationStepForm),
    ('review', ReviewStepForm),
]

WIZARD_TEMPLATES = {
    'blueprint': 'core/services/wizard/step_blueprint.html',
    'repository': 'core/services/wizard/step_repository.html',
    'configuration': 'core/services/wizard/step_configuration.html',
    'review': 'core/services/wizard/step_review.html',
}

STEP_TITLES = {
    'blueprint': 'Blueprint',
    'repository': 'Repository',
    'configuration': 'Configuration',
    'review': 'Review',
}


class ServiceCreateWizard(LoginRequiredMixin, SessionWizardView):
    """4-step service creation wizard."""
    form_list = WIZARD_FORMS

    def dispatch(self, request, *args, **kwargs):
        # Get project from URL if provided
        project_name = kwargs.get('project_name')
        if project_name:
            self.project = get_object_or_404(Project, name=project_name, status='active')
            # Check contributor permission
            access = can_access_project(request.user, self.project)
            if not access or access == 'viewer':
                messages.error(request, "You don't have permission to create services in this project.")
                return redirect('projects:detail', project_name=project_name)
        else:
            self.project = None

        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [WIZARD_TEMPLATES[self.steps.current]]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        if step == 'blueprint':
            kwargs['project'] = self.project

        elif step == 'repository':
            # Pass project and blueprint from step 1
            blueprint_data = self.get_cleaned_data_for_step('blueprint')
            if blueprint_data:
                kwargs['project'] = blueprint_data.get('project') or self.project
                kwargs['blueprint'] = blueprint_data.get('blueprint')

        elif step == 'configuration':
            # Pass project and service name for env var inheritance display
            blueprint_data = self.get_cleaned_data_for_step('blueprint')
            if blueprint_data:
                kwargs['project'] = blueprint_data.get('project') or self.project
                kwargs['service_name'] = blueprint_data.get('name')

        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)

        # Step metadata for progress bar
        step_keys = list(dict(WIZARD_FORMS).keys())
        context['steps'] = [
            {
                'key': key,
                'title': STEP_TITLES[key],
                'is_current': key == self.steps.current,
                'index': i,
            }
            for i, (key, _) in enumerate(WIZARD_FORMS)
        ]
        context['current_step_index'] = self.steps.index
        context['step_title'] = STEP_TITLES[self.steps.current]

        # Project context
        context['project'] = self.project

        # Step-specific context
        if self.steps.current == 'blueprint':
            # For HTMX blueprint version loading
            pass

        elif self.steps.current == 'repository':
            # Preview repo name
            blueprint_data = self.get_cleaned_data_for_step('blueprint')
            if blueprint_data:
                project = blueprint_data.get('project') or self.project
                service_name = blueprint_data.get('name')
                if project and service_name:
                    context['preview_repo_name'] = f"{project.name}-{service_name}"

        elif self.steps.current == 'configuration':
            # Show inherited project vars
            blueprint_data = self.get_cleaned_data_for_step('blueprint')
            if blueprint_data:
                project = blueprint_data.get('project') or self.project
                service_name = blueprint_data.get('name')
                context['project_env_vars'] = project.env_vars or [] if project else []
                context['service_name'] = service_name
                # Default SERVICE_NAME variable (locked)
                context['default_service_var'] = {'key': 'SERVICE_NAME', 'value': service_name, 'lock': True}

        elif self.steps.current == 'review':
            # Compile all data for review
            context['review_data'] = self._get_review_data()

        return context

    def _get_review_data(self):
        """Compile all wizard data for review step."""
        blueprint_data = self.get_cleaned_data_for_step('blueprint') or {}
        repository_data = self.get_cleaned_data_for_step('repository') or {}
        config_data = self.get_cleaned_data_for_step('configuration') or {}

        project = blueprint_data.get('project') or self.project
        blueprint = blueprint_data.get('blueprint')
        blueprint_version = blueprint_data.get('blueprint_version')
        service_name = blueprint_data.get('name')

        return {
            'project': project,
            'blueprint': blueprint,
            'blueprint_version': blueprint_version,
            'service_name': service_name,
            'handler': f"{project.name}-{service_name}" if project and service_name else '',
            'scm_connection': repository_data.get('scm_connection'),
            'repo_mode': repository_data.get('repo_mode'),
            'repo_mode_display': 'New repository' if repository_data.get('repo_mode') == 'new' else 'Existing repository',
            'existing_repo_url': repository_data.get('existing_repo_url'),
            'branch': repository_data.get('branch'),
            'env_vars': config_data.get('env_vars_json', []),
        }

    def done(self, form_list, form_dict, **kwargs):
        """Create service and trigger repository scaffolding."""
        # Extract data from all forms
        blueprint_data = form_dict['blueprint'].cleaned_data
        repository_data = form_dict['repository'].cleaned_data
        config_data = form_dict['configuration'].cleaned_data

        project = blueprint_data.get('project') or self.project
        blueprint = blueprint_data['blueprint']
        blueprint_version = blueprint_data['blueprint_version']
        service_name = blueprint_data['name']

        scm_connection = repository_data['scm_connection']
        repo_mode = repository_data['repo_mode']
        existing_repo_url = repository_data.get('existing_repo_url', '')
        branch = repository_data['branch']

        env_vars = config_data.get('env_vars_json', [])

        # Add default SERVICE_NAME variable (locked)
        env_vars = [{'key': 'SERVICE_NAME', 'value': service_name, 'lock': True}] + [
            v for v in env_vars if v.get('key') != 'SERVICE_NAME'
        ]

        # Determine repo URL
        if repo_mode == 'new':
            # Will be set by scaffolding task after repo creation
            repo_url = ''
            repo_is_new = True
        else:
            repo_url = existing_repo_url
            repo_is_new = False

        # Create Service record
        service = Service.objects.create(
            project=project,
            name=service_name,
            blueprint=blueprint,
            blueprint_version=blueprint_version,
            repo_url=repo_url,
            repo_branch=branch,
            repo_is_new=repo_is_new,
            env_vars=env_vars,
            status='draft',
            scaffold_status='pending',
            created_by=self.request.user.username,
        )

        # Enqueue scaffolding task
        scaffold_repository.enqueue(
            service_id=service.id,
            scm_connection_id=scm_connection.connection.id,
        )

        messages.success(
            self.request,
            f'Service "{service_name}" created. Repository scaffolding in progress...'
        )

        return redirect('projects:services', project_name=project.name)


class BlueprintVersionsView(LoginRequiredMixin, View):
    """HTMX endpoint to load blueprint versions."""

    def get(self, request, blueprint_id):
        versions = BlueprintVersion.objects.filter(
            blueprint_id=blueprint_id
        ).order_by('-sort_key')

        html = '<option value="">Select version...</option>'
        for v in versions:
            html += f'<option value="{v.id}">{v.display_name}</option>'

        return HttpResponse(html)


@method_decorator(vary_on_headers("HX-Request"), name='dispatch')
class ServiceDetailView(LoginRequiredMixin, TemplateView):
    """Service detail with HTMX tab navigation."""

    def dispatch(self, request, *args, **kwargs):
        # Get project and service from URL
        project_name = kwargs.get('project_name')
        service_name = kwargs.get('service_name')

        self.project = get_object_or_404(Project, name=project_name, status='active')
        self.service = get_object_or_404(
            Service, project=self.project, name=service_name
        )

        # Check viewer permission
        self.user_project_role = can_access_project(request.user, self.project)
        if not self.user_project_role:
            messages.error(request, "You don't have permission to view this service.")
            return redirect('projects:list')

        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        tab = self.request.GET.get('tab', 'details')
        valid_tabs = ['details', 'builds', 'environments']
        if tab not in valid_tabs:
            tab = 'details'

        if self.request.htmx:
            return [f'core/services/_{tab}_tab.html']
        return ['core/services/detail.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get('tab', 'details')
        valid_tabs = ['details', 'builds', 'environments']
        if tab not in valid_tabs:
            tab = 'details'

        context['project'] = self.project
        context['service'] = self.service
        context['active_tab'] = tab
        context['user_project_role'] = self.user_project_role
        # Pass tab template path for include (avoids invalid Django filter concatenation)
        context['tab_template'] = f'core/services/_{tab}_tab.html'

        # Tab-specific context
        if tab == 'details':
            # Get merged env vars for display
            context['merged_env_vars'] = self.service.get_merged_env_vars()
            # Can edit if contributor or owner
            context['can_edit'] = self.user_project_role in ('contributor', 'owner')

        elif tab == 'builds':
            # Placeholder for Phase 6
            context['builds'] = []  # Will be populated in Phase 6

        elif tab == 'environments':
            # Show environments with deployment info (placeholder for Phase 7)
            context['environments'] = self.project.environments.filter(status='active').order_by('order', 'name')

        return context


class ServiceDeleteView(LoginRequiredMixin, View):
    """Delete a service (owner only)."""

    def dispatch(self, request, *args, **kwargs):
        project_name = kwargs.get('project_name')
        service_name = kwargs.get('service_name')

        self.project = get_object_or_404(Project, name=project_name, status='active')
        self.service = get_object_or_404(
            Service, project=self.project, name=service_name
        )

        # Check owner permission
        role = can_access_project(request.user, self.project)
        if role != 'owner':
            messages.error(request, "Only project owners can delete services.")
            return redirect('services:detail', project_name=project_name, service_name=service_name)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        service_name = self.service.name
        project_name = self.project.name

        # TODO: Consider cleanup of repository if we created it (future enhancement)
        self.service.delete()

        messages.success(request, f'Service "{service_name}" has been deleted.')
        return redirect('projects:detail', project_name=project_name)


class ServiceScaffoldStatusView(LoginRequiredMixin, View):
    """HTMX endpoint to poll scaffold status."""

    def get(self, request, project_name, service_name):
        project = get_object_or_404(Project, name=project_name)
        service = get_object_or_404(Service, project=project, name=service_name)

        # Return status badge HTML
        status_classes = {
            'pending': 'bg-gray-500/20 text-gray-300',
            'running': 'bg-blue-500/20 text-blue-300',
            'success': 'bg-green-500/20 text-green-300',
            'failed': 'bg-red-500/20 text-red-300',
        }

        status_class = status_classes.get(service.scaffold_status, 'bg-gray-500/20 text-gray-300')
        status_label = service.get_scaffold_status_display()

        if service.scaffold_status in ('pending', 'running'):
            html = f'''<span class="px-2 py-1 text-xs rounded {status_class}"
                      hx-get="{request.path}"
                      hx-trigger="every 3s"
                      hx-swap="outerHTML">Scaffold: {status_label}</span>'''
        else:
            html = f'<span class="px-2 py-1 text-xs rounded {status_class}">Scaffold: {status_label}</span>'

        return HttpResponse(html)
