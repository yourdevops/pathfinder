# Phase 4: Blueprints - Research

**Researched:** 2026-01-26
**Domain:** Blueprint catalog, git tag versioning, YAML manifest parsing, availability filtering
**Confidence:** HIGH

## Summary

This research covers the technical foundation for implementing Phase 4: Blueprints, which enables platform engineers to register service templates (blueprints) from git URLs and developers to browse available blueprints filtered by project environment connections. Blueprints define "golden paths" for application deployment via `ssp-template.yaml` manifests.

The standard approach uses the existing GitHub plugin infrastructure (PyGithub) for fetching manifest files and git tags, the `semver` library for semantic version parsing and sorting, PyYAML's `safe_load` for secure manifest parsing, and the Django Tasks framework (already configured) for background sync operations. The Blueprint model stores metadata synced from the manifest, with a separate BlueprintVersion model for git tags.

Key user decisions from CONTEXT.md are locked: compact table-style list layout, flat list with filter controls, single URL field registration with immediate save and background sync, "Syncing..." status during sync, auto-select latest semantic version, pre-releases hidden by default with toggle, dimmed unavailable blueprints with tooltips.

**Primary recommendation:** Implement Blueprint and BlueprintVersion models, sync task using PyGithub to fetch ssp-template.yaml and git tags, use semver library for version parsing/sorting, display table-style list with filters and availability dimming based on EnvironmentConnection matching deploy.plugin.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 6.0.1 | Web framework, ORM, Tasks | Already installed, patterns established |
| PyGithub | 2.5+ | Git tag listing, file content fetching | Already installed for Phase 3 GitHub plugin |
| PyYAML | 6.0+ | YAML manifest parsing | Bundled with Django, safe_load for security |
| semver | 3.0+ | Semantic version parsing and sorting | Standard Python semver library |
| django-tasks | 0.4+ | Background sync operations | Already configured for health checks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| packaging | 23.0+ | Version parsing fallback | Already installed (Django dependency), for non-semver tags |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| semver | packaging.version | semver is stricter SemVer 2.0.0 compliance |
| PyYAML | ruamel.yaml | PyYAML sufficient, ruamel.yaml for round-trip editing |
| PyGithub | httpx + raw API | PyGithub already in use, handles auth and pagination |

**Installation:**
```bash
pip install semver
# PyYAML, PyGithub already installed
```

## Architecture Patterns

### Recommended Model Structure
```
core/
├── models.py                  # Add Blueprint, BlueprintVersion
├── views/
│   ├── blueprints.py          # Replace placeholder with real implementation
│   └── __init__.py            # Export new views
├── tasks.py                   # Add sync_blueprint task
├── templates/core/
│   └── blueprints/
│       ├── list.html          # Table layout with filters
│       ├── detail.html        # Blueprint detail with version dropdown
│       └── register.html      # Single URL field registration form
└── urls.py                    # Add blueprint routes
```

