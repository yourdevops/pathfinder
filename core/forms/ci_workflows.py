"""CI Workflows forms for repository registration and workflow creation."""

from django import forms

from core.models import (
    CIWorkflow,
    IntegrationConnection,
    ProjectApprovedWorkflow,
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
                "class": DARK_INPUT,
                "placeholder": "e.g., pathfinder-steps",
            }
        ),
    )
    git_url = forms.URLField(
        max_length=500,
        help_text="HTTPS URL of the Git repository containing CI step definitions.",
        widget=forms.URLInput(
            attrs={
                "class": DARK_INPUT,
                "placeholder": "https://github.com/org/ci-steps-repo",
            }
        ),
    )
    engine = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": DARK_SELECT}),
        help_text="CI engine for the steps in this repository.",
    )
    connection = forms.ModelChoiceField(
        queryset=IntegrationConnection.objects.filter(plugin_name="github", status="active"),
        required=False,
        empty_label="None (public repository)",
        help_text="Select a GitHub connection for private repositories.",
        widget=forms.Select(
            attrs={
                "class": DARK_SELECT,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from plugins.base import get_available_engines

        engine_choices = get_available_engines()
        if engine_choices:
            self.fields["engine"].choices = engine_choices  # type: ignore[attr-defined]
        else:
            self.fields["engine"].choices = [("", "No CI engines available")]  # type: ignore[attr-defined]

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
    """Form for creating a new CI workflow (name, description, engine, dev_workflow)."""

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
    engine = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": DARK_SELECT}),
    )
    dev_workflow = forms.ChoiceField(
        choices=CIWorkflow.DEV_WORKFLOW_CHOICES,
        initial="trunk_based",
        help_text="Development workflow pattern. More options coming soon.",
        widget=forms.Select(
            attrs={
                "class": DARK_SELECT,
                "disabled": "disabled",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Derive available engines from connected Steps Repositories
        repo_engines = list(StepsRepository.objects.values_list("engine", flat=True).distinct().order_by("engine"))

        from plugins.base import get_ci_plugin_for_engine

        engine_choices = []
        for eng in repo_engines:
            plugin = get_ci_plugin_for_engine(eng)
            label = plugin.engine_display_name if plugin else eng
            engine_choices.append((eng, label))

        if len(engine_choices) == 1:
            # Single engine: pre-select it, no placeholder
            self.fields["engine"].choices = engine_choices  # type: ignore[attr-defined]
            self.fields["engine"].initial = engine_choices[0][0]
        else:
            self.fields["engine"].choices = [("", "-- Select CI engine --"), *engine_choices]  # type: ignore[attr-defined]

    def clean_name(self):
        name = self.cleaned_data["name"]
        if CIWorkflow.objects.filter(name=name).exists():
            raise forms.ValidationError("A workflow with this name already exists.")
        return name


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

            self.fields["default_workflow"].queryset = get_available_workflows_for_project(project)  # type: ignore[attr-defined]


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
            self.fields["workflow"].queryset = CIWorkflow.objects.filter(status="published").exclude(  # type: ignore[attr-defined]
                id__in=already_approved_ids
            )
