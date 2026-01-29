"""CI Workflows forms for repository registration."""
from django import forms

from core.models import StepsRepository, IntegrationConnection
from core.validators import dns_label_validator


class StepsRepoRegisterForm(forms.Form):
    """Form for registering a new CI steps repository."""

    name = forms.CharField(
        max_length=63,
        validators=[dns_label_validator],
        help_text='DNS-compatible name: lowercase letters, numbers, hyphens. Max 63 chars.',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text placeholder-dark-muted focus:outline-none focus:border-dark-accent',
            'placeholder': 'e.g., pathfinder-steps',
        }),
    )
    git_url = forms.URLField(
        max_length=500,
        help_text='HTTPS URL of the Git repository containing CI step definitions.',
        widget=forms.URLInput(attrs={
            'class': 'w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text placeholder-dark-muted focus:outline-none focus:border-dark-accent',
            'placeholder': 'https://github.com/org/ci-steps-repo',
        }),
    )
    connection = forms.ModelChoiceField(
        queryset=IntegrationConnection.objects.filter(
            plugin_name='github', status='active'
        ),
        required=False,
        empty_label='None (public repository)',
        help_text='Select a GitHub connection for private repositories.',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 bg-dark-surface border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-dark-accent',
        }),
    )

    def clean_name(self):
        name = self.cleaned_data['name']
        if StepsRepository.objects.filter(name=name).exists():
            raise forms.ValidationError('A repository with this name already exists.')
        return name

    def clean_git_url(self):
        git_url = self.cleaned_data['git_url']
        if StepsRepository.objects.filter(git_url=git_url).exists():
            raise forms.ValidationError('A repository with this URL is already registered.')
        return git_url