### Pattern 1: Blueprint Model with Status-Based Sync
**What:** Blueprint model storing git URL and synced metadata with explicit sync status
**When to use:** All blueprint records
**Example:**
```python
# Source: docs/blueprints.md model requirements + CONTEXT.md decisions
# core/models.py
import uuid
from django.db import models

class Blueprint(models.Model):
    """
    Service template registered from a git URL.

    Metadata is synced from ssp-template.yaml in the repository.
    """
    SYNC_STATUS_CHOICES = [
        ('pending', 'Pending'),      # Initial state, sync not started
        ('syncing', 'Syncing'),      # Sync in progress
        ('synced', 'Synced'),        # Successfully synced
        ('error', 'Error'),          # Sync failed
    ]

    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    # Source repository
    git_url = models.URLField(max_length=500, unique=True)
    default_branch = models.CharField(max_length=100, default='main')

    # Synced metadata from ssp-template.yaml
    name = models.CharField(max_length=100, blank=True)  # Populated from manifest
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list)  # ['python', 'kubernetes']
    ci_plugin = models.CharField(max_length=63, blank=True)  # e.g., 'jenkins', 'github-actions'
    deploy_plugin = models.CharField(max_length=63, blank=True)  # e.g., 'kubernetes', 'docker'

    # Full manifest stored for reference
    manifest = models.JSONField(default=dict)

    # Sync status
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default='pending')
    sync_error = models.TextField(blank=True)  # Error message if sync failed
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Connection used for syncing (auto-detected GitHub connection)
    connection = models.ForeignKey(
        'IntegrationConnection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blueprints'
    )

    # Audit fields
    created_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_blueprint'
        ordering = ['name', 'created_at']

    def __str__(self):
        return self.name or f'Blueprint {self.uuid}'

    @property
    def version_count(self) -> int:
        """Return count of available versions."""
        return self.versions.count()

    @property
    def latest_version(self) -> 'BlueprintVersion | None':
        """Return latest non-prerelease version, or None."""
        return self.versions.filter(is_prerelease=False).order_by('-sort_key').first()

    def is_available_for_project(self, project) -> bool:
        """
        Check if this blueprint is available for a project.

        Available if any environment in the project has a connection
        matching the blueprint's deploy_plugin.
        """
        if not self.deploy_plugin:
            return True  # No deploy plugin requirement

        from core.models import EnvironmentConnection
        return EnvironmentConnection.objects.filter(
            environment__project=project,
            connection__plugin_name=self.deploy_plugin
        ).exists()

    def is_available_globally(self) -> bool:
        """
        Check if blueprint is available based on any connection in the system.
        """
        if not self.deploy_plugin:
            return True

        from core.models import IntegrationConnection
        return IntegrationConnection.objects.filter(
            plugin_name=self.deploy_plugin,
            status='active'
        ).exists()


class BlueprintVersion(models.Model):
    """
    A git tag representing a version of a blueprint.
    """
    blueprint = models.ForeignKey(
        Blueprint,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    tag_name = models.CharField(max_length=100)  # e.g., 'v1.2.3', '1.0.0-beta.1'
    commit_sha = models.CharField(max_length=40, blank=True)  # Git commit SHA

    # Parsed version info
    major = models.IntegerField(default=0)
    minor = models.IntegerField(default=0)
    patch = models.IntegerField(default=0)
    prerelease = models.CharField(max_length=100, blank=True)  # e.g., 'alpha', 'beta.1', 'rc.2'
    is_prerelease = models.BooleanField(default=False)

    # Sort key for ordering (computed from semver)
    sort_key = models.CharField(max_length=100, blank=True)  # Zero-padded for string sort

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_blueprint_version'
        unique_together = ['blueprint', 'tag_name']
        ordering = ['-sort_key']  # Latest first

    def __str__(self):
        return f'{self.blueprint.name} {self.tag_name}'

    @property
    def display_name(self) -> str:
        """Formatted display name."""
        if self.is_prerelease:
            return f'{self.tag_name} (pre-release)'
        return self.tag_name
```

