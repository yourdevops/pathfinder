---
phase: quick-012
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - plugins/github/plugin.py
  - plugins/github/forms.py
  - plugins/github/views.py
  - plugins/github/urls.py
  - plugins/github/templates/github/repositories.html
  - plugins/github/templates/github/wizard_auth.html
autonomous: true

must_haves:
  truths:
    - "GitHub plugin can list repositories for a connection"
    - "Users can view repository list in connection detail page"
    - "PAT authentication works as alternative to GitHub App"
  artifacts:
    - path: "plugins/github/plugin.py"
      provides: "list_repositories and PAT auth methods"
      contains: "def list_repositories"
    - path: "plugins/github/views.py"
      provides: "Repository list view"
      contains: "class RepositoryListView"
    - path: "plugins/github/templates/github/repositories.html"
      provides: "Repository list UI"
  key_links:
    - from: "plugins/github/views.py"
      to: "plugins/github/plugin.py"
      via: "list_repositories method call"
---

<objective>
Add core missing GitHub plugin functionality: list repositories, PAT authentication, and repository list UI.

Purpose: Enable users to see their connected GitHub repositories and support both GitHub App and Personal Access Token authentication methods.
Output: Working repository listing via UI and dual authentication support.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docs/plugins/github.md
@plugins/github/plugin.py
@plugins/github/views.py
@plugins/github/forms.py
@plugins/github/urls.py
@plugins/base.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add list_repositories and PAT support to plugin.py</name>
  <files>plugins/github/plugin.py</files>
  <action>
  Add the following to GitHubPlugin class:

  1. Update capabilities to include 'list_repos' (already present, verify)

  2. Update get_config_schema to support PAT auth type:
     - Add 'auth_type' field: {'type': 'string', 'required': True, 'label': 'Authentication Type'} with choices 'app' or 'token'
     - Add 'personal_token' field: {'type': 'string', 'required': False, 'sensitive': True, 'label': 'Personal Access Token'}
     - Keep existing app_id, private_key, installation_id fields but mark as required=False (conditionally required based on auth_type)

  3. Add _get_github_client_pat method for PAT authentication:
     ```python
     def _get_github_client_pat(self, config: Dict[str, Any]) -> Github:
         """Get GitHub client using Personal Access Token."""
         token = config['personal_token']
         base_url = config.get('base_url')
         if base_url:
             return Github(auth=Auth.Token(token), base_url=base_url)
         return Github(auth=Auth.Token(token))
     ```

  4. Update _get_github_client to detect auth_type and route appropriately:
     - If config.get('auth_type') == 'token', call _get_github_client_pat
     - Otherwise, use existing GitHub App logic (default for backwards compat)

  5. Add list_repositories method:
     ```python
     def list_repositories(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
         """
         List all accessible repositories.

         Returns list of dicts with: name, full_name, description, html_url,
         clone_url, private, default_branch, language, updated_at
         """
         g = self._get_github_client(config)
         org_name = config.get('organization')

         if org_name:
             org = g.get_organization(org_name)
             repos = org.get_repos()
         else:
             # For PAT, list user's repos; for App, use installation repos
             if config.get('auth_type') == 'token':
                 repos = g.get_user().get_repos()
             else:
                 # Installation repos are already scoped
                 repos = g.get_user().get_repos()

         return [{
             'name': r.name,
             'full_name': r.full_name,
             'description': r.description or '',
             'html_url': r.html_url,
             'clone_url': r.clone_url,
             'private': r.private,
             'default_branch': r.default_branch,
             'language': r.language or 'Unknown',
             'updated_at': r.updated_at.isoformat() if r.updated_at else None,
         } for r in repos]
     ```

  6. Update health_check to use the unified _get_github_client method (no changes needed if routing works).
  </action>
  <verify>python -c "from plugins.github.plugin import GitHubPlugin; p = GitHubPlugin(); print(p.get_config_schema().keys())"</verify>
  <done>GitHubPlugin has list_repositories method and supports both auth_type='app' and auth_type='token'</done>
</task>

