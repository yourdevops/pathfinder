"""CI Workflows forms for repository registration and workflow creation."""

from django import forms

from core.models import (
    CIWorkflow,
    IntegrationConnection,
    ProjectApprovedWorkflow,
    RuntimeFamily,
    StepsRepository,
)
from core.validators import dns_label_validator

DARK_INPUT = "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text placeholder-dark-muted focus:outline-none focus:border-dark-accent"
DARK_SELECT = "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-dark-accent"
DARK_TEXTAREA = "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text placeholder-dark-muted focus:outline-none focus:border-dark-accent"


class StepsRepoRegisterForm(forms.Form):
    """Form for registering a new CI steps repository."""

    name = forms.CharField(
        max_length=63,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text placeholder-dark-muted focus:outline-none focus:border-dark-accent",
                "placeholder": "e.g., pathfinder-steps",
            }
        ),
    )
    git_url = forms.URLField(
        max_length=500,
        help_text="HTTPS URL of the Git repository containing CI step definitions.",
        widget=forms.URLInput(
            attrs={
                "class": "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text placeholder-dark-muted focus:outline-none focus:border-dark-accent",
                "placeholder": "https://github.com/org/ci-steps-repo",
            }
        ),
    )
    connection = forms.ModelChoiceField(
        queryset=IntegrationConnection.objects.filter(plugin_name="github", status="active"),
        required=False,
        empty_label="None (public repository)",
        help_text="Select a GitHub connection for private repositories.",
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-dark-accent",
            }
        ),
    )

    def clean_name(self):
        name = self.cleaned_data["name"]
        if StepsRepository.objects.filter(name=name).exists():
            raise forms.ValidationError("A repository with this name already exists.")
        return name

    def clean_git_url(self):
        git_url = self.cleaned_data["git_url"]
        if StepsRepository.objects.filter(git_url=git_url).exists():
            raise forms.ValidationError("A repository with this URL is already registered.")
        return git_url


class WorkflowCreateForm(forms.Form):
    """Form for creating a new CI workflow with runtime selection."""

    name = forms.CharField(
        max_length=63,
        validators=[dns_label_validator],
        help_text="DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.",
        widget=forms.TextInput(
            attrs={
                "class": DARK_INPUT,
                "placeholder": "e.g., python-api-workflow",
            }
        ),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": DARK_TEXTAREA,
                "rows": 3,
                "placeholder": "Optional description of this workflow...",
            }
        ),
    )
    runtime_family = forms.ChoiceField(
        choices=[],
        widget=forms.Select(
            attrs={
                "class": DARK_SELECT,
            }
        ),
    )
    runtime_version = forms.ChoiceField(
        choices=[],
        widget=forms.Select(
            attrs={
                "class": DARK_SELECT,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate runtime_family choices dynamically
        families = RuntimeFamily.objects.values_list("name", flat=True).distinct().order_by("name")
        family_choices = [("", "-- Select runtime --")] + [(f, f.title()) for f in families]
        self.fields["runtime_family"].choices = family_choices

        # Populate runtime_version if family is already selected (e.g. on form re-render)
        if self.data and self.data.get("runtime_family"):
            family = self.data["runtime_family"]
            versions = self._get_versions_for_family(family)
            self.fields["runtime_version"].choices = [("", "-- Select version --")] + [(v, v) for v in versions]
        else:
            self.fields["runtime_version"].choices = [("", "-- Select family first --")]

    @staticmethod
    def _get_versions_for_family(family_name):
        """Get all unique versions for a runtime family across all repositories."""
        runtimes = RuntimeFamily.objects.filter(name=family_name)
        versions = set()
        for rt in runtimes:
            for v in rt.versions:
                versions.add(str(v))
        return sorted(versions, reverse=True)

    def clean_name(self):
        name = self.cleaned_data["name"]
        if CIWorkflow.objects.filter(name=name).exists():
            raise forms.ValidationError("A workflow with this name already exists.")
        return name

    def clean_runtime_family(self):
        family = self.cleaned_data["runtime_family"]
        if not RuntimeFamily.objects.filter(name=family).exists():
            raise forms.ValidationError("Selected runtime family does not exist.")
        return family

    def clean_runtime_version(self):
        version = self.cleaned_data.get("runtime_version")
        family = self.cleaned_data.get("runtime_family")
        if family and version:
            versions = self._get_versions_for_family(family)
            if version not in versions:
                raise forms.ValidationError("Selected version is not available for this runtime family.")
        return version


class ProjectCIConfigForm(forms.Form):
    """Form for project-level CI configuration."""

    default_workflow = forms.ModelChoiceField(
        queryset=CIWorkflow.objects.none(),
        required=False,
        empty_label="-- No default --",
        widget=forms.Select(attrs={"class": DARK_SELECT}),
    )
    approve_all_published = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "rounded border-dark-border bg-dark-bg text-dark-accent focus:ring-dark-accent",
            }
        ),
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            from core.models import get_available_workflows_for_project

            self.fields["default_workflow"].queryset = get_available_workflows_for_project(project)


class ApproveWorkflowForm(forms.Form):
    """Form for adding a workflow to the project's approved list."""

    workflow = forms.ModelChoiceField(
        queryset=CIWorkflow.objects.none(),
        widget=forms.Select(attrs={"class": DARK_SELECT}),
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            already_approved_ids = ProjectApprovedWorkflow.objects.filter(project=project).values_list(
                "workflow_id", flat=True
            )
            self.fields["workflow"].queryset = CIWorkflow.objects.filter(status="published").exclude(
                id__in=already_approved_ids
            )