### Pattern 2: Background Sync Task
**What:** Django task for fetching manifest and tags from GitHub
**When to use:** After blueprint registration and manual sync triggers
**Example:**
```python
# Source: Django Tasks docs, PyGithub file content API
# core/tasks.py (additions)
import yaml
import semver
from django_tasks import task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def parse_github_url(url: str) -> tuple[str, str] | None:
    """
    Parse GitHub URL to extract owner/repo.

    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git

    Returns (owner, repo) or None if not a valid GitHub URL.
    """
    import re

    # HTTPS format
    https_match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if https_match:
        return https_match.group(1), https_match.group(2)

    # SSH format
    ssh_match = re.match(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)

    return None


def compute_version_sort_key(major: int, minor: int, patch: int, prerelease: str) -> str:
    """
    Compute sortable string key for version ordering.

    Format: MMMMM.MMMMM.PPPPP.RRRR
    - Major, minor, patch zero-padded to 5 digits
    - Prerelease: 'zzzz' for release, otherwise prerelease string

    This ensures: 1.0.0 > 1.0.0-rc.1 > 1.0.0-beta.1 > 1.0.0-alpha.1
    """
    if prerelease:
        # Prereleases sort before releases (z comes after a-y)
        return f'{major:05d}.{minor:05d}.{patch:05d}.{prerelease}'
    else:
        # Releases sort after prereleases
        return f'{major:05d}.{minor:05d}.{patch:05d}.zzzz'


def parse_version_tag(tag_name: str) -> dict:
    """
    Parse a git tag into version components.

    Returns dict with: major, minor, patch, prerelease, is_prerelease, sort_key
    """
    # Strip leading 'v' if present
    version_str = tag_name.lstrip('vV')

    try:
        ver = semver.Version.parse(version_str)
        is_prerelease = bool(ver.prerelease)
        return {
            'major': ver.major,
            'minor': ver.minor,
            'patch': ver.patch,
            'prerelease': ver.prerelease or '',
            'is_prerelease': is_prerelease,
            'sort_key': compute_version_sort_key(ver.major, ver.minor, ver.patch, ver.prerelease or ''),
        }
    except ValueError:
        # Non-semver tag - treat as 0.0.0 with tag as prerelease
        return {
            'major': 0,
            'minor': 0,
            'patch': 0,
            'prerelease': version_str,
            'is_prerelease': True,
            'sort_key': compute_version_sort_key(0, 0, 0, version_str),
        }


@task(queue_name='blueprint_sync')
def sync_blueprint(blueprint_id: int) -> dict:
    """
    Sync blueprint metadata and versions from GitHub.

    1. Fetch ssp-template.yaml from default branch
    2. Parse manifest and update blueprint fields
    3. Fetch all git tags
    4. Parse tags into BlueprintVersion records
    """
    from core.models import Blueprint, BlueprintVersion, IntegrationConnection
    from plugins.base import registry

    try:
        blueprint = Blueprint.objects.get(id=blueprint_id)
    except Blueprint.DoesNotExist:
        logger.error(f'Blueprint {blueprint_id} not found')
        return {'error': 'Blueprint not found'}

    # Mark as syncing
    blueprint.sync_status = 'syncing'
    blueprint.sync_error = ''
    blueprint.save(update_fields=['sync_status', 'sync_error'])

    try:
        # Get or auto-detect GitHub connection
        connection = blueprint.connection
        if not connection:
            # Find first active GitHub connection
            connection = IntegrationConnection.objects.filter(
                plugin_name='github',
                status='active'
            ).first()

            if not connection:
                raise ValueError('No GitHub connection available. Please create one first.')

            blueprint.connection = connection

        # Get GitHub plugin and client
        plugin = registry.get('github')
        if not plugin:
            raise ValueError('GitHub plugin not available')

        config = connection.get_config()
        client = plugin._get_github_client(config)

        # Parse git URL
        parsed = parse_github_url(blueprint.git_url)
        if not parsed:
            raise ValueError(f'Invalid GitHub URL: {blueprint.git_url}')

        owner, repo_name = parsed
        repo = client.get_repo(f'{owner}/{repo_name}')

        # Fetch ssp-template.yaml from default branch
        manifest_content = None
        for manifest_name in ['ssp-template.yaml', 'pathfinder-template.yaml']:
            try:
                file_content = repo.get_contents(manifest_name, ref=blueprint.default_branch)
                manifest_content = file_content.decoded_content.decode('utf-8')
                break
            except Exception:
                continue

        if not manifest_content:
            raise ValueError('No ssp-template.yaml or pathfinder-template.yaml found in repository')

        # Parse manifest with safe_load (security)
        manifest = yaml.safe_load(manifest_content)
        if not isinstance(manifest, dict):
            raise ValueError('Invalid manifest format: expected YAML dictionary')

        # Update blueprint fields from manifest
        blueprint.name = manifest.get('name', '')
        blueprint.description = manifest.get('description', '')
        blueprint.tags = manifest.get('tags', [])

        # Extract plugin references
        ci_config = manifest.get('ci', {})
        deploy_config = manifest.get('deploy', {})

        blueprint.ci_plugin = ci_config.get('type', '') if isinstance(ci_config, dict) else ''

        # deploy.required_plugins or deploy.type
        if isinstance(deploy_config, dict):
            required_plugins = deploy_config.get('required_plugins', [])
            if required_plugins:
                # Use first deploy plugin
                blueprint.deploy_plugin = required_plugins[0] if isinstance(required_plugins, list) else ''
            else:
                blueprint.deploy_plugin = deploy_config.get('type', '')
        else:
            blueprint.deploy_plugin = ''

        blueprint.manifest = manifest

        # Fetch git tags
        tags = list(repo.get_tags())

        # Sync versions
        existing_tags = set(blueprint.versions.values_list('tag_name', flat=True))
        fetched_tags = set()

        for tag in tags:
            tag_name = tag.name
            fetched_tags.add(tag_name)

            # Parse version info
            version_info = parse_version_tag(tag_name)

            # Create or update version
            BlueprintVersion.objects.update_or_create(
                blueprint=blueprint,
                tag_name=tag_name,
                defaults={
                    'commit_sha': tag.commit.sha if tag.commit else '',
                    **version_info
                }
            )

        # Remove versions for tags that no longer exist
        removed_tags = existing_tags - fetched_tags
        if removed_tags:
            blueprint.versions.filter(tag_name__in=removed_tags).delete()

        # Mark as synced
        blueprint.sync_status = 'synced'
        blueprint.last_synced_at = timezone.now()
        blueprint.save()

        logger.info(f'Synced blueprint {blueprint.name}: {len(tags)} versions')
        return {
            'status': 'synced',
            'name': blueprint.name,
            'versions': len(tags),
        }

    except Exception as e:
        logger.exception(f'Failed to sync blueprint {blueprint_id}')
        blueprint.sync_status = 'error'
        blueprint.sync_error = str(e)
        blueprint.save(update_fields=['sync_status', 'sync_error'])
        return {'error': str(e)}
```

