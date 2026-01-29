# Phase 3: Integrations - Research

**Researched:** 2026-01-23
**Domain:** Plugin architecture, encrypted credentials, GitHub API, Docker SDK, background health checks
**Confidence:** HIGH

## Summary

This research covers the technical foundation for implementing Phase 3: Integrations, which enables platform engineers to register GitHub and Docker connections with health monitoring. The phase introduces a plugin architecture for connection types, Fernet encryption for sensitive credentials, and periodic background health checks.

The standard approach uses Django's `autodiscover_modules()` for plugin discovery from a `plugins/` directory, the `cryptography` library's Fernet encryption for sensitive fields stored in JSONField, PyGithub for GitHub App authentication and repository operations, Docker SDK for Python (`docker-py`) for container management, and Django 6.0's built-in Tasks framework with `django-tasks` DatabaseBackend for periodic health checks.

Key decisions from CONTEXT.md are locked: plugins isolated from core, auto-discovery from `plugins/` directory, step wizard for GitHub registration, status pill indicators (healthy/unhealthy/unknown), sensitive fields hidden after save with "empty = keep" edit pattern, periodic checks spread evenly across configurable interval.

**Primary recommendation:** Implement plugin system using `autodiscover_modules()` in an AppConfig's `ready()` method, store credentials in encrypted JSONField using Fernet with key from environment variable or auto-generated file, use Django 6.0 Tasks with `django-tasks` DatabaseBackend for scheduled health checks.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 6.0.1 | Web framework, ORM, Tasks | Already installed, has built-in Tasks framework |
| cryptography | 44.0+ | Fernet encryption | Gold standard for Python symmetric encryption |
| PyGithub | 2.5+ | GitHub API v3 client | Official typed Python SDK, supports GitHub Apps |
| docker | 7.1+ | Docker Engine API | Official Docker SDK for Python |
| django-tasks | 0.4+ | Background task execution | Reference implementation with DatabaseBackend |
| django-formtools | 2.5+ | Multi-step form wizard | Official Django form wizard package |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyJWT | 2.9+ | JWT for GitHub App auth | Already a dependency of PyGithub |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| django-tasks DatabaseBackend | Celery + Redis | Celery requires external broker; DB backend is simpler |
| Fernet (cryptography) | django-fernet-fields | Custom encryption gives more control over JSONField |
| Custom plugin system | django-plugin-system | Standard autodiscover is simpler, well-documented |
| PyGithub | ghapi | PyGithub has better GitHub App support, typed |

**Installation:**
```bash
pip install cryptography PyGithub docker django-tasks django-formtools
```

## Architecture Patterns

### Recommended Project Structure
```
pathfinder/
├── plugins/                    # Plugin packages (outside core app)
│   ├── __init__.py            # Plugin registry
│   ├── base.py                # Base plugin classes
│   ├── github/                # GitHub plugin
│   │   ├── __init__.py        # Plugin registration
│   │   ├── plugin.py          # GitHubPlugin class
│   │   ├── forms.py           # Registration wizard forms
│   │   ├── urls.py            # Plugin-specific URLs
│   │   └── templates/
│   │       └── github/
│   │           ├── wizard_step1.html
│   │           ├── wizard_step2.html
│   │           └── connection_detail.html
│   └── docker/                # Docker plugin
│       ├── __init__.py
│       ├── plugin.py
│       ├── forms.py
│       └── templates/
core/
├── models.py                  # Add IntegrationConnection model
├── views/
│   └── integrations.py        # Connection list, plugin dispatch
├── tasks.py                   # Health check tasks
└── encryption.py              # Fernet encryption utilities
```

