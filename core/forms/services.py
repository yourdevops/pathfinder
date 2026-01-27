"""Service creation wizard forms."""
import re
from django import forms
from core.models import Project, Blueprint, BlueprintVersion, Service, ProjectConnection


class BlueprintStepForm(forms.Form):
    """Step 1: Select project, blueprint, and service name."""

    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(status='active'),
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
        }),
        label='Project',
        help_text='Select the project for this service'
    )

    blueprint = forms.ModelChoiceField(
        queryset=Blueprint.objects.filter(sync_status='synced'),
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
        }),
        label='Blueprint',
        help_text='Select the blueprint template for this service'
    )

    blueprint_version = forms.ModelChoiceField(
        queryset=BlueprintVersion.objects.none(),
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
        }),
        label='Version',
        help_text='Select the blueprint version'
    )

    name = forms.CharField(
        max_length=63,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
            'placeholder': 'my-service',
            'pattern': '[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]',
        }),
        label='Service Name',
        help_text='DNS-compatible name (lowercase, numbers, hyphens)'
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_project = project

        # If project is pre-selected (from project context), filter and set initial
        if project:
            self.fields['project'].initial = project
            self.fields['project'].queryset = Project.objects.filter(pk=project.pk)
            self.fields['project'].widget.attrs['disabled'] = True
            # Filter blueprints available for this project
            self._filter_blueprints_for_project(project)
        else:
            # Global wizard (no project context) - show blueprints available globally
            self._filter_blueprints_globally()

        # Handle blueprint version dynamic loading (will be populated via HTMX)
        if 'blueprint' in self.data:
            try:
                blueprint_id = int(self.data.get('blueprint'))
                self.fields['blueprint_version'].queryset = BlueprintVersion.objects.filter(
                    blueprint_id=blueprint_id
                ).order_by('-sort_key')
            except (ValueError, TypeError):
                pass
        # Also handle prefixed field name from wizard
        elif 'blueprint-blueprint' in self.data:
            try:
                blueprint_id = int(self.data.get('blueprint-blueprint'))
                self.fields['blueprint_version'].queryset = BlueprintVersion.objects.filter(
                    blueprint_id=blueprint_id
                ).order_by('-sort_key')
            except (ValueError, TypeError):
                pass

    def _filter_blueprints_for_project(self, project):
        """Filter blueprints to those available for this project."""
        available_blueprints = []
        for blueprint in Blueprint.objects.filter(sync_status='synced'):
            if blueprint.is_available_for_project(project):
                available_blueprints.append(blueprint.pk)
        self.fields['blueprint'].queryset = Blueprint.objects.filter(pk__in=available_blueprints)

    def _filter_blueprints_globally(self):
        """Filter blueprints to those available globally (have at least one matching connection)."""
        available_blueprints = []
        for blueprint in Blueprint.objects.filter(sync_status='synced'):
            if blueprint.is_available_globally():
                available_blueprints.append(blueprint.pk)
        self.fields['blueprint'].queryset = Blueprint.objects.filter(pk__in=available_blueprints)

    def clean_name(self):
        name = self.cleaned_data['name'].lower()
        # DNS-compatible validation (RFC 1123 label format)
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
            raise forms.ValidationError(
                'Name must be DNS-compatible: lowercase letters, numbers, and hyphens only. '
                'No leading/trailing hyphens.'
            )
        return name

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project') or self.initial_project
        name = cleaned_data.get('name')

        if project and name:
            # Check uniqueness within project
            if Service.objects.filter(project=project, name=name).exists():
                raise forms.ValidationError(
                    f"A service named '{name}' already exists in project '{project.name}'."
                )

            # Check handler length (project-name + - + service-name <= 63)
            handler = f"{project.name}-{name}"
            if len(handler) > 63:
                raise forms.ValidationError(
                    f"Service handler '{handler}' exceeds 63 characters. Use a shorter name."
                )

        return cleaned_data


class RepositoryStepForm(forms.Form):
    """Step 2: Configure repository settings."""

    scm_connection = forms.ModelChoiceField(
        queryset=ProjectConnection.objects.none(),
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
        }),
        label='SCM Connection',
        help_text='Select the Git provider connection'
    )

    repo_mode = forms.ChoiceField(
        choices=[
            ('new', 'Create new repository'),
            ('existing', 'Use existing repository'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'text-dark-accent focus:ring-dark-accent',
        }),
        initial='new',
        label='Repository Mode'
    )

    existing_repo_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
            'placeholder': 'https://github.com/org/repo',
        }),
        label='Existing Repository URL',
        help_text='URL of the existing repository (required for existing repo mode)'
    )

    branch = forms.CharField(
        max_length=100,
        initial='main',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent',
            'placeholder': 'main',
        }),
        label='Branch',
        help_text='Target branch for new repo, or base branch for existing repo PR'
    )

    def __init__(self, *args, project=None, blueprint=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.blueprint = blueprint

        # Populate SCM connections from project
        if project:
            self.fields['scm_connection'].queryset = ProjectConnection.objects.filter(
                project=project
            ).select_related('connection')

    def clean(self):
        cleaned_data = super().clean()
        repo_mode = cleaned_data.get('repo_mode')
        existing_repo_url = cleaned_data.get('existing_repo_url')

        if repo_mode == 'existing' and not existing_repo_url:
            self.add_error('existing_repo_url', 'Repository URL is required for existing repository mode.')

        return cleaned_data


class ConfigurationStepForm(forms.Form):
    """Step 3: Configure service-level environment variables."""

    # This form handles dynamic env vars via JavaScript in template
    # The form itself just captures the JSON data

    env_vars_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        initial='[]'
    )

    def __init__(self, *args, project=None, service_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.service_name = service_name

    def clean_env_vars_json(self):
        import json
        data = self.cleaned_data.get('env_vars_json', '[]')
        try:
            env_vars = json.loads(data)
            if not isinstance(env_vars, list):
                raise forms.ValidationError('Invalid environment variables format.')

            # Validate each var
            for var in env_vars:
                if not isinstance(var, dict):
                    raise forms.ValidationError('Invalid environment variable format.')
                if 'key' not in var or 'value' not in var:
                    raise forms.ValidationError('Each variable must have key and value.')
                key = var['key']
                if key and not re.match(r'^[A-Z][A-Z0-9_]*$', key):
                    raise forms.ValidationError(
                        f'Variable key "{key}" must be uppercase with underscores only.'
                    )

            return env_vars
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format for environment variables.')


class ReviewStepForm(forms.Form):
    """Step 4: Review and confirm service creation."""

    # No fields - this is a read-only review step
    # The template displays all collected data

    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-dark-border bg-dark-bg text-dark-accent focus:ring-dark-accent',
        }),
        label='I confirm the service configuration is correct'
    )
