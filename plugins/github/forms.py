"""GitHub plugin wizard forms."""
from django import forms


class GitHubAuthForm(forms.Form):
    """Step 1: GitHub authentication credentials."""
    AUTH_TYPE_CHOICES = [
        ('app', 'GitHub App (Recommended)'),
        ('token', 'Personal Access Token'),
    ]

    name = forms.CharField(
        max_length=63,
        label='Connection Name',
        help_text='Unique name for this connection (e.g., "github-prod")'
    )
    auth_type = forms.ChoiceField(
        choices=AUTH_TYPE_CHOICES,
        label='Authentication Type',
        initial='app',
        widget=forms.RadioSelect
    )
    # GitHub App fields
    app_id = forms.CharField(
        label='GitHub App ID',
        required=False,
        help_text='Your GitHub App ID from the app settings page'
    )
    private_key = forms.CharField(
        label='Private Key',
        required=False,
        widget=forms.Textarea(attrs={'rows': 8, 'class': 'font-mono text-xs'}),
        help_text='GitHub App private key in PEM format'
    )
    installation_id = forms.CharField(
        label='Installation ID',
        required=False,
        help_text='Installation ID from your GitHub App installation'
    )
    # PAT field
    personal_token = forms.CharField(
        label='Personal Access Token',
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text='Classic token or fine-grained token (ghp_ or github_pat_ prefix)'
    )
    # Common fields
    base_url = forms.URLField(
        label='GitHub Enterprise URL',
        required=False,
        help_text='Leave blank for github.com, or enter your GitHub Enterprise Server URL'
    )
    organization = forms.CharField(
        label='Organization',
        required=False,
        help_text='Organization name for creating repos (leave blank for personal repos)'
    )

    def clean(self):
        cleaned_data = super().clean()
        auth_type = cleaned_data.get('auth_type')

        if auth_type == 'app':
            if not cleaned_data.get('app_id'):
                self.add_error('app_id', 'Required for GitHub App authentication')
            if not cleaned_data.get('private_key'):
                self.add_error('private_key', 'Required for GitHub App authentication')
            if not cleaned_data.get('installation_id'):
                self.add_error('installation_id', 'Required for GitHub App authentication')
        elif auth_type == 'token':
            if not cleaned_data.get('personal_token'):
                self.add_error('personal_token', 'Required for PAT authentication')

        return cleaned_data


class GitHubWebhookForm(forms.Form):
    """Step 2: Webhook configuration."""
    webhook_secret = forms.CharField(
        label='Webhook Secret',
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text='Secret for webhook signature verification (recommended)'
    )


class GitHubConfirmForm(forms.Form):
    """Step 3: Confirmation step (no input fields)."""
    # Display-only step showing summary
    pass