### Pattern 1: Plugin Base Class and Registry
**What:** Abstract base class defining plugin interface with auto-discovery
**When to use:** All plugin implementations must inherit from this
**Example:**
```python
# Source: Django autodiscover_modules pattern + docs/integrations.md
# plugins/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from django import forms

class PluginRegistry:
    """Singleton registry for discovered plugins."""
    _plugins: Dict[str, 'BasePlugin'] = {}

    @classmethod
    def register(cls, plugin: 'BasePlugin'):
        cls._plugins[plugin.name] = plugin

    @classmethod
    def get(cls, name: str) -> Optional['BasePlugin']:
        return cls._plugins.get(name)

    @classmethod
    def all(cls) -> Dict[str, 'BasePlugin']:
        return cls._plugins.copy()

    @classmethod
    def by_category(cls, category: str) -> Dict[str, 'BasePlugin']:
        return {k: v for k, v in cls._plugins.items() if v.category == category}

registry = PluginRegistry()

class BasePlugin(ABC):
    """Base class for all integration plugins."""
    name: str  # Unique identifier (e.g., 'github', 'docker')
    display_name: str  # Human-readable name
    category: str  # 'scm', 'ci', 'artifact', 'deploy'
    capabilities: List[str]  # ['create_repo', 'create_branch', 'commit', ...]
    icon: str  # Icon class or path

    # Sensitive field patterns - fields matching these are encrypted
    sensitive_field_patterns = [
        'password', 'token', 'secret', 'private_key',
        'api_key', 'client_secret', 'access_key', 'secret_key'
    ]

    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for plugin configuration."""
        pass

    @abstractmethod
    def get_wizard_forms(self) -> List[forms.Form]:
        """Return list of form classes for registration wizard."""
        pass

    @abstractmethod
    def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check connection health.
        Returns: {'status': 'healthy'|'unhealthy'|'unknown', 'message': str, 'details': dict}
        """
        pass

    @abstractmethod
    def get_urlpatterns(self):
        """Return URL patterns for plugin-specific views."""
        pass

    def is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field should be encrypted."""
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in self.sensitive_field_patterns)
```

### Pattern 2: Plugin Auto-Discovery
**What:** Discover plugins at Django startup using autodiscover_modules
**When to use:** Load plugins from plugins/ directory into registry
**Example:**
```python
# Source: Django autodiscover_modules documentation
# plugins/__init__.py
from django.utils.module_loading import autodiscover_modules

def autodiscover():
    """Discover and register all plugins."""
    autodiscover_modules('plugin', register_to=None)

# In AppConfig (e.g., plugins app or core app)
# plugins/apps.py or core/apps.py
from django.apps import AppConfig

class PluginsConfig(AppConfig):
    name = 'plugins'

    def ready(self):
        # Import plugin modules - each registers itself
        from plugins import autodiscover
        autodiscover()

# Alternative: Explicit discovery from settings
# plugins/__init__.py
import importlib
from django.conf import settings

def discover_plugins():
    """Load plugins listed in settings or scan plugins directory."""
    from plugins.base import registry

    # Discover from plugins package
    import pkgutil
    import plugins

    for importer, modname, ispkg in pkgutil.iter_modules(plugins.__path__):
        if ispkg:  # Each plugin is a package
            try:
                module = importlib.import_module(f'plugins.{modname}')
                # Plugin registers itself in its __init__.py
            except ImportError as e:
                import logging
                logging.warning(f"Failed to load plugin {modname}: {e}")
```

### Pattern 3: IntegrationConnection Model
**What:** Database model for configured connection instances
**When to use:** Store connection configuration with encrypted sensitive fields
**Example:**
```python
# Source: docs/integrations.md connection model
# core/models.py
import uuid
from django.db import models
from django.conf import settings
from core.encryption import encrypt_config, decrypt_config

class IntegrationConnection(models.Model):
    """Configured instance of a plugin."""
    HEALTH_STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('unhealthy', 'Unhealthy'),
        ('unknown', 'Unknown'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('disabled', 'Disabled'),
        ('error', 'Error'),
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=63, unique=True)  # DNS-compatible
    description = models.TextField(blank=True)
    plugin_name = models.CharField(max_length=63)  # References plugin

    # Configuration (sensitive fields encrypted)
    config = models.JSONField(default=dict)  # Non-sensitive config
    config_encrypted = models.BinaryField(null=True, blank=True)  # Encrypted sensitive fields

    enabled_capabilities = models.JSONField(default=list)  # Subset of plugin capabilities
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_production = models.BooleanField(default=False)

    # Health monitoring
    health_status = models.CharField(max_length=20, choices=HEALTH_STATUS_CHOICES, default='unknown')
    last_health_check = models.DateTimeField(null=True, blank=True)
    last_health_message = models.TextField(blank=True)

    # Webhook token for CI callbacks
    webhook_token = models.CharField(max_length=64, blank=True)

    # Audit fields
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_integration_connection'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.plugin_name})"

    def set_config(self, full_config: dict):
        """Separate and store config, encrypting sensitive fields."""
        from plugins.base import registry
        plugin = registry.get(self.plugin_name)
        if not plugin:
            raise ValueError(f"Unknown plugin: {self.plugin_name}")

        sensitive = {}
        non_sensitive = {}

        for key, value in full_config.items():
            if plugin.is_sensitive_field(key):
                sensitive[key] = value
            else:
                non_sensitive[key] = value

        self.config = non_sensitive
        if sensitive:
            self.config_encrypted = encrypt_config(sensitive)
        else:
            self.config_encrypted = None

    def get_config(self) -> dict:
        """Return merged config with decrypted sensitive fields."""
        result = dict(self.config)
        if self.config_encrypted:
            decrypted = decrypt_config(self.config_encrypted)
            result.update(decrypted)
        return result

    def get_plugin(self):
        """Return the plugin instance for this connection."""
        from plugins.base import registry
        return registry.get(self.plugin_name)

    @property
    def plugin_missing(self) -> bool:
        """Check if plugin is no longer available."""
        return self.get_plugin() is None
```

