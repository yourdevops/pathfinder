"""GitHub plugin wizard forms."""
from django import forms


class GitHubAuthForm(forms.Form):
    """Step 1: GitHub App authentication credentials."""
    name = forms.CharField(
        max_length=63,
        label='Connection Name',
        help_text='Unique name for this connection (e.g., "github-prod")'
    )
    app_id = forms.CharField(
        label='GitHub App ID',
        help_text='Your GitHub App ID from the app settings page'
    )
    private_key = forms.CharField(
        label='Private Key',
        widget=forms.Textarea(attrs={'rows': 8, 'class': 'font-mono text-xs'}),
        help_text='GitHub App private key in PEM format'
    )
    installation_id = forms.CharField(
        label='Installation ID',
        help_text='Installation ID from your GitHub App installation'
    )
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
