"""GitHub plugin views."""
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from formtools.wizard.views import SessionWizardView
from core.models import IntegrationConnection
from core.permissions import OperatorRequiredMixin
from .forms import GitHubAuthForm, GitHubWebhookForm, GitHubConfirmForm
from .plugin import GitHubPlugin


WIZARD_FORMS = [
    ('auth', GitHubAuthForm),
    ('webhook', GitHubWebhookForm),
    ('confirm', GitHubConfirmForm),
]


class GitHubConnectionWizard(LoginRequiredMixin, OperatorRequiredMixin, SessionWizardView):
    """Multi-step wizard for GitHub connection creation."""
    form_list = WIZARD_FORMS
    template_name = 'github/wizard.html'

    def get_template_names(self):
        step_templates = {
            'auth': 'github/wizard_auth.html',
            'webhook': 'github/wizard_webhook.html',
            'confirm': 'github/wizard_confirm.html',
        }
        return [step_templates.get(self.steps.current, self.template_name)]

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['plugin'] = GitHubPlugin()

        if self.steps.current == 'confirm':
            auth_data = self.get_cleaned_data_for_step('auth')
            webhook_data = self.get_cleaned_data_for_step('webhook')
            context['auth_data'] = auth_data
            context['webhook_data'] = webhook_data
            # Mask sensitive data for display
            context['masked_private_key'] = '***' + auth_data.get('private_key', '')[-20:] if auth_data else ''

        return context

    def done(self, form_list, form_dict, **kwargs):
        auth_data = form_dict['auth'].cleaned_data
        webhook_data = form_dict['webhook'].cleaned_data

        # Build full config
        config = {
            'app_id': auth_data['app_id'],
            'private_key': auth_data['private_key'],
            'installation_id': auth_data['installation_id'],
            'webhook_secret': webhook_data.get('webhook_secret', ''),
        }
        if auth_data.get('base_url'):
            config['base_url'] = auth_data['base_url']
        if auth_data.get('organization'):
            config['organization'] = auth_data['organization']

        # Create connection
        connection = IntegrationConnection(
            name=auth_data['name'],
            plugin_name='github',
            description=f"GitHub App connection for {auth_data.get('organization') or 'personal'} repos",
            created_by=self.request.user.username,
        )
        connection.set_config(config)
        connection.save()

        messages.success(self.request, f'GitHub connection "{connection.name}" created successfully.')
        return redirect('connections:detail', uuid=connection.uuid)