### Pattern 4: Fernet Encryption for Sensitive Fields
**What:** Symmetric encryption for API keys, tokens, private keys
**When to use:** All sensitive configuration fields
**Example:**
```python
# Source: cryptography.io Fernet documentation
# core/encryption.py
import os
import json
import base64
from pathlib import Path
from django.conf import settings
from cryptography.fernet import Fernet, MultiFernet

def get_encryption_key() -> bytes:
    """
    Get encryption key from environment or file.
    Priority: PTF_ENCRYPTION_KEY env var > secrets/encryption.key file
    Auto-generates key file if neither exists.
    """
    # Check environment variable first
    env_key = os.environ.get('PTF_ENCRYPTION_KEY')
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    # Check/create key file
    key_file = Path(settings.BASE_DIR) / 'secrets' / 'encryption.key'

    if key_file.exists():
        return key_file.read_bytes().strip()

    # Generate new key
    key = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(key)
    # Set restrictive permissions
    key_file.chmod(0o600)

    return key

def get_fernet() -> Fernet:
    """Get Fernet instance with current key."""
    key = get_encryption_key()
    return Fernet(key)

def encrypt_config(config: dict) -> bytes:
    """Encrypt a config dictionary."""
    f = get_fernet()
    json_bytes = json.dumps(config).encode('utf-8')
    return f.encrypt(json_bytes)

def decrypt_config(encrypted: bytes) -> dict:
    """Decrypt a config dictionary."""
    f = get_fernet()
    json_bytes = f.decrypt(encrypted)
    return json.loads(json_bytes.decode('utf-8'))

# For key rotation (future use)
def get_multi_fernet(keys: list[bytes]) -> MultiFernet:
    """
    Get MultiFernet for key rotation.
    First key encrypts new data; all keys can decrypt.
    """
    fernets = [Fernet(key) for key in keys]
    return MultiFernet(fernets)
```