### Pattern 3: List View with Availability Filtering
**What:** Table-style list with filters, dimmed unavailable blueprints
**When to use:** Blueprint catalog page
**Example:**
```python
# Source: CONTEXT.md decisions, existing connections list pattern
# core/views/blueprints.py
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from core.models import Blueprint, IntegrationConnection
from core.permissions import OperatorRequiredMixin


class BlueprintListView(LoginRequiredMixin, View):
    """
    Blueprint catalog with filtering and availability display.

    - Compact table layout
    - Filter by tags and deploy plugin
    - Unavailable blueprints dimmed with tooltip
    - Toggle to show/hide unavailable
    """
    template_name = 'core/blueprints/list.html'

    def get(self, request):
        blueprints = Blueprint.objects.exclude(sync_status='pending').select_related('connection')

        # Get unique tags and deploy plugins for filters
        all_tags = set()
        deploy_plugins = set()
        for bp in blueprints:
            all_tags.update(bp.tags or [])
            if bp.deploy_plugin:
                deploy_plugins.add(bp.deploy_plugin)

        # Get available deploy plugins (from active connections)
        available_plugins = set(
            IntegrationConnection.objects.filter(status='active')
            .values_list('plugin_name', flat=True)
        )

        # Annotate availability for each blueprint
        blueprint_data = []
        for bp in blueprints:
            is_available = bp.is_available_globally()
            blueprint_data.append({
                'blueprint': bp,
                'is_available': is_available,
                'required_plugin': bp.deploy_plugin if not is_available else None,
            })

        # Check operator permission
        from core.permissions import has_system_role
        can_manage = has_system_role(request.user, ['admin', 'operator'])

        return render(request, self.template_name, {
            'blueprints': blueprint_data,
            'all_tags': sorted(all_tags),
            'deploy_plugins': sorted(deploy_plugins),
            'can_manage': can_manage,
        })


class BlueprintRegisterView(OperatorRequiredMixin, View):
    """
    Register a new blueprint from git URL.

    - Single URL field entry
    - Save immediately, sync in background
    """
    template_name = 'core/blueprints/register.html'

    def get(self, request):
        # Check for available GitHub connections
        github_connections = IntegrationConnection.objects.filter(
            plugin_name='github',
            status='active'
        )

        if not github_connections.exists():
            # No GitHub connection - show warning
            return render(request, self.template_name, {
                'no_github_connection': True,
            })

        return render(request, self.template_name, {
            'github_connections': github_connections,
        })

    def post(self, request):
        git_url = request.POST.get('git_url', '').strip()

        if not git_url:
            return render(request, self.template_name, {
                'error': 'Git URL is required',
            })

        # Validate URL format
        from core.tasks import parse_github_url
        if not parse_github_url(git_url):
            return render(request, self.template_name, {
                'error': 'Invalid GitHub URL format',
                'git_url': git_url,
            })

        # Check for duplicate
        if Blueprint.objects.filter(git_url=git_url).exists():
            return render(request, self.template_name, {
                'error': 'A blueprint with this URL already exists',
                'git_url': git_url,
            })

        # Create blueprint record
        blueprint = Blueprint.objects.create(
            git_url=git_url,
            sync_status='pending',
            created_by=request.user.username,
        )

        # Trigger background sync
        from core.tasks import sync_blueprint
        sync_blueprint.enqueue(blueprint_id=blueprint.id)

        # Redirect to list (or detail page to show sync status)
        return redirect('blueprints:list')
```