<task type="auto">
  <name>Task 2: Add RepositoryListView and URL route</name>
  <files>plugins/github/views.py, plugins/github/urls.py</files>
  <action>
  1. In plugins/github/views.py, add a new view:
     ```python
     from django.views.generic import TemplateView
     from core.models import IntegrationConnection

     class RepositoryListView(LoginRequiredMixin, OperatorRequiredMixin, TemplateView):
         """Display repositories for a GitHub connection."""
         template_name = 'github/repositories.html'

         def get_context_data(self, **kwargs):
             context = super().get_context_data(**kwargs)
             connection_uuid = self.kwargs.get('uuid')
             connection = IntegrationConnection.objects.get(uuid=connection_uuid)

             plugin = GitHubPlugin()
             config = connection.get_config()

             try:
                 repositories = plugin.list_repositories(config)
                 context['repositories'] = repositories
                 context['error'] = None
             except Exception as e:
                 context['repositories'] = []
                 context['error'] = str(e)

             context['connection'] = connection
             context['plugin'] = plugin
             return context
     ```

  2. In plugins/github/urls.py, add the route:
     ```python
     path('<uuid:uuid>/repositories/', views.RepositoryListView.as_view(), name='repositories'),
     ```
  </action>
  <verify>grep -n "RepositoryListView" plugins/github/views.py && grep -n "repositories" plugins/github/urls.py</verify>
  <done>RepositoryListView exists and is routed at /<uuid>/repositories/</done>
</task>

<task type="auto">
  <name>Task 3: Create repository list template</name>
  <files>plugins/github/templates/github/repositories.html</files>
  <action>
  Create plugins/github/templates/github/repositories.html:

  ```html
  {% extends "base.html" %}

  {% block title %}Repositories - {{ connection.name }}{% endblock %}

  {% block content %}
  <div class="p-8">
      <div class="mb-6">
          <a href="{% url 'connections:detail' uuid=connection.uuid %}" class="text-dark-accent hover:text-dark-accent-hover">
              &larr; Back to Connection
          </a>
      </div>

      <div class="flex items-center justify-between mb-6">
          <div>
              <h1 class="text-2xl font-bold">Repositories</h1>
              <p class="text-dark-muted">{{ connection.name }} - {{ repositories|length }} repositories</p>
          </div>
          <button onclick="location.reload()" class="btn-secondary">
              Refresh
          </button>
      </div>

      {% if error %}
      <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6">
          <p class="text-red-400">{{ error }}</p>
      </div>
      {% endif %}

      {% if repositories %}
      <div class="card">
          <table class="min-w-full">
              <thead>
                  <tr class="border-b border-dark-border">
                      <th class="text-left py-3 px-4 text-sm font-medium text-dark-muted">Repository</th>
                      <th class="text-left py-3 px-4 text-sm font-medium text-dark-muted">Language</th>
                      <th class="text-left py-3 px-4 text-sm font-medium text-dark-muted">Visibility</th>
                      <th class="text-left py-3 px-4 text-sm font-medium text-dark-muted">Default Branch</th>
                      <th class="text-left py-3 px-4 text-sm font-medium text-dark-muted">Updated</th>
                      <th class="text-right py-3 px-4 text-sm font-medium text-dark-muted">Actions</th>
                  </tr>
              </thead>
              <tbody class="divide-y divide-dark-border">
                  {% for repo in repositories %}
                  <tr class="hover:bg-dark-surface/50">
                      <td class="py-3 px-4">
                          <div>
                              <a href="{{ repo.html_url }}" target="_blank" class="font-medium text-dark-text hover:text-dark-accent">
                                  {{ repo.name }}
                              </a>
                              {% if repo.description %}
                              <p class="text-sm text-dark-muted truncate max-w-md">{{ repo.description }}</p>
                              {% endif %}
                          </div>
                      </td>
                      <td class="py-3 px-4">
                          <span class="text-sm text-dark-muted">{{ repo.language }}</span>
                      </td>
                      <td class="py-3 px-4">
                          {% if repo.private %}
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-400">
                              Private
                          </span>
                          {% else %}
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-400">
                              Public
                          </span>
                          {% endif %}
                      </td>
                      <td class="py-3 px-4">
                          <span class="text-sm text-dark-muted font-mono">{{ repo.default_branch }}</span>
                      </td>
                      <td class="py-3 px-4">
                          <span class="text-sm text-dark-muted">{{ repo.updated_at|slice:":10" }}</span>
                      </td>
                      <td class="py-3 px-4 text-right">
                          <a href="{{ repo.html_url }}" target="_blank" class="text-dark-accent hover:text-dark-accent-hover text-sm">
                              View on GitHub
                          </a>
                      </td>
                  </tr>
                  {% endfor %}
              </tbody>
          </table>
      </div>
      {% else %}
      <div class="card text-center py-12">
          <p class="text-dark-muted">No repositories found.</p>
      </div>
      {% endif %}
  </div>
  {% endblock %}
  ```
  </action>
  <verify>test -f plugins/github/templates/github/repositories.html && echo "Template exists"</verify>
  <done>Repository list template renders table of repos with name, language, visibility, branch, updated date</done>
