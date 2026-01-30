"""Service creation wizard forms."""

import re

from django import forms

from core.models import Project, ProjectConnection, Service


class ProjectStepForm(forms.Form):
    """Step 1: Select project and service name."""

    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(status="active"),
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent",
            }
        ),
        label="Project",
        help_text="Select the project for this service",
    )

    name = forms.CharField(
        max_length=63,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent",
                "placeholder": "my-service",
                "pattern": "[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]",
            }
        ),
        label="Service Name",
        help_text="DNS-compatible name (lowercase, numbers, hyphens)",
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_project = project

        # If project is pre-selected (from project context), filter and set initial
        if project:
            self.fields["project"].initial = project
            self.fields["project"].queryset = Project.objects.filter(pk=project.pk)
            self.fields["project"].widget.attrs["disabled"] = True

    def clean_name(self):
        name = self.cleaned_data["name"].lower()
        # DNS-compatible validation (RFC 1123 label format)
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
            raise forms.ValidationError(
                "Name must be DNS-compatible: lowercase letters, numbers, and hyphens only. "
                "No leading/trailing hyphens."
            )
        return name

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get("project") or self.initial_project
        name = cleaned_data.get("name")

        if project and name:
            # Check uniqueness within project
            if Service.objects.filter(project=project, name=name).exists():
                raise forms.ValidationError(f"A service named '{name}' already exists in project '{project.name}'.")

            # Check handler length (project-name + - + service-name <= 63)
            handler = f"{project.name}-{name}"
            if len(handler) > 63:
                raise forms.ValidationError(f"Service handler '{handler}' exceeds 63 characters. Use a shorter name.")

        return cleaned_data


class RepositoryStepForm(forms.Form):
    """Step 2: Configure repository settings."""

    scm_connection = forms.ModelChoiceField(
        queryset=ProjectConnection.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent",
            }
        ),
        label="SCM Connection",
        help_text="Select the Git provider connection",
    )

    repo_mode = forms.ChoiceField(
        choices=[
            ("new", "Create new repository"),
            ("existing", "Use existing repository"),
        ],
        widget=forms.RadioSelect(
            attrs={
                "class": "text-dark-accent focus:ring-dark-accent",
            }
        ),
        initial="new",
        label="Repository Mode",
    )

    existing_repo_url = forms.URLField(
        required=False,
        widget=forms.URLInput(
            attrs={
                "class": "w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent",
                "placeholder": "https://github.com/org/repo",
            }
        ),
        label="Existing Repository URL",
        help_text="URL of the existing repository (required for existing repo mode)",
    )

    branch = forms.CharField(
        max_length=100,
        initial="main",
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-dark-accent",
                "placeholder": "main",
            }
        ),
        label="Branch",
        help_text="Target branch for new repo, or base branch for existing repo PR",
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project

        # Populate SCM connections from project
        if project:
            self.fields["scm_connection"].queryset = ProjectConnection.objects.filter(project=project).select_related(
                "connection"
            )

    def clean(self):
        cleaned_data = super().clean()
        repo_mode = cleaned_data.get("repo_mode")
        existing_repo_url = cleaned_data.get("existing_repo_url")

        if repo_mode == "existing" and not existing_repo_url:
            self.add_error(
                "existing_repo_url",
                "Repository URL is required for existing repository mode.",
            )

        return cleaned_data


class ConfigurationStepForm(forms.Form):
    """Step 3: Configure service-level environment variables."""

    # This form handles dynamic env vars via JavaScript in template
    # The form itself just captures the JSON data

    env_vars_json = forms.CharField(required=False, widget=forms.HiddenInput(), initial="[]")

    def __init__(self, *args, project=None, service_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.service_name = service_name

    def clean_env_vars_json(self):
        import json

        data = self.cleaned_data.get("env_vars_json", "[]")
        try:
            env_vars = json.loads(data)
            if not isinstance(env_vars, list):
                raise forms.ValidationError("Invalid environment variables format.")

            # Validate each var
            for var in env_vars:
                if not isinstance(var, dict):
                    raise forms.ValidationError("Invalid environment variable format.")
                if "key" not in var or "value" not in var:
                    raise forms.ValidationError("Each variable must have key and value.")
                key = var["key"]
                if key and not re.match(r"^[A-Z][A-Z0-9_]*$", key):
                    raise forms.ValidationError(f'Variable key "{key}" must be uppercase with underscores only.')

            return env_vars
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format for environment variables.")


class ReviewStepForm(forms.Form):
    """Step 4: Review and confirm service creation."""

    # No fields - this is a read-only review step
    # The template displays all collected data

    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "rounded border-dark-border bg-dark-bg text-dark-accent focus:ring-dark-accent",
            }
        ),
        label="I confirm the service configuration is correct",
    )