### Pattern 4: Detail View with Version Selection
**What:** Blueprint detail page with version dropdown
**When to use:** Viewing individual blueprint
**Example:**
```python
# Source: CONTEXT.md version management decisions
# core/views/blueprints.py (continued)

class BlueprintDetailView(LoginRequiredMixin, View):
    """
    Blueprint detail page with version selection.

    - Metadata from manifest
    - Version dropdown (latest selected by default)
    - Pre-releases hidden by default with toggle
    - Manual sync button for operators
    """
    template_name = 'core/blueprints/detail.html'

    def get(self, request, uuid):
        blueprint = get_object_or_404(Blueprint, uuid=uuid)

        # Get versions
        show_prereleases = request.GET.get('show_prereleases') == 'true'

        if show_prereleases:
            versions = blueprint.versions.all()
        else:
            versions = blueprint.versions.filter(is_prerelease=False)

        # Default to latest stable version
        selected_version = request.GET.get('version')
        if selected_version:
            current_version = blueprint.versions.filter(tag_name=selected_version).first()
        else:
            current_version = blueprint.latest_version

        # Check availability
        is_available = blueprint.is_available_globally()

        # Check permissions
        from core.permissions import has_system_role
        can_manage = has_system_role(request.user, ['admin', 'operator'])

        return render(request, self.template_name, {
            'blueprint': blueprint,
            'versions': versions,
            'current_version': current_version,
            'show_prereleases': show_prereleases,
            'prerelease_count': blueprint.versions.filter(is_prerelease=True).count(),
            'is_available': is_available,
            'required_plugin': blueprint.deploy_plugin if not is_available else None,
            'can_manage': can_manage,
        })


class BlueprintSyncView(OperatorRequiredMixin, View):
    """Manually trigger blueprint sync."""

    def post(self, request, uuid):
        blueprint = get_object_or_404(Blueprint, uuid=uuid)

        # Only sync if not already syncing
        if blueprint.sync_status != 'syncing':
            blueprint.sync_status = 'syncing'
            blueprint.save(update_fields=['sync_status'])

            from core.tasks import sync_blueprint
            sync_blueprint.enqueue(blueprint_id=blueprint.id)

        # Return updated status for HTMX
        if request.headers.get('HX-Request'):
            return render(request, 'core/blueprints/_sync_status.html', {
                'blueprint': blueprint,
            })

        return redirect('blueprints:detail', uuid=uuid)
```

### Anti-Patterns to Avoid
- **Synchronous git operations in request:** Always use background tasks for network calls
- **Using yaml.load():** Always use yaml.safe_load() for security
- **Ignoring non-semver tags:** Handle gracefully by treating as prerelease
- **Hardcoding manifest filename:** Support both ssp-template.yaml and pathfinder-template.yaml
- **Storing full manifest in every version:** Manifest belongs on Blueprint, versions are lightweight
- **Blocking UI during sync:** Save immediately with 'pending' status, update via background task

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic version parsing | Regex parsing | semver library | Handles edge cases, prerelease ordering |
| Version comparison/sorting | Custom comparators | semver.Version.compare() | Correct precedence rules |
| YAML parsing | Manual parsing | PyYAML safe_load | Security, edge case handling |
| Git tag listing | Raw HTTP requests | PyGithub repo.get_tags() | Pagination, auth, error handling |
| File content fetching | Raw git clone | PyGithub repo.get_contents() | Efficient, no full clone needed |
| Background sync | Threading/subprocess | Django Tasks | Crash recovery, persistence |
| URL pattern matching | String manipulation | Regex with tested patterns | Edge cases (trailing slash, .git suffix) |

**Key insight:** PyGithub already provides everything needed for blueprint sync - no additional git libraries required. The semver library handles the complexity of version precedence (1.0.0 > 1.0.0-rc.1 > 1.0.0-beta.1).