### Pattern 5: GitHub Plugin with App Authentication
**What:** GitHub plugin using GitHub App credentials
**When to use:** SCM connection for repository operations
**Example:**
```python
# Source: PyGithub documentation, GitHub App authentication
# plugins/github/plugin.py
from typing import Dict, Any, List
from django import forms
from github import Github, GithubIntegration, Auth
from plugins.base import BasePlugin, registry

class GitHubPlugin(BasePlugin):
    name = 'github'
    display_name = 'GitHub'
    category = 'scm'
    capabilities = [
        'list_repos', 'create_repo', 'create_branch',
        'commit', 'push', 'webhooks'
    ]
    icon = 'github'

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'app_id': {'type': 'string', 'required': True},
            'private_key': {'type': 'string', 'required': True, 'sensitive': True},
            'installation_id': {'type': 'string', 'required': True},
            'webhook_secret': {'type': 'string', 'required': False, 'sensitive': True},
            'base_url': {'type': 'string', 'required': False},  # For GitHub Enterprise
        }

    def get_wizard_forms(self) -> List[forms.Form]:
        from .forms import GitHubAuthForm, GitHubWebhookForm, GitHubConfirmForm
        return [GitHubAuthForm, GitHubWebhookForm, GitHubConfirmForm]

    def _get_github_client(self, config: Dict[str, Any]) -> Github:
        """Get authenticated GitHub client for installation."""
        app_id = int(config['app_id'])
        private_key = config['private_key']
        installation_id = int(config['installation_id'])
        base_url = config.get('base_url')

        # Create App authentication
        auth = Auth.AppAuth(app_id, private_key)

        # Get installation authentication
        if base_url:
            gi = GithubIntegration(auth=auth, base_url=base_url)
        else:
            gi = GithubIntegration(auth=auth)

        # Get installation access
        installation_auth = auth.get_installation_auth(installation_id)

        if base_url:
            return Github(auth=installation_auth, base_url=base_url)
        return Github(auth=installation_auth)

    def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check GitHub connection health."""
        try:
            g = self._get_github_client(config)
            # Simple API call to verify authentication
            user = g.get_user()
            rate = g.get_rate_limit()

            return {
                'status': 'healthy',
                'message': f'Connected as {user.login}',
                'details': {
                    'rate_limit_remaining': rate.core.remaining,
                    'rate_limit_reset': rate.core.reset.isoformat(),
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': str(e),
                'details': {}
            }

    def create_repository(self, config: Dict[str, Any], name: str, **kwargs) -> Dict[str, Any]:
        """Create a new repository."""
        g = self._get_github_client(config)
        org_name = config.get('organization')

        if org_name:
            org = g.get_organization(org_name)
            repo = org.create_repo(name, **kwargs)
        else:
            user = g.get_user()
            repo = user.create_repo(name, **kwargs)

        return {
            'name': repo.name,
            'full_name': repo.full_name,
            'clone_url': repo.clone_url,
            'html_url': repo.html_url,
        }

    def create_branch(self, config: Dict[str, Any], repo_name: str,
                      branch_name: str, source_branch: str = 'main') -> Dict[str, Any]:
        """Create a new branch from source."""
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)

        # Get source branch SHA
        source = repo.get_branch(source_branch)
        sha = source.commit.sha

        # Create new branch ref
        ref = repo.create_git_ref(f'refs/heads/{branch_name}', sha)

        return {
            'ref': ref.ref,
            'sha': ref.object.sha,
        }

    def create_file(self, config: Dict[str, Any], repo_name: str, path: str,
                    content: str, message: str, branch: str = 'main') -> Dict[str, Any]:
        """Create or update a file in the repository."""
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)

        result = repo.create_file(path, message, content, branch=branch)

        return {
            'path': result['content'].path,
            'sha': result['content'].sha,
            'commit_sha': result['commit'].sha,
        }

    def get_urlpatterns(self):
        from . import urls
        return urls.urlpatterns

# Register plugin
registry.register(GitHubPlugin())
```

### Pattern 6: Docker Plugin
**What:** Docker plugin for container deployment via socket
**When to use:** Deploy target connection for container workloads
**Example:**
```python
# Source: Docker SDK for Python documentation
# plugins/docker/plugin.py
from typing import Dict, Any, List
from django import forms
import docker
from docker.errors import DockerException
from plugins.base import BasePlugin, registry

class DockerPlugin(BasePlugin):
    name = 'docker'
    display_name = 'Docker'
    category = 'deploy'
    capabilities = ['deploy', 'get_status', 'stop', 'logs']
    icon = 'docker'

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            'socket_path': {
                'type': 'string',
                'required': True,
                'default': '/var/run/docker.sock'
            },
            'tls_enabled': {'type': 'boolean', 'required': False, 'default': False},
            'tls_ca_cert': {'type': 'string', 'required': False, 'sensitive': True},
            'tls_client_cert': {'type': 'string', 'required': False, 'sensitive': True},
            'tls_client_key': {'type': 'string', 'required': False, 'sensitive': True},
        }

    def get_wizard_forms(self) -> List[forms.Form]:
        from .forms import DockerConnectionForm
        return [DockerConnectionForm]  # Single-page form for Docker

    def _get_docker_client(self, config: Dict[str, Any]) -> docker.DockerClient:
        """Get Docker client from config."""
        socket_path = config.get('socket_path', '/var/run/docker.sock')

        # Check if socket path or TCP URL
        if socket_path.startswith(('tcp://', 'https://')):
            base_url = socket_path
        else:
            base_url = f'unix://{socket_path}'

        # TLS configuration
        tls_config = None
        if config.get('tls_enabled'):
            tls_config = docker.tls.TLSConfig(
                ca_cert=config.get('tls_ca_cert'),
                client_cert=(config.get('tls_client_cert'), config.get('tls_client_key')),
                verify=True
            )

        return docker.DockerClient(base_url=base_url, tls=tls_config)

    def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check Docker daemon connectivity."""
        try:
            client = self._get_docker_client(config)
            # Ping the daemon
            client.ping()

            # Get version info
            version = client.version()
            info = client.info()

            return {
                'status': 'healthy',
                'message': f'Docker {version.get("Version", "unknown")}',
                'details': {
                    'version': version.get('Version'),
                    'api_version': version.get('ApiVersion'),
                    'os': version.get('Os'),
                    'arch': version.get('Arch'),
                    'containers_running': info.get('ContainersRunning', 0),
                    'containers_total': info.get('Containers', 0),
                }
            }
        except DockerException as e:
            return {
                'status': 'unhealthy',
                'message': str(e),
                'details': {}
            }
        except Exception as e:
            return {
                'status': 'unknown',
                'message': f'Unexpected error: {e}',
                'details': {}
            }

    def run_container(self, config: Dict[str, Any], image: str,
                      name: str = None, **kwargs) -> Dict[str, Any]:
        """Run a container."""
        client = self._get_docker_client(config)
        container = client.containers.run(
            image,
            name=name,
            detach=True,
            **kwargs
        )
        return {
            'id': container.id,
            'short_id': container.short_id,
            'name': container.name,
            'status': container.status,
        }

    def get_container_status(self, config: Dict[str, Any],
                             container_id: str) -> Dict[str, Any]:
        """Get container status."""
        client = self._get_docker_client(config)
        try:
            container = client.containers.get(container_id)
            container.reload()  # Refresh attributes
            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'health': container.attrs.get('State', {}).get('Health', {}).get('Status', 'none'),
            }
        except docker.errors.NotFound:
            return {
                'id': container_id,
                'status': 'not_found',
                'error': 'Container not found'
            }

    def stop_container(self, config: Dict[str, Any],
                       container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """Stop a container."""
        client = self._get_docker_client(config)
        container = client.containers.get(container_id)
        container.stop(timeout=timeout)
        return {'status': 'stopped', 'id': container_id}

    def get_urlpatterns(self):
        from . import urls
        return urls.urlpatterns

# Register plugin
registry.register(DockerPlugin())
```

