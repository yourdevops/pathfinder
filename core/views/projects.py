from django.views.generic import ListView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse
from django.http import HttpResponse

from core.models import Project
from core.forms import ProjectCreateForm
from core.decorators import AdminRequiredMixin


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