## Common Pitfalls

### Pitfall 1: Non-Semver Git Tags
**What goes wrong:** Tags like 'latest', 'stable', 'v1' break semver parsing
**Why it happens:** Not all projects follow strict semver
**How to avoid:** Catch ValueError from semver.parse, treat non-semver as 0.0.0 with prerelease
**Warning signs:** "Invalid version" errors in sync logs

### Pitfall 2: Manifest Not Found
**What goes wrong:** Repository doesn't have ssp-template.yaml
**Why it happens:** Template not yet converted, wrong filename
**How to avoid:** Check multiple filenames, provide clear error message
**Warning signs:** Sync fails with "manifest not found"

### Pitfall 3: GitHub Rate Limiting
**What goes wrong:** Too many API calls, 403 errors
**Why it happens:** Multiple syncs triggered rapidly, large repos with many tags
**How to avoid:** Use authenticated requests (already via GitHub connection), cache results
**Warning signs:** 403 errors during sync

### Pitfall 4: Race Condition on Sync
**What goes wrong:** Multiple sync tasks running concurrently corrupt data
**Why it happens:** User clicks sync multiple times
**How to avoid:** Check sync_status before enqueue, skip if already 'syncing'
**Warning signs:** Duplicate version records, inconsistent state

### Pitfall 5: Large Manifest Files
**What goes wrong:** Memory issues parsing huge YAML
**Why it happens:** Manifest includes large embedded content
**How to avoid:** Check file size before parsing, set reasonable limit (e.g., 1MB)
**Warning signs:** Out of memory during sync

### Pitfall 6: Version Sort Order
**What goes wrong:** Pre-releases sorted incorrectly (1.0.0-alpha after 1.0.0)
**Why it happens:** String sorting vs semver precedence
**How to avoid:** Use computed sort_key field with padding, store 'zzzz' for releases
**Warning signs:** "Latest version" shows wrong version

```python
# Correct version sorting with computed key
def compute_version_sort_key(major, minor, patch, prerelease):
    """
    Pre-releases sort BEFORE their release.
    1.0.0-alpha.1 < 1.0.0-beta.1 < 1.0.0-rc.1 < 1.0.0
    """
    if prerelease:
        return f'{major:05d}.{minor:05d}.{patch:05d}.{prerelease}'
    return f'{major:05d}.{minor:05d}.{patch:05d}.zzzz'  # 'zzzz' > any prerelease
```

## Code Examples

Verified patterns from official sources:

### Fetching File Content with PyGithub
```python
# Source: PyGithub documentation
from github import Github

def get_manifest(client, repo_name, branch='main'):
    """Fetch ssp-template.yaml from repository."""
    repo = client.get_repo(repo_name)

    for filename in ['ssp-template.yaml', 'pathfinder-template.yaml']:
        try:
            content = repo.get_contents(filename, ref=branch)
            return content.decoded_content.decode('utf-8')
        except Exception:
            continue

    raise FileNotFoundError('No manifest found')
```

### Listing Git Tags with PyGithub
```python
# Source: PyGithub Repository documentation
def list_tags(client, repo_name):
    """List all git tags with commit SHA."""
    repo = client.get_repo(repo_name)
    tags = repo.get_tags()  # Returns PaginatedList

    return [
        {
            'name': tag.name,
            'sha': tag.commit.sha,
        }
        for tag in tags
    ]
```

### Safe YAML Parsing
```python
# Source: PyYAML documentation, security best practices
import yaml

def parse_manifest(content: str) -> dict:
    """
    Safely parse YAML manifest.

    Always use safe_load to prevent code execution.
    """
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError('Manifest must be a YAML dictionary')
        return data
    except yaml.YAMLError as e:
        raise ValueError(f'Invalid YAML: {e}')
```

