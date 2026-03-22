"""Template registration forms."""

from django import forms

from core.models import IntegrationConnection

DARK_INPUT = "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text placeholder-dark-muted focus:outline-none focus:border-dark-accent"
DARK_SELECT = "w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-dark-accent"


class TemplateRegisterForm(forms.Form):
    """Form for registering a new service template."""

    connection = forms.ModelChoiceField(
        queryset=IntegrationConnection.objects.none(),
        required=False,
        empty_label="None (public repo)",
        help_text="Select an SCM connection for private repositories.",
        widget=forms.Select(attrs={"class": DARK_SELECT}),
    )
    git_url = forms.URLField(
        max_length=500,
        help_text="HTTPS URL of the Git repository containing the service template.",
        widget=forms.URLInput(
            attrs={
                "class": DARK_INPUT,
                "placeholder": "https://github.com/org/template-repo",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from plugins.base import registry

        scm_names = [p.name for p in registry.all().values() if p.category == "scm"]
        self.fields["connection"].queryset = IntegrationConnection.objects.filter(  # type: ignore[attr-defined]
            status="active", plugin_name__in=scm_names
        )

    def clean_git_url(self):
        git_url = self.cleaned_data["git_url"]
        from core.models import Template

        if Template.objects.filter(git_url=git_url).exists():
            raise forms.ValidationError("A template with this URL is already registered.")
        return git_url
