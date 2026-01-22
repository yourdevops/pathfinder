from django.views.generic import ListView, CreateView, TemplateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.contrib import messages
from django_htmx.http import HttpResponseClientRedirect

from core.models import Project, Environment, ProjectMembership, Group
from core.forms import ProjectCreateForm, ProjectUpdateForm, EnvironmentForm, AddProjectMemberForm
from core.decorators import AdminRequiredMixin
from core.permissions import ProjectViewerMixin, ProjectContributorMixin, ProjectOwnerMixin


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
        context['environment'] = get_object_or_404(
            Environment, uuid=kwargs.get('env_uuid'), project=self.project
        )
        return context


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
