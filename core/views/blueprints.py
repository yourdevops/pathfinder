"""Blueprint management views."""
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string

from core.models import Blueprint, BlueprintVersion, IntegrationConnection
from core.permissions import OperatorRequiredMixin, has_system_role
from core.tasks import sync_blueprint
from core.git_utils import (
    parse_git_url,
    clone_repo_shallow,
    read_manifest_from_repo,
    cleanup_repo,
    build_authenticated_git_url,
)


class BlueprintListView(LoginRequiredMixin, View):
    """List all registered blueprints."""
    template_name = 'core/blueprints/list.html'

    def get(self, request):
        # Query blueprints excluding pending (not yet synced)
        blueprints_qs = Blueprint.objects.exclude(
            sync_status='pending'
        ).select_related('connection').order_by('name', 'created_at')

        # Collect unique tags and deploy plugins for filtering
        all_tags = set()
        deploy_plugins = set()
        for bp in blueprints_qs:
            if bp.tags:
                all_tags.update(bp.tags)
            if bp.deploy_plugins:
                deploy_plugins.update(bp.deploy_plugins)

        # Build blueprint data with availability info
        blueprint_data = []
        for bp in blueprints_qs:
            is_available = bp.is_available_globally()
            blueprint_data.append({
                'blueprint': bp,
                'is_available': is_available,
                'required_plugins': bp.deploy_plugins if not is_available else [],
            })

        # Check if user can manage blueprints
        can_manage = has_system_role(request.user, ['admin', 'operator'])

        return render(request, self.template_name, {
            'blueprints': blueprint_data,
            'all_tags': sorted(all_tags),
            'deploy_plugins': sorted(deploy_plugins),
            'can_manage': can_manage,
        })


class BlueprintPreviewView(OperatorRequiredMixin, View):
    """HTMX endpoint for previewing manifest before registration."""

    def post(self, request):
        git_url = request.POST.get('git_url', '').strip()
        connection_id = request.POST.get('connection_id', '').strip()

        # Validate URL format
        if not git_url:
            return self._render_error(request, 'Please enter a Git URL')

        parsed = parse_git_url(git_url)
        if not parsed:
            return self._render_error(request, 'Invalid Git URL format. Use HTTPS or SSH format.')

        # Get connection if specified
        connection = None
        if connection_id:
            try:
                connection = IntegrationConnection.objects.get(
                    id=connection_id,
                    status='active'
                )
            except IntegrationConnection.DoesNotExist:
                return self._render_error(request, 'Selected connection not found or inactive.')

        # Build authenticated URL
        auth_url = build_authenticated_git_url(git_url, connection)

        repo = None
        temp_dir = None

        try:
            # Clone repository (shallow, main branch)
            repo, temp_dir = clone_repo_shallow(git_url, 'main', auth_url)

            # Read manifest
            manifest = read_manifest_from_repo(temp_dir)

            # Build preview data
            preview_data = {
                'name': manifest.get('name', ''),
                'description': manifest.get('description', ''),
                'tags': manifest.get('tags', []),
                'ci_plugin': manifest.get('ci', {}).get('type', ''),
                'deploy_plugins': self._get_deploy_plugins(manifest),
            }

            return self._render_success(request, preview_data)

        except FileNotFoundError as e:
            return self._render_error(request, str(e))

        except Exception as e:
            error_msg = str(e)
            # Clean up error message for display
            if 'Could not read from remote repository' in error_msg:
                error_msg = 'Could not access repository. Check URL and authentication.'
            elif 'Repository not found' in error_msg:
                error_msg = 'Repository not found. Check the URL.'
            elif 'Authentication failed' in error_msg:
                error_msg = 'Authentication failed. Select a connection with valid credentials.'
            return self._render_error(request, error_msg)

        finally:
            if repo and temp_dir:
                cleanup_repo(repo, temp_dir)

    def _get_deploy_plugins(self, manifest):
        """Extract deploy plugins list from manifest."""
        deploy_config = manifest.get('deploy', {})
        required_plugins = deploy_config.get('required_plugins', [])
        if required_plugins:
            return required_plugins
        deploy_type = deploy_config.get('type', '')
        return [deploy_type] if deploy_type else []

    def _render_success(self, request, preview_data):
        """Render successful preview partial."""
        html = render_to_string('core/blueprints/_preview.html', {
            'preview_valid': True,
            'preview_data': preview_data,
        }, request=request)
        return HttpResponse(html)

    def _render_error(self, request, error_message):
        """Render error preview partial."""
        html = render_to_string('core/blueprints/_preview.html', {
            'preview_valid': False,
            'preview_error': error_message,
        }, request=request)
        return HttpResponse(html)


