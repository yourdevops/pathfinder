from django.views.generic import ListView, CreateView, TemplateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect

from core.models import Project, Environment, ProjectMembership, Group, ProjectConnection, EnvironmentConnection
from core.forms import ProjectCreateForm, ProjectUpdateForm, EnvironmentForm, AddProjectMemberForm, AttachConnectionForm
from core.decorators import AdminRequiredMixin
from core.permissions import ProjectViewerMixin, ProjectContributorMixin, ProjectOwnerMixin, can_access_project


class ProjectListView(LoginRequiredMixin, ListView):
    """List all active/inactive projects with environment counts."""
    model = Project
    template_name = 'core/projects/list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        # Annotate with environment count to avoid N+1 queries
        return Project.objects.filter(
            status__in=['active', 'inactive']
        ).annotate(
            env_count=Count('environments')
        ).order_by('name')


class ProjectCreateModalView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Render the create project modal form."""
    template_name = 'core/projects/create_modal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ProjectCreateForm()
        return context


class ProjectCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Handle project creation from modal form."""
    model = Project
    form_class = ProjectCreateForm
    template_name = 'core/projects/create_modal.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username
        self.object = form.save()
        # Redirect to project list
        # Note: projects:detail URL doesn't exist until Plan 03
        # Once Plan 03 is complete, redirect can be updated to project detail
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('projects:list')
        return response

    def form_invalid(self, form):
        # Re-render modal with errors
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(vary_on_headers("HX-Request"), name='dispatch')
class ProjectDetailView(LoginRequiredMixin, ProjectViewerMixin, TemplateView):
    """Project detail with HTMX tab navigation."""

    def get_template_names(self):
        tab = self.request.GET.get('tab', 'services')
        # Validate tab name to prevent path traversal
        valid_tabs = ['services', 'environments', 'members', 'settings']
        if tab not in valid_tabs:
            tab = 'services'
        if self.request.htmx:
            return [f'core/projects/_{tab}_tab.html']
        return ['core/projects/detail.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get('tab', 'services')
        valid_tabs = ['services', 'environments', 'members', 'settings']
        if tab not in valid_tabs:
            tab = 'services'
        context['active_tab'] = tab

        # Tab-specific data
        if tab == 'environments':
            context['environments'] = self.project.environments.filter(
                status='active'
            ).order_by('order', 'name')
        elif tab == 'members':
            memberships = self.project.memberships.select_related('group').order_by('project_role')
            # Group memberships by role
            context['memberships'] = memberships
            context['owners'] = [m for m in memberships if m.project_role == 'owner']
            context['contributors'] = [m for m in memberships if m.project_role == 'contributor']
            context['viewers'] = [m for m in memberships if m.project_role == 'viewer']
        elif tab == 'settings':
            context['form'] = ProjectUpdateForm(instance=self.project)
        # services tab will be empty until Phase 5

        return context


class ProjectUpdateView(LoginRequiredMixin, ProjectOwnerMixin, UpdateView):
    """Update project settings."""
    model = Project
    form_class = ProjectUpdateForm
    template_name = 'core/projects/_settings_tab.html'

    def get_object(self, queryset=None):
        return self.project

    def get_success_url(self):
        return reverse('projects:detail', kwargs={'project_uuid': self.project.uuid}) + '?tab=settings'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Project settings updated.')
        return response


class ProjectArchiveView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Archive a project."""

    def post(self, request, *args, **kwargs):
        self.project.status = 'archived'
        self.project.save()
        messages.success(request, f'Project "{self.project.name}" has been archived.')
        return redirect('projects:list')


class EnvironmentCreateView(LoginRequiredMixin, ProjectContributorMixin, TemplateView):
    """Create a new environment."""
    template_name = 'core/projects/environment_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = EnvironmentForm()
        return context

    def post(self, request, *args, **kwargs):
        form = EnvironmentForm(request.POST)
        if form.is_valid():
            env = form.save(commit=False)
            env.project = self.project
            # First environment becomes default
            if not self.project.environments.exists():
                env.is_default = True
            env.save()
            messages.success(request, f'Environment "{env.name}" created.')
            return redirect('projects:detail', project_uuid=self.project.uuid)
        return self.render_to_response(self.get_context_data(form=form))


class EnvironmentDetailView(LoginRequiredMixin, ProjectViewerMixin, TemplateView):
    """View/edit environment details."""
    template_name = 'core/projects/environment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        env = get_object_or_404(
            Environment, uuid=kwargs.get('env_uuid'), project=self.project
        )
        context['environment'] = env
        context['form'] = EnvironmentForm(instance=env)
        # Get merged env vars with inheritance info
        context['merged_env_vars'] = self.get_merged_env_vars(env)
        return context

    def get_merged_env_vars(self, environment):
        """Merge project and environment env vars with inheritance tracking."""
        merged = {}

        # First add project-level vars (all inherited)
        for var in (self.project.env_vars or []):
            merged[var['key']] = {
                'key': var['key'],
                'value': var['value'],
                'lock': var.get('lock', False),
                'inherited': True,
                'source': 'project',
            }

        # Then add/override with environment-level vars
        for var in (environment.env_vars or []):
            key = var['key']
            if key in merged and merged[key]['lock']:
                # Locked at project level - can't override, mark as locked
                merged[key]['locked_override'] = True
            else:
                merged[key] = {
                    'key': var['key'],
                    'value': var['value'],
                    'lock': var.get('lock', False),
                    'inherited': False,
                    'source': 'environment',
                }

        return list(merged.values())


class EnvironmentUpdateView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Update environment settings."""

    def post(self, request, *args, **kwargs):
        env = get_object_or_404(
            Environment, uuid=kwargs.get('env_uuid'), project=self.project
        )
        form = EnvironmentForm(request.POST, instance=env)
        if form.is_valid():
            # Handle is_default - ensure only one default
            if form.cleaned_data.get('is_default'):
                Environment.objects.filter(
                    project=self.project, is_default=True
                ).exclude(pk=env.pk).update(is_default=False)

            form.save()
            messages.success(request, f'Environment "{env.name}" updated.')
            return redirect('projects:environment_detail',
                          project_uuid=self.project.uuid, env_uuid=env.uuid)
        # Re-render with errors
        return render(request, 'core/projects/environment_detail.html', {
            'project': self.project,
            'environment': env,
            'form': form,
            'user_project_role': self.user_project_role,
        })


class EnvironmentDeleteView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Delete an environment."""

    def post(self, request, *args, **kwargs):
        env = get_object_or_404(
            Environment, uuid=kwargs.get('env_uuid'), project=self.project
        )
        env_name = env.name
        was_default = env.is_default
        env.delete()

        # If deleted env was default, make another one default
        if was_default:
            next_env = self.project.environments.first()
            if next_env:
                next_env.is_default = True
                next_env.save()

        messages.success(request, f'Environment "{env_name}" deleted.')
        return redirect('projects:detail', project_uuid=self.project.uuid)


class AddMemberModalView(LoginRequiredMixin, ProjectOwnerMixin, TemplateView):
    """Modal for adding a group to project."""
    template_name = 'core/projects/add_member_modal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get groups not already in this project
        existing_group_ids = self.project.memberships.values_list('group_id', flat=True)
        context['form'] = AddProjectMemberForm(
            existing_group_ids=existing_group_ids
        )
        return context

    def post(self, request, *args, **kwargs):
        existing_group_ids = self.project.memberships.values_list('group_id', flat=True)
        form = AddProjectMemberForm(request.POST, existing_group_ids=existing_group_ids)
        if form.is_valid():
            ProjectMembership.objects.create(
                project=self.project,
                group=form.cleaned_data['group'],
                project_role=form.cleaned_data['project_role'],
                added_by=request.user.username
            )
            messages.success(request, f'Group "{form.cleaned_data["group"].name}" added to project.')
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('projects:detail', kwargs={'project_uuid': self.project.uuid}) + '?tab=members'
            return response
        return self.render_to_response(self.get_context_data(form=form))


class RemoveMemberView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Remove a group from project."""

    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, uuid=kwargs.get('group_uuid'))
        membership = get_object_or_404(
            ProjectMembership, project=self.project, group=group
        )
        membership.delete()
        messages.success(request, f'Group "{group.name}" removed from project.')
        return redirect('projects:detail', project_uuid=self.project.uuid)