### Pattern 7: Periodic Health Checks with Django Tasks
**What:** Background task for periodic connection health checks
**When to use:** Spread health checks across configurable interval
**Example:**
```python
# Source: Django 6.0 Tasks documentation, django-tasks
# core/tasks.py
from django.tasks import task
from django.utils import timezone
from datetime import timedelta

@task(queue_name='health_checks')
def check_connection_health(connection_id: int):
    """
    Check health of a single connection.
    Called by scheduler, also available for manual "Check Now".
    """
    from core.models import IntegrationConnection

    try:
        connection = IntegrationConnection.objects.get(id=connection_id)
    except IntegrationConnection.DoesNotExist:
        return {'error': 'Connection not found'}

    plugin = connection.get_plugin()
    if not plugin:
        connection.health_status = 'unknown'
        connection.last_health_message = 'Plugin not available'
        connection.last_health_check = timezone.now()
        connection.save(update_fields=['health_status', 'last_health_message', 'last_health_check'])
        return {'status': 'unknown', 'error': 'Plugin missing'}

    # Run health check
    config = connection.get_config()
    result = plugin.health_check(config)

    # Update connection
    connection.health_status = result['status']
    connection.last_health_message = result.get('message', '')
    connection.last_health_check = timezone.now()
    connection.save(update_fields=['health_status', 'last_health_message', 'last_health_check'])

    return result

@task(queue_name='health_checks')
def schedule_health_checks():
    """
    Schedule health checks for all active connections.
    Spreads checks evenly across the interval to avoid load spikes.
    Called periodically by db_worker with --repeat.
    """
    from core.models import IntegrationConnection
    from django.conf import settings

    # Get interval from settings (default 15 minutes)
    interval_seconds = getattr(settings, 'HEALTH_CHECK_INTERVAL', 900)

    connections = IntegrationConnection.objects.filter(status='active')
    count = connections.count()

    if count == 0:
        return {'scheduled': 0}

    # Calculate delay between each check to spread evenly
    delay_between = interval_seconds / count

    scheduled = 0
    for i, connection in enumerate(connections):
        # Calculate when this check should run
        run_after = timezone.now() + timedelta(seconds=i * delay_between)
        check_connection_health.using(run_after=run_after).enqueue(connection_id=connection.id)
        scheduled += 1

    return {'scheduled': scheduled, 'interval': interval_seconds}
```

