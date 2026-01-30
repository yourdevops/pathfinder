"""GitHub plugin forms."""

from django import forms
from core.models import IntegrationConnection


class GitHubConnectionForm(forms.Form):
    """Single form for GitHub connection creation."""

    AUTH_TYPE_CHOICES = [
        ("app", "GitHub App (Recommended)"),
        ("token", "Personal Access Token"),
    ]
    SETUP_MODE_CHOICES = [
        ("automatic", "Automatic (via GitHub)"),
        ("manual", "Manual Entry"),
    ]

    # Connection name - auto-generated but editable
    name = forms.CharField(
        max_length=63,
        label="Connection Name",
        help_text="Unique identifier for this connection",
    )

    # Auth type selection
    auth_type = forms.ChoiceField(
        choices=AUTH_TYPE_CHOICES,
        label="Authentication Method",
        initial="app",
        widget=forms.RadioSelect,
    )

    # GitHub App setup mode (only shown when auth_type='app')
    setup_mode = forms.ChoiceField(
        choices=SETUP_MODE_CHOICES,
        label="Setup Method",
        initial="automatic",
        required=False,
        widget=forms.RadioSelect,
    )

    # Automatic setup fields (GitHub App via manifest)
    organization = forms.CharField(
        label="Organization Name",
        required=False,
        help_text="The GitHub organization to connect. You must have Owner or Admin permissions.",
    )
    app_name = forms.CharField(
        label="GitHub App Name",
        required=False,
        help_text="Name for the GitHub App (auto-generated, can be customized)",
    )

    # Manual GitHub App fields
    app_id = forms.CharField(
        label="GitHub App ID",
        required=False,
        help_text="Your GitHub App ID from the app settings page",
    )
    private_key = forms.CharField(
        label="Private Key",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "class": "font-mono text-xs"}),
        help_text="GitHub App private key in PEM format",
    )
    installation_id = forms.CharField(
        label="Installation ID",
        required=False,
        help_text="Installation ID from your GitHub App installation",
    )

    # PAT field
    personal_token = forms.CharField(
        label="Personal Access Token",
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text="Classic token (ghp_) or fine-grained token (github_pat_)",
    )

    # Common optional fields
    base_url = forms.URLField(
        label="GitHub Enterprise URL",
        required=False,
        help_text="Leave blank for github.com, or enter your GitHub Enterprise Server URL",
    )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").lower().strip()
        # DNS-compatible validation
        import re

        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
            raise forms.ValidationError(
                "Name must be DNS-compatible: lowercase letters, numbers, and hyphens. "
                "Must start and end with a letter or number."
            )
        if IntegrationConnection.objects.filter(name=name).exists():
            raise forms.ValidationError("A connection with this name already exists.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        auth_type = cleaned_data.get("auth_type")
        setup_mode = cleaned_data.get("setup_mode")

        if auth_type == "app":
            if setup_mode == "manual":
                # Manual GitHub App requires all credentials
                if not cleaned_data.get("app_id"):
                    self.add_error("app_id", "Required for manual GitHub App setup")
                if not cleaned_data.get("private_key"):
                    self.add_error(
                        "private_key", "Required for manual GitHub App setup"
                    )
                if not cleaned_data.get("installation_id"):
                    self.add_error(
                        "installation_id", "Required for manual GitHub App setup"
                    )
            else:  # automatic
                # Automatic setup requires organization
                if not cleaned_data.get("organization"):
                    self.add_error(
                        "organization", "Required for automatic GitHub App setup"
                    )

        elif auth_type == "token":
            if not cleaned_data.get("personal_token"):
                self.add_error("personal_token", "Required for PAT authentication")

        return cleaned_data


class GitHubManifestSetupForm(forms.Form):
    """Form for initiating GitHub App manifest flow."""

    name = forms.CharField(
        max_length=63,
        label="Connection Name",
        help_text="Unique identifier for this connection",
    )
    organization = forms.CharField(
        label="Organization Name",
        help_text="The GitHub organization to connect. You must have Owner or Admin permissions.",
    )
    app_name = forms.CharField(
        label="GitHub App Name",
        help_text="Name for the GitHub App that will be created",
    )
    base_url = forms.URLField(
        label="GitHub Enterprise URL",
        required=False,
        help_text="Leave blank for github.com",
    )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").lower().strip()
        import re

        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
            raise forms.ValidationError(
                "Name must be DNS-compatible: lowercase letters, numbers, and hyphens."
            )
        if IntegrationConnection.objects.filter(name=name).exists():
            raise forms.ValidationError("A connection with this name already exists.")
        return name