# ============================================================================
# Project-level Environment Variables
# ============================================================================

class ProjectEnvVarModalView(LoginRequiredMixin, ProjectOwnerMixin, TemplateView):
    """Show modal to add/edit project-level env var."""
    template_name = 'core/projects/env_var_modal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target'] = 'project'
        context['action_url'] = reverse('projects:project_env_var_save',
                                        kwargs={'project_uuid': self.project.uuid})
        return context


class ProjectEnvVarSaveView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Save a project-level env var."""

    def post(self, request, *args, **kwargs):
        import re
        key = request.POST.get('key', '').strip().upper()
        value = request.POST.get('value', '')
        lock = request.POST.get('lock') == 'on'

        # Validate key
        if not key:
            messages.error(request, 'Key is required.')
            return redirect('projects:detail', project_uuid=self.project.uuid)

        if not re.match(r'^[A-Z][A-Z0-9_]*$', key):
            messages.error(request, 'Key must start with a letter and contain only uppercase letters, numbers, and underscores.')
            return redirect('projects:detail', project_uuid=self.project.uuid)

        # Update or add env var
        env_vars = list(self.project.env_vars or [])
        updated = False
        for var in env_vars:
            if var['key'] == key:
                var['value'] = value
                var['lock'] = lock
                updated = True
                break

        if not updated:
            env_vars.append({'key': key, 'value': value, 'lock': lock})

        self.project.env_vars = env_vars
        self.project.save(update_fields=['env_vars', 'updated_at'])
        messages.success(request, f'Variable "{key}" saved.')

        # Return to settings tab
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('projects:detail',
                                          kwargs={'project_uuid': self.project.uuid}) + '?tab=settings'
        return response


class ProjectEnvVarDeleteView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Delete a project-level env var."""

    def delete(self, request, *args, **kwargs):
        key = kwargs.get('key')
        env_vars = [v for v in (self.project.env_vars or []) if v['key'] != key]
        self.project.env_vars = env_vars
        self.project.save(update_fields=['env_vars', 'updated_at'])
        return HttpResponse(status=200)  # HTMX will remove the element