### Pattern 8: Multi-Step Form Wizard for GitHub
**What:** Step wizard using django-formtools for complex registration
**When to use:** GitHub connection with Auth -> Webhook -> Confirm steps
**Example:**
```python
# Source: django-formtools documentation
# plugins/github/forms.py
from django import forms

class GitHubAuthForm(forms.Form):
    """Step 1: GitHub App authentication."""
    app_id = forms.CharField(
        label='App ID',
        help_text='Your GitHub App ID'
    )
    private_key = forms.CharField(
        label='Private Key',
        widget=forms.Textarea(attrs={'rows': 10}),
        help_text='GitHub App private key (PEM format)'
    )
    installation_id = forms.CharField(
        label='Installation ID',
        help_text='Installation ID for your GitHub App'
    )
    base_url = forms.URLField(
        label='GitHub Enterprise URL',
        required=False,
        help_text='Leave blank for github.com'
    )

class GitHubWebhookForm(forms.Form):
    """Step 2: Webhook configuration."""
    webhook_secret = forms.CharField(
        label='Webhook Secret',
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text='Secret for webhook signature verification'
    )

class GitHubConfirmForm(forms.Form):
    """Step 3: Confirmation (read-only summary)."""
    # No fields - just displays summary from previous steps
    pass

# plugins/github/views.py
from django.shortcuts import redirect
from django.urls import reverse
from formtools.wizard.views import SessionWizardView
from core.models import IntegrationConnection
from .forms import GitHubAuthForm, GitHubWebhookForm, GitHubConfirmForm

class GitHubConnectionWizard(SessionWizardView):
    """Multi-step wizard for GitHub connection registration."""
    form_list = [
        ('auth', GitHubAuthForm),
        ('webhook', GitHubWebhookForm),
        ('confirm', GitHubConfirmForm),
    ]
    template_name = 'github/wizard.html'

    def get_template_names(self):
        """Return step-specific template."""
        return [f'github/wizard_step{self.steps.current}.html']

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        # Add previous step data for confirmation step
        if self.steps.current == 'confirm':
            context['auth_data'] = self.get_cleaned_data_for_step('auth')
            context['webhook_data'] = self.get_cleaned_data_for_step('webhook')
        return context

    def done(self, form_list, form_dict, **kwargs):
        """Create the connection after all steps complete."""
        auth_data = form_dict['auth'].cleaned_data
        webhook_data = form_dict['webhook'].cleaned_data

        # Merge all config
        config = {
            'app_id': auth_data['app_id'],
            'private_key': auth_data['private_key'],
            'installation_id': auth_data['installation_id'],
            'webhook_secret': webhook_data.get('webhook_secret', ''),
        }
        if auth_data.get('base_url'):
            config['base_url'] = auth_data['base_url']

        # Create connection
        connection = IntegrationConnection(
            name=self.request.POST.get('connection_name', f'github-{auth_data["app_id"]}'),
            plugin_name='github',
            created_by=self.request.user.username,
        )
        connection.set_config(config)
        connection.save()

        return redirect('connections:detail', uuid=connection.uuid)
```

### Pattern 9: Project/Environment Connection Attachments
**What:** M2M relationships for attaching connections to projects/environments
**When to use:** PROJ-05 and ENV-02 requirements
**Example:**
```python
# Source: docs/integrations.md, docs/environments.md
# core/models.py (additions)

class ProjectConnection(models.Model):
    """Links SCM connections to Projects."""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='connections'
    )
    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name='project_attachments'
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_project_connection'
        unique_together = ['project', 'connection']

    def save(self, *args, **kwargs):
        # Ensure only one default per plugin type per project
        if self.is_default:
            plugin = self.connection.get_plugin()
            if plugin:
                ProjectConnection.objects.filter(
                    project=self.project,
                    connection__plugin_name=self.connection.plugin_name,
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

class EnvironmentConnection(models.Model):
    """Links deploy connections to Environments."""
    environment = models.ForeignKey(
        Environment,
        on_delete=models.CASCADE,
        related_name='connections'
    )
    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name='environment_attachments'
    )
    is_default = models.BooleanField(default=False)
    config_override = models.JSONField(default=dict, blank=True)  # Environment-specific overrides
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_environment_connection'
        unique_together = ['environment', 'connection']

    def save(self, *args, **kwargs):
        # Ensure only one default per plugin type per environment
        if self.is_default:
            plugin = self.connection.get_plugin()
            if plugin:
                EnvironmentConnection.objects.filter(
                    environment=self.environment,
                    connection__plugin_name=self.connection.plugin_name,
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
```