### Semantic Version Parsing with semver
```python
# Source: python-semver documentation
import semver

def parse_tag(tag_name: str) -> semver.Version | None:
    """
    Parse git tag into semver Version.

    Returns None for non-semver tags.
    """
    # Strip leading 'v' or 'V'
    version_str = tag_name.lstrip('vV')

    try:
        return semver.Version.parse(version_str)
    except ValueError:
        return None

def sort_versions(versions: list[semver.Version]) -> list[semver.Version]:
    """Sort versions by semver precedence (latest first)."""
    return sorted(versions, reverse=True)

# Example usage
versions = [
    semver.Version.parse('1.0.0'),
    semver.Version.parse('1.0.0-beta.1'),
    semver.Version.parse('1.0.0-rc.1'),
    semver.Version.parse('0.9.0'),
]
sorted_versions = sort_versions(versions)
# Result: [1.0.0, 1.0.0-rc.1, 1.0.0-beta.1, 0.9.0]
```

### Availability Filtering Template Pattern
```html
<!-- Source: CONTEXT.md availability filtering decisions -->
<!-- Template pattern for dimmed unavailable blueprints -->
{% for item in blueprints %}
<tr class="{% if not item.is_available %}opacity-50{% endif %}">
    <td>
        {% if item.is_available %}
        <a href="{% url 'blueprints:detail' uuid=item.blueprint.uuid %}">
            {{ item.blueprint.name }}
        </a>
        {% else %}
        <span class="cursor-not-allowed" title="Requires {{ item.required_plugin }} connection">
            {{ item.blueprint.name }}
        </span>
        {% endif %}
    </td>
    <!-- ... other columns ... -->
</tr>
{% endfor %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full git clone for tags | PyGithub API (get_tags) | Stable | Faster, no disk usage |
| Manual version sorting | semver library | Stable | Correct precedence |
| yaml.load() | yaml.safe_load() | Security best practice | Prevents code execution |
| Celery for background tasks | Django 6.0 Tasks | Dec 2025 | Simpler, DB-backed |
| Separate sync service | In-process task worker | Django 6.0 | Single deployment |

**Deprecated/outdated:**
- `yaml.load()` without Loader: Use `yaml.safe_load()` only
- `semver` v2 module-level functions: Use `semver.Version` class in v3
- Custom version comparison: Use `semver.compare()` or built-in comparison

## Open Questions

Things that couldn't be fully resolved:

1. **Private Repository Support**
   - What we know: PyGithub handles auth via GitHub App or PAT
   - What's unclear: Should blueprints support multiple connections (different orgs)?
   - Recommendation: Use single connection per blueprint, allow changing it

2. **Webhook-Triggered Sync**
   - What we know: docs/blueprints.md mentions webhook sync option
   - What's unclear: Implementation details for webhook receiver
   - Recommendation: Manual sync for Phase 4, webhook sync as future enhancement

3. **Blueprint Deletion**
   - What we know: Deleting blueprint should cascade to versions
   - What's unclear: Should deletion be allowed if services reference the blueprint?
   - Recommendation: Soft delete or block if in use, decide in Phase 5

4. **GitHub Enterprise Support**
   - What we know: PyGithub supports custom base_url for GHE
   - What's unclear: How to determine base_url from git URL
   - Recommendation: Auto-detect from URL pattern, store in connection config

## Sources

### Primary (HIGH confidence)
- [python-semver documentation](https://python-semver.readthedocs.io/) - Version parsing, comparison, sorting
- [PyGithub Repository API](https://pygithub.readthedocs.io/en/latest/github_objects/Repository.html) - get_tags(), get_contents()
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) - safe_load security
- [Django 6.0 Tasks](https://docs.djangoproject.com/en/6.0/topics/tasks/) - Background task patterns
- docs/blueprints.md - Manifest format, registration flow

### Secondary (MEDIUM confidence)
- [semver PyPI](https://pypi.org/project/semver/) - Current version 3.0+
- [PyGithub PyPI](https://pypi.org/project/PyGithub/) - Version 2.8.1 features
- Existing Phase 3 implementation - Plugin patterns, task patterns

### Tertiary (LOW confidence)
- WebSearch results on best practices - General patterns only

## Metadata

**Confidence breakdown:**
- Blueprint model: HIGH - Based on docs/blueprints.md and existing patterns
- Sync task: HIGH - Uses existing PyGithub plugin infrastructure
- Version parsing: HIGH - semver library is authoritative for semver
- Availability filtering: HIGH - Clear requirements from CONTEXT.md
- UI patterns: HIGH - Follows existing connections list template

**Research date:** 2026-01-26
**Valid until:** 2026-02-26 (30 days - stable domain, established libraries)