# ============================================================================
# Environment-level Environment Variables
# ============================================================================

class EnvVarModalView(LoginRequiredMixin, ProjectContributorMixin, TemplateView):
    """Show modal to add/edit environment-level env var."""
    template_name = 'core/projects/env_var_modal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        env = get_object_or_404(
            Environment, uuid=kwargs.get('env_uuid'), project=self.project
        )
        context['environment'] = env
        context['target'] = 'environment'
        context['action_url'] = reverse('projects:env_var_save',
                                        kwargs={'project_uuid': self.project.uuid,
                                               'env_uuid': env.uuid})
        # Pass locked keys from project for validation hint
        context['locked_keys'] = [v['key'] for v in (self.project.env_vars or [])
                                  if v.get('lock')]
        return context


class EnvVarSaveView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Save an environment-level env var."""

    def post(self, request, *args, **kwargs):
        import re
        env = get_object_or_404(
            Environment, uuid=kwargs.get('env_uuid'), project=self.project
        )

        key = request.POST.get('key', '').strip().upper()
        value = request.POST.get('value', '')

        # Validate key
        if not key:
            messages.error(request, 'Key is required.')
            return redirect('projects:environment_detail',
                          project_uuid=self.project.uuid, env_uuid=env.uuid)

        if not re.match(r'^[A-Z][A-Z0-9_]*$', key):
            messages.error(request, 'Key must start with a letter and contain only uppercase letters, numbers, and underscores.')
            return redirect('projects:environment_detail',
                          project_uuid=self.project.uuid, env_uuid=env.uuid)

        # Check if key is locked at project level
        locked_keys = [v['key'] for v in (self.project.env_vars or [])
                      if v.get('lock')]
        if key in locked_keys:
            messages.error(request, f'Variable "{key}" is locked at project level and cannot be overridden.')
            return redirect('projects:environment_detail',
                          project_uuid=self.project.uuid, env_uuid=env.uuid)

        # Update or add env var
        env_vars = list(env.env_vars or [])
        updated = False
        for var in env_vars:
            if var['key'] == key:
                var['value'] = value
                updated = True
                break

        if not updated:
            env_vars.append({'key': key, 'value': value})

        env.env_vars = env_vars
        env.save(update_fields=['env_vars', 'updated_at'])
        messages.success(request, f'Variable "{key}" saved.')

        # Return to environment detail
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('projects:environment_detail',
                                          kwargs={'project_uuid': self.project.uuid,
                                                 'env_uuid': env.uuid})
        return response


class EnvVarDeleteView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Delete an environment-level env var."""

    def delete(self, request, *args, **kwargs):
        env = get_object_or_404(
            Environment, uuid=kwargs.get('env_uuid'), project=self.project
        )
        key = kwargs.get('key')
        env_vars = [v for v in (env.env_vars or []) if v['key'] != key]
        env.env_vars = env_vars
        env.save(update_fields=['env_vars', 'updated_at'])
        return HttpResponse(status=200)  # HTMX will remove the element