class BlueprintRegisterView(OperatorRequiredMixin, View):
    """Register a new blueprint from a Git repository."""
    template_name = 'core/blueprints/register.html'

    def get(self, request):
        # Query active SCM connections (GitHub for now)
        scm_connections = IntegrationConnection.objects.filter(
            plugin_name='github',
            status='active'
        ).order_by('name')

        return render(request, self.template_name, {
            'scm_connections': scm_connections,
        })

    def post(self, request):
        git_url = request.POST.get('git_url', '').strip()
        connection_id = request.POST.get('connection_id', '').strip()

        # Validate URL not empty
        if not git_url:
            messages.error(request, 'Git URL is required.')
            return self._render_form(request, git_url, connection_id)

        # Validate URL format
        parsed = parse_git_url(git_url)
        if not parsed:
            messages.error(request, 'Invalid Git URL format.')
            return self._render_form(request, git_url, connection_id)

        # Check for duplicate
        if Blueprint.objects.filter(git_url=git_url).exists():
            messages.error(request, 'A blueprint with this Git URL already exists.')
            return self._render_form(request, git_url, connection_id)

        # Get connection if specified
        connection = None
        if connection_id:
            try:
                connection = IntegrationConnection.objects.get(
                    id=connection_id,
                    status='active'
                )
            except IntegrationConnection.DoesNotExist:
                messages.error(request, 'Selected connection not found.')
                return self._render_form(request, git_url, connection_id)

        # Validate manifest exists by re-fetching (preview validation)
        auth_url = build_authenticated_git_url(git_url, connection)
        repo = None
        temp_dir = None

        try:
            repo, temp_dir = clone_repo_shallow(git_url, 'main', auth_url)
            manifest = read_manifest_from_repo(temp_dir)
        except FileNotFoundError:
            messages.error(request, 'Cannot register: manifest file not found in repository.')
            return self._render_form(request, git_url, connection_id)
        except Exception as e:
            messages.error(request, f'Cannot register: {str(e)}')
            return self._render_form(request, git_url, connection_id)
        finally:
            if repo and temp_dir:
                cleanup_repo(repo, temp_dir)

        # Create blueprint
        blueprint = Blueprint.objects.create(
            git_url=git_url,
            connection=connection,
            sync_status='pending',
            created_by=request.user.username,
        )

        # Enqueue sync task
        sync_blueprint.enqueue(blueprint_id=blueprint.id)

        messages.success(request, f'Blueprint registered. Syncing from repository...')
        return redirect('blueprints:detail', blueprint_name=blueprint.name)

    def _render_form(self, request, git_url='', connection_id=''):
        """Re-render form with current values."""
        scm_connections = IntegrationConnection.objects.filter(
            plugin_name='github',
            status='active'
        ).order_by('name')

        return render(request, self.template_name, {
            'scm_connections': scm_connections,
            'git_url': git_url,
            'connection_id': connection_id,
        })


class BlueprintDetailView(LoginRequiredMixin, View):
    """Display blueprint details and versions."""
    template_name = 'core/blueprints/detail.html'

    def get(self, request, blueprint_name):
        blueprint = get_object_or_404(Blueprint, name=blueprint_name)

        # Check for prerelease toggle
        show_prereleases = request.GET.get('show_prereleases') == 'true'

        # Get versions
        versions_qs = blueprint.versions.all()
        prerelease_count = versions_qs.filter(is_prerelease=True).count()

        if not show_prereleases:
            versions_qs = versions_qs.filter(is_prerelease=False)

        versions = list(versions_qs.order_by('-sort_key'))

        # Get selected version
        selected_tag = request.GET.get('version')
        current_version = None

        if selected_tag:
            current_version = blueprint.versions.filter(tag_name=selected_tag).first()

        if not current_version and versions:
            # Default to latest stable version
            current_version = blueprint.latest_version or (versions[0] if versions else None)

        # Check availability
        is_available = blueprint.is_available_globally()
        required_plugins = blueprint.deploy_plugins if not is_available else []

        # Check permissions
        can_manage = has_system_role(request.user, ['admin', 'operator'])

        return render(request, self.template_name, {
            'blueprint': blueprint,
            'versions': versions,
            'current_version': current_version,
            'show_prereleases': show_prereleases,
            'prerelease_count': prerelease_count,
            'is_available': is_available,
            'required_plugins': required_plugins,
            'can_manage': can_manage,
        })


class BlueprintSyncView(OperatorRequiredMixin, View):
    """Trigger manual sync of a blueprint."""

    def post(self, request, blueprint_name):
        blueprint = get_object_or_404(Blueprint, name=blueprint_name)

        if blueprint.sync_status != 'syncing':
            blueprint.sync_status = 'syncing'
            blueprint.sync_error = ''
            blueprint.save(update_fields=['sync_status', 'sync_error'])
            sync_blueprint.enqueue(blueprint_id=blueprint.id)

        # Check if HTMX request
        if request.headers.get('HX-Request'):
            html = render_to_string('core/blueprints/_sync_status.html', {
                'blueprint': blueprint,
                'can_manage': has_system_role(request.user, ['admin', 'operator']),
            }, request=request)
            return HttpResponse(html)

        return redirect('blueprints:detail', blueprint_name=blueprint.name)


class BlueprintSyncStatusView(LoginRequiredMixin, View):
    """Return sync status partial for HTMX polling."""

    def get(self, request, blueprint_name):
        blueprint = get_object_or_404(Blueprint, name=blueprint_name)

        html = render_to_string('core/blueprints/_sync_status.html', {
            'blueprint': blueprint,
            'can_manage': has_system_role(request.user, ['admin', 'operator']),
        }, request=request)
        return HttpResponse(html)


# Alias for backwards compatibility with URL patterns
BlueprintsListView = BlueprintListView