### Anti-Patterns to Avoid
- **Storing plaintext credentials:** Always encrypt sensitive fields with Fernet
- **Revealing encrypted values in forms:** Never populate sensitive fields in edit forms
- **Single-threaded health checks:** Spread checks evenly to avoid load spikes
- **Hardcoded plugin list:** Use auto-discovery for extensibility
- **Blocking health checks:** Use background tasks, not request-time checks
- **Storing encryption key in database:** Keep in environment variable or file with restricted permissions

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symmetric encryption | Custom AES implementation | cryptography.fernet.Fernet | Battle-tested, handles IV, padding, HMAC |
| Key rotation | Custom key versioning | MultiFernet | Built-in support for multiple keys |
| GitHub API wrapper | Raw HTTP requests | PyGithub | Typed, handles auth, pagination, rate limits |
| Docker client | Raw socket/HTTP | docker-py | Official SDK, handles TLS, API versions |
| Plugin discovery | Custom file scanning | autodiscover_modules | Django standard, handles import errors |
| Multi-step forms | Custom session state | django-formtools wizard | Handles back navigation, validation state |
| Background tasks | Threading/APScheduler | django-tasks + DatabaseBackend | Persistent, crash-recoverable, native Django |
| Webhook signature | Manual HMAC | hmac.compare_digest | Constant-time comparison prevents timing attacks |

**Key insight:** The cryptography library's Fernet provides authenticated encryption with a simple API. PyGithub handles the complexity of GitHub App JWT authentication and token refresh automatically.

## Common Pitfalls

### Pitfall 1: Encryption Key Loss
**What goes wrong:** Lost encryption key makes all stored credentials unrecoverable
**Why it happens:** Key stored only in environment, container redeployed without it
**How to avoid:** Document key backup procedures, use secrets manager in production
**Warning signs:** Decryption errors after deployment

### Pitfall 2: GitHub App Token Expiration
**What goes wrong:** Installation access tokens expire after 1 hour, causing operations to fail
**Why it happens:** Caching tokens without refresh logic
**How to avoid:** PyGithub's AppInstallationAuth handles refresh automatically; don't cache tokens manually
**Warning signs:** 401 errors after initial success

### Pitfall 3: Docker Socket Permissions
**What goes wrong:** Permission denied accessing /var/run/docker.sock
**Why it happens:** Web process user not in docker group
**How to avoid:** Document socket permission requirements, test in setup wizard
**Warning signs:** "Permission denied" in health check

### Pitfall 4: Health Check Thundering Herd
**What goes wrong:** All connections checked simultaneously, overwhelming external APIs
**Why it happens:** Naive scheduling triggers all checks at same time
**How to avoid:** Spread checks evenly across interval using calculated delays
**Warning signs:** Rate limit errors, high latency during check period

### Pitfall 5: Plugin Registration Race Condition
**What goes wrong:** Plugin not found when creating connection
**Why it happens:** Connection created before app ready() completes
**How to avoid:** Ensure autodiscover runs in AppConfig.ready(), verify plugin exists before save
**Warning signs:** "Unknown plugin" errors on form submission

### Pitfall 6: Sensitive Field Exposure in Logs/Errors
**What goes wrong:** API keys appear in error messages or logs
**Why it happens:** Exception stringification includes request/config data
**How to avoid:** Use custom exception handling, redact sensitive patterns in logging
**Warning signs:** Credentials visible in error reports

### Pitfall 7: Empty String vs. None in Encrypted Fields
**What goes wrong:** Editing a connection replaces existing secret with empty string
**Why it happens:** Form submits empty string for unchanged password fields
**How to avoid:** Treat empty string as "keep existing" - only update if non-empty value provided
**Warning signs:** "Authentication failed" after editing non-sensitive fields

```python
# Safe credential update pattern
def update_connection_config(connection, new_config: dict):
    """Update config, preserving existing secrets for empty values."""
    existing_config = connection.get_config()
    plugin = connection.get_plugin()

    for key, value in new_config.items():
        if plugin.is_sensitive_field(key) and not value:
            # Keep existing value for empty sensitive fields
            new_config[key] = existing_config.get(key, '')

    connection.set_config(new_config)
```

## Code Examples

Verified patterns from official sources:

### Webhook Signature Verification
```python
# Source: GitHub Docs - Validating webhook deliveries
import hmac
import hashlib

def verify_webhook_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    """
    Verify GitHub webhook signature.
    signature_header: X-Hub-Signature-256 header value
    """
    if not signature_header:
        return False

    expected = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)
```