# ============================================================================
# Connection Attachment Views
# ============================================================================

class ProjectAttachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Attach a connection to a project."""

    def get(self, request, *args, **kwargs):
        existing_ids = self.project.connections.values_list('connection_id', flat=True)
        form = AttachConnectionForm(category='scm', exclude_ids=list(existing_ids))

        return render(request, 'core/connections/_attach_modal.html', {
            'form': form,
            'project': self.project,
            'title': 'Attach SCM Connection',
            'action_url': request.path,
        })

    def post(self, request, *args, **kwargs):
        existing_ids = self.project.connections.values_list('connection_id', flat=True)
        form = AttachConnectionForm(request.POST, category='scm', exclude_ids=list(existing_ids))

        if form.is_valid():
            ProjectConnection.objects.create(
                project=self.project,
                connection=form.cleaned_data['connection'],
                is_default=form.cleaned_data.get('is_default', False),
                created_by=request.user.username,
            )
            messages.success(request, 'Connection attached successfully.')

        if request.headers.get('HX-Request'):
            # Return updated connections list partial
            return render(request, 'core/projects/_connections_list.html', {
                'project': self.project,
                'connections': self.project.connections.select_related('connection').all(),
                'user_project_role': self.user_project_role,
            })

        return redirect('projects:detail', project_uuid=self.project.uuid)


class ProjectDetachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Detach a connection from a project."""

    def post(self, request, *args, **kwargs):
        connection_id = kwargs.get('connection_id')
        attachment = get_object_or_404(ProjectConnection, project=self.project, connection_id=connection_id)

        # TODO: Check if any services use this connection (Phase 5+)
        # For now, allow detachment

        attachment.delete()
        messages.success(request, 'Connection detached.')

        if request.headers.get('HX-Request'):
            return render(request, 'core/projects/_connections_list.html', {
                'project': self.project,
                'connections': self.project.connections.select_related('connection').all(),
                'user_project_role': self.user_project_role,
            })

        return redirect('projects:detail', project_uuid=self.project.uuid)


class EnvironmentAttachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Attach a deploy connection to an environment."""

    def get(self, request, *args, **kwargs):
        environment = get_object_or_404(Environment, uuid=kwargs.get('env_uuid'), project=self.project)
        existing_ids = environment.connections.values_list('connection_id', flat=True)
        form = AttachConnectionForm(category='deploy', exclude_ids=list(existing_ids))

        return render(request, 'core/connections/_attach_modal.html', {
            'form': form,
            'environment': environment,
            'project': self.project,
            'title': 'Attach Deploy Connection',
            'action_url': request.path,
        })

    def post(self, request, *args, **kwargs):
        environment = get_object_or_404(Environment, uuid=kwargs.get('env_uuid'), project=self.project)
        existing_ids = environment.connections.values_list('connection_id', flat=True)
        form = AttachConnectionForm(request.POST, category='deploy', exclude_ids=list(existing_ids))

        if form.is_valid():
            EnvironmentConnection.objects.create(
                environment=environment,
                connection=form.cleaned_data['connection'],
                is_default=form.cleaned_data.get('is_default', False),
                created_by=request.user.username,
            )
            messages.success(request, 'Connection attached successfully.')

        if request.headers.get('HX-Request'):
            return render(request, 'core/projects/_env_connections_list.html', {
                'environment': environment,
                'project': self.project,
                'connections': environment.connections.select_related('connection').all(),
                'user_project_role': self.user_project_role,
            })

        return redirect('projects:environment_detail', project_uuid=self.project.uuid, env_uuid=environment.uuid)


class EnvironmentDetachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Detach a connection from an environment."""

    def post(self, request, *args, **kwargs):
        environment = get_object_or_404(Environment, uuid=kwargs.get('env_uuid'), project=self.project)
        connection_id = kwargs.get('connection_id')
        attachment = get_object_or_404(EnvironmentConnection, environment=environment, connection_id=connection_id)

        attachment.delete()
        messages.success(request, 'Connection detached.')

        if request.headers.get('HX-Request'):
            return render(request, 'core/projects/_env_connections_list.html', {
                'environment': environment,
                'project': self.project,
                'connections': environment.connections.select_related('connection').all(),
                'user_project_role': self.user_project_role,
            })

        return redirect('projects:environment_detail', project_uuid=self.project.uuid, env_uuid=environment.uuid)