</task>

<task type="auto">
  <name>Task 4: Add auth type selection to wizard forms</name>
  <files>plugins/github/forms.py, plugins/github/templates/github/wizard_auth.html</files>
  <action>
  1. Update plugins/github/forms.py GitHubAuthForm to support auth type selection:
     ```python
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
             help_text='Leave blank for github.com'
         )
         organization = forms.CharField(
             label='Organization',
             required=False,
             help_text='Organization name (leave blank for personal repos)'
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
     ```

  2. Update wizard_auth.html to show/hide fields based on auth_type selection using Alpine.js or simple JS toggle. Add x-data for Alpine.js toggle of field visibility based on auth_type radio selection.
  </action>
  <verify>python -c "from plugins.github.forms import GitHubAuthForm; f = GitHubAuthForm(); print('auth_type' in f.fields)"</verify>
  <done>GitHubAuthForm has auth_type field with conditional validation for app vs token fields</done>
</task>

<task type="auto">
  <name>Task 5: Update wizard view to handle both auth types</name>
  <files>plugins/github/views.py</files>
  <action>
  Update GitHubConnectionWizard.done() method to handle both auth types:

  ```python
  def done(self, form_list, form_dict, **kwargs):
      auth_data = form_dict['auth'].cleaned_data
      webhook_data = form_dict['webhook'].cleaned_data

      auth_type = auth_data['auth_type']

      # Build config based on auth type
      config = {
          'auth_type': auth_type,
      }

      if auth_type == 'app':
          config.update({
              'app_id': auth_data['app_id'],
              'private_key': auth_data['private_key'],
              'installation_id': auth_data['installation_id'],
              'webhook_secret': webhook_data.get('webhook_secret', ''),
          })
      else:  # token
          config['personal_token'] = auth_data['personal_token']

      # Common optional fields
      if auth_data.get('base_url'):
          config['base_url'] = auth_data['base_url']
      if auth_data.get('organization'):
          config['organization'] = auth_data['organization']

      # Create connection
      org_or_user = auth_data.get('organization') or 'personal'
      connection = IntegrationConnection(
          name=auth_data['name'],
          plugin_name='github',
          description=f"GitHub {'App' if auth_type == 'app' else 'PAT'} connection for {org_or_user} repos",
          created_by=self.request.user.username,
      )
      connection.set_config(config)
      connection.save()

      messages.success(self.request, f'GitHub connection "{connection.name}" created successfully.')
      return redirect('connections:detail', uuid=connection.uuid)
  ```
  </action>
  <verify>grep -n "auth_type" plugins/github/views.py</verify>
  <done>Wizard correctly builds config for both GitHub App and PAT auth types</done>
</task>

<task type="auto">
  <name>Task 6: Update wizard auth template with conditional fields</name>
  <files>plugins/github/templates/github/wizard_auth.html</files>
  <action>
  Update wizard_auth.html to use Alpine.js for conditional field visibility:

  1. Add x-data to the form with authType state
  2. Add radio buttons for auth type selection
  3. Wrap GitHub App fields in x-show="authType === 'app'"
  4. Wrap PAT field in x-show="authType === 'token'"

  The template should include:
  - Auth type radio group at the top (after connection name)
  - Conditional sections that show/hide based on selection
  - Proper field names matching form.field.html_name pattern
  </action>
  <verify>grep -n "x-data\|x-show\|authType" plugins/github/templates/github/wizard_auth.html | head -5</verify>
  <done>Auth template shows/hides appropriate fields based on auth type selection</done>
</task>

</tasks>

<verification>
1. Create GitHub connection with PAT: Navigate to /integrations/github/create/, select PAT auth type, enter token
2. Create GitHub connection with App: Select App auth type, enter app_id, private_key, installation_id
3. View repositories: Navigate to /integrations/github/<uuid>/repositories/ and see repo list
4. Health check works for both auth types
</verification>

<success_criteria>
- GitHubPlugin.list_repositories() returns list of repository dicts
- PAT authentication creates valid GitHub client
- Repository list view displays repos in table format
- Wizard form shows correct fields based on auth type selection
- Both auth types successfully create working connections
</success_criteria>

<output>
After completion, create `.planning/quick/012-add-missing-github-plugin-functionality/012-SUMMARY.md`
</output>