### Django Tasks Configuration
```python
# Source: django-tasks documentation
# settings.py
INSTALLED_APPS = [
    # ...existing apps...
    'django_tasks',
    'django_tasks.backends.database',
]

TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.database.DatabaseBackend"
    }
}

# Health check interval in seconds (default 15 minutes)
HEALTH_CHECK_INTERVAL = 900
```

### Running the Task Worker
```bash
# Source: django-tasks documentation
# Run worker process (separate terminal or supervisor)
python manage.py db_worker

# For periodic scheduling, use --repeat
# The schedule_health_checks task should be called periodically
python manage.py db_worker --repeat 900  # Run scheduler every 15 min
```

### Plugin URL Integration
```python
# Source: Django URL patterns
# pathfinder/urls.py
from django.urls import path, include
from plugins.base import registry

urlpatterns = [
    # ... existing patterns ...
]

# Dynamically add plugin URLs
for plugin_name, plugin in registry.all().items():
    patterns = plugin.get_urlpatterns()
    if patterns:
        urlpatterns.append(
            path(f'integrations/{plugin_name}/', include(patterns))
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery for all background tasks | Django 6.0 Tasks framework | Dec 2025 | Simpler setup, no Redis/RabbitMQ required |
| Custom encryption | Fernet from cryptography | Stable | Standard symmetric encryption |
| GitHub personal tokens | GitHub App authentication | 2023+ | Better security, granular permissions |
| requests for Docker API | docker-py SDK | Stable | Type safety, version handling |
| Manual plugin registration | autodiscover_modules | Django standard | Cleaner separation |

**Deprecated/outdated:**
- `django-background-tasks`: Use Django 6.0 Tasks with django-tasks backend
- GitHub OAuth Apps: Prefer GitHub Apps for machine access
- `X-Hub-Signature` (SHA1): Use `X-Hub-Signature-256` (SHA256)

## Open Questions

Things that couldn't be fully resolved:

1. **Django-tasks Production Stability**
   - What we know: django-tasks provides DatabaseBackend and db_worker
   - What's unclear: Package still marked "beta", production reliability unknown
   - Recommendation: Use for this project; acceptable for SQLite + small scale

2. **Plugin Removal Flow**
   - What we know: Filesystem deletion = orphan connections with warning
   - What's unclear: Exact UI flow for warning display, migration path
   - Recommendation: Show "Plugin missing" badge, prevent new operations

3. **Health Check Retry Logic**
   - What we know: Need to spread checks, avoid thundering herd
   - What's unclear: Retry behavior on transient failures
   - Recommendation: Single attempt per scheduled check; retry via manual "Check Now"

## Sources

### Primary (HIGH confidence)
- [Django 6.0 Tasks Documentation](https://docs.djangoproject.com/en/6.0/topics/tasks/) - Task API, backends, configuration
- [cryptography.io Fernet](https://cryptography.io/en/latest/fernet/) - Encryption patterns, MultiFernet
- [PyGithub Authentication](https://pygithub.readthedocs.io/en/stable/examples/Authentication.html) - GitHub App auth patterns
- [PyGithub GithubIntegration](https://pygithub.readthedocs.io/en/stable/github_integration.html) - Installation access
- [Docker SDK for Python](https://docker-py.readthedocs.io/en/stable/) - Container management
- [django-formtools wizard](https://django-formtools.readthedocs.io/en/latest/wizard.html) - Multi-step forms
- [Django autodiscover_modules](https://djangopatterns.readthedocs.io/en/latest/configuration/autodiscovery.html) - Plugin discovery

### Secondary (MEDIUM confidence)
- [django-tasks GitHub](https://github.com/RealOrangeOne/django-tasks) - DatabaseBackend, db_worker
- [GitHub webhook validation](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) - HMAC signature verification
- [django-fernet-encrypted-fields](https://github.com/jazzband/django-fernet-encrypted-fields) - Alternative encryption approach

### Tertiary (LOW confidence)
- WebSearch results on plugin architecture patterns - implementation varies

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official libraries, well-documented
- Plugin architecture: HIGH - Django standard autodiscover pattern
- Encryption: HIGH - cryptography library is gold standard
- GitHub/Docker SDKs: HIGH - Official, actively maintained
- Background tasks: MEDIUM - django-tasks is new but reference implementation
- Health check scheduling: MEDIUM - Pattern clear, timing tuning may need adjustment

**Research date:** 2026-01-23
**Valid until:** 2026-02-23 (30 days - stable domain, mature frameworks)
