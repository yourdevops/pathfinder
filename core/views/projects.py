import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, View

from core.decorators import AdminRequiredMixin
from core.forms import (
    AddProjectMemberForm,
    AttachConnectionForm,
    EnvironmentForm,
    ProjectCreateForm,
    ProjectUpdateForm,
)
from core.forms.ci_workflows import ApproveWorkflowForm, ProjectCIConfigForm
from core.models import (
    CIWorkflow,
    Environment,
    EnvironmentConnection,
    Group,
    Project,
    ProjectApprovedWorkflow,
    ProjectCIConfig,
    ProjectConnection,
    ProjectMembership,
)
from core.permissions import (
    ProjectContributorMixin,
    ProjectOwnerMixin,
    ProjectViewerMixin,
)
from core.utils import resolve_env_vars


class ProjectListView(LoginRequiredMixin, ListView):
    """List all active/inactive projects with environment counts."""

    model = Project
    template_name = "core/projects/list.html"
    context_object_name = "projects"

    def get_queryset(self):
        # Annotate with environment count to avoid N+1 queries
        return (
            Project.objects.filter(status__in=["active", "inactive"])
            .annotate(env_count=Count("environments"))
            .order_by("name")
        )


class ProjectCreateModalView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Render the create project modal form."""

    template_name = "core/projects/create_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ProjectCreateForm()
        return context


class ProjectCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Handle project creation from modal form."""

    model = Project
    form_class = ProjectCreateForm
    template_name = "core/projects/create_modal.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username
        self.object = form.save()
        # Redirect to project list
        # Note: projects:detail URL doesn't exist until Plan 03
        # Once Plan 03 is complete, redirect can be updated to project detail
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("projects:list")
        return response

    def form_invalid(self, form):
        # Re-render modal with errors
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(vary_on_headers("HX-Request"), name="dispatch")
class ProjectDetailView(LoginRequiredMixin, ProjectViewerMixin, TemplateView):
    """Project detail with HTMX tab navigation."""

    def get_template_names(self):
        tab = self.request.GET.get("tab", "services")
        # Validate tab name to prevent path traversal
        valid_tabs = ["services", "environments", "settings"]
        if tab not in valid_tabs:
            tab = "services"
        if self.request.htmx:  # type: ignore[attr-defined]
            return [f"core/projects/_{tab}_tab.html"]
        return ["core/projects/detail.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get("tab", "services")
        valid_tabs = ["services", "environments", "settings"]
        if tab not in valid_tabs:
            tab = "services"
        context["active_tab"] = tab

        # Tab-specific data
        if tab == "services":
            context["services"] = self.project.services.order_by("name")
        elif tab == "environments":
            context["environments"] = self.project.environments.filter(status="active").order_by("order", "name")
        elif tab == "settings":
            # Initialize form with CI config values
            ci_config: ProjectCIConfig | None
            try:
                ci_config = self.project.ci_config
                initial = {
                    "approve_all_published": ci_config.approve_all_published,
                    "default_workflow": ci_config.default_workflow,
                }
            except ProjectCIConfig.DoesNotExist:
                ci_config = None
                initial = {
                    "approve_all_published": False,
                    "default_workflow": None,
                }
            context["form"] = ProjectUpdateForm(instance=self.project, project=self.project, initial=initial)
            # Members context (merged from members tab)
            memberships = self.project.memberships.select_related("group").order_by("project_role")
            context["memberships"] = memberships
            context["owners"] = [m for m in memberships if m.project_role == "owner"]
            context["contributors"] = [m for m in memberships if m.project_role == "contributor"]
            context["viewers"] = [m for m in memberships if m.project_role == "viewer"]
            context["ci_config"] = ci_config
            context["ci_config_form"] = ProjectCIConfigForm(
                project=self.project,
                initial={
                    "default_workflow": ci_config.default_workflow if ci_config else None,
                    "approve_all_published": ci_config.approve_all_published if ci_config else False,
                },
            )
            context["approved_workflows"] = self.project.approved_workflows.select_related("workflow").order_by(
                "workflow__name"
            )
            already_approved_ids = self.project.approved_workflows.values_list("workflow_id", flat=True)
            context["available_workflows"] = CIWorkflow.objects.filter(status="published").exclude(
                id__in=already_approved_ids
            )
            context["approve_workflow_form"] = ApproveWorkflowForm(project=self.project)

            # Env vars resolved cascade for unified component
            resolved_vars = resolve_env_vars(self.project)
            context["resolved_vars"] = resolved_vars
            context["is_editable_env_vars"] = self.user_project_role == "owner"
            context["current_level_vars_json"] = json.dumps(self.project.env_vars or [])
            context["env_var_bulk_save_url"] = reverse(
                "projects:project_env_var_bulk_save", kwargs={"project_name": self.project.name}
            )
            context["upstream_var_count"] = sum(1 for v in resolved_vars if v["source"] != "project")

        return context


class ProjectUpdateView(LoginRequiredMixin, ProjectOwnerMixin, UpdateView):
    """Update project settings including CI configuration."""

    model = Project
    form_class = ProjectUpdateForm
    template_name = "core/projects/_settings_tab.html"

    def get_object(self, queryset=None):
        return self.project

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.project
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        # Set CI config initial values
        try:
            ci_config = self.project.ci_config
            initial["approve_all_published"] = ci_config.approve_all_published
            initial["default_workflow"] = ci_config.default_workflow
        except ProjectCIConfig.DoesNotExist:
            initial["approve_all_published"] = False
            initial["default_workflow"] = None
        return initial

    def get_success_url(self):
        return reverse("projects:detail", kwargs={"project_name": self.project.name}) + "?tab=settings"

    def form_valid(self, form):
        response = super().form_valid(form)
        # Save CI configuration
        ci_config, _ = ProjectCIConfig.objects.get_or_create(project=self.project)
        ci_config.approve_all_published = form.cleaned_data.get("approve_all_published", False)
        ci_config.default_workflow = form.cleaned_data.get("default_workflow")
        ci_config.save()
        messages.success(self.request, "Project settings updated.")
        return response


class ProjectArchiveView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Archive a project."""

    def post(self, request, *args, **kwargs):
        self.project.status = "archived"
        self.project.save()
        messages.success(request, f'Project "{self.project.name}" has been archived.')
        return redirect("projects:list")


class EnvironmentCreateView(LoginRequiredMixin, ProjectContributorMixin, TemplateView):
    """Create a new environment."""

    template_name = "core/projects/environment_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = EnvironmentForm()
        return context

    def post(self, request, *args, **kwargs):
        form = EnvironmentForm(request.POST)
        if form.is_valid():
            env = form.save(commit=False)
            env.project = self.project
            with transaction.atomic():
                # Lock project row to serialize first-default assignment
                Project.objects.select_for_update().filter(pk=self.project.pk).first()  # advisory lock
                if not self.project.environments.exists():
                    env.is_default = True
                env.save()
            messages.success(request, f'Environment "{env.name}" created.')
            return redirect("projects:detail", project_name=self.project.name)
        return self.render_to_response(self.get_context_data(form=form))


class EnvironmentDetailView(LoginRequiredMixin, ProjectViewerMixin, TemplateView):
    """View/edit environment details."""

    template_name = "core/projects/environment_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        env = get_object_or_404(Environment, name=kwargs.get("env_name"), project=self.project)
        context["environment"] = env
        context["form"] = EnvironmentForm(instance=env)
        # Resolved cascade via unified resolve_env_vars
        resolved_vars = resolve_env_vars(self.project, environment=env)
        context["resolved_vars"] = resolved_vars
        context["is_editable_env_vars"] = self.user_project_role in ("contributor", "owner")
        context["current_level_vars_json"] = json.dumps(env.env_vars or [])
        context["env_var_bulk_save_url"] = reverse(
            "projects:env_env_var_bulk_save",
            kwargs={"project_name": self.project.name, "env_name": env.name},
        )
        context["upstream_var_count"] = sum(1 for v in resolved_vars if v["source"] != "environment")
        return context


class EnvironmentUpdateView(LoginRequiredMixin, ProjectContributorMixin, View):
    """Update environment settings."""

    def post(self, request, *args, **kwargs):
        env = get_object_or_404(Environment, name=kwargs.get("env_name"), project=self.project)
        form = EnvironmentForm(request.POST, instance=env)
        if form.is_valid():
            with transaction.atomic():
                # Handle is_default - ensure only one default
                if form.cleaned_data.get("is_default"):
                    Project.objects.select_for_update().filter(pk=self.project.pk).first()  # advisory lock
                    Environment.objects.filter(project=self.project, is_default=True).exclude(pk=env.pk).update(
                        is_default=False
                    )
                form.save()
            messages.success(request, f'Environment "{env.name}" updated.')
            return redirect(
                "projects:environment_detail",
                project_name=self.project.name,
                env_name=env.name,
            )
        # Re-render with errors
        return render(
            request,
            "core/projects/environment_detail.html",
            {
                "project": self.project,
                "environment": env,
                "form": form,
                "user_project_role": self.user_project_role,
            },
        )


class EnvironmentDeleteView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Delete an environment."""

    def post(self, request, *args, **kwargs):
        env = get_object_or_404(Environment, name=kwargs.get("env_name"), project=self.project)
        env_name = env.name
        with transaction.atomic():
            Project.objects.select_for_update().filter(pk=self.project.pk).first()  # advisory lock
            was_default = env.is_default
            env.delete()

            # If deleted env was default, make another one default
            if was_default:
                next_env = self.project.environments.first()
                if next_env:
                    next_env.is_default = True
                    next_env.save()

        messages.success(request, f'Environment "{env_name}" deleted.')
        return redirect("projects:detail", project_name=self.project.name)


class AddMemberModalView(LoginRequiredMixin, ProjectOwnerMixin, TemplateView):
    """Modal for adding a group to project."""

    template_name = "core/projects/add_member_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get groups not already in this project
        existing_group_ids = self.project.memberships.values_list("group_id", flat=True)
        context["form"] = AddProjectMemberForm(existing_group_ids=existing_group_ids)
        return context

    def post(self, request, *args, **kwargs):
        existing_group_ids = self.project.memberships.values_list("group_id", flat=True)
        form = AddProjectMemberForm(request.POST, existing_group_ids=existing_group_ids)
        if form.is_valid():
            ProjectMembership.objects.create(
                project=self.project,
                group=form.cleaned_data["group"],
                project_role=form.cleaned_data["project_role"],
                added_by=request.user.username,
            )
            messages.success(request, f'Group "{form.cleaned_data["group"].name}" added to project.')
            response = HttpResponse(status=204)
            response["HX-Redirect"] = (
                reverse("projects:detail", kwargs={"project_name": self.project.name}) + "?tab=settings"
            )
            return response
        return self.render_to_response(self.get_context_data(form=form))


class RemoveMemberView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Remove a group from project."""

    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, name=kwargs.get("group_name"))
        membership = get_object_or_404(ProjectMembership, project=self.project, group=group)
        membership.delete()
        messages.success(request, f'Group "{group.name}" removed from project.')
        return redirect(reverse("projects:detail", kwargs={"project_name": self.project.name}) + "?tab=settings")


# ============================================================================
# Connection Attachment Views
# ============================================================================


class ProjectAttachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Attach a connection to a project."""

    def get(self, request, *args, **kwargs):
        existing_ids = self.project.connections.values_list("connection_id", flat=True)
        form = AttachConnectionForm(category="scm", exclude_ids=list(existing_ids))

        return render(
            request,
            "core/connections/_attach_modal.html",
            {
                "form": form,
                "project": self.project,
                "title": "Attach SCM Connection",
                "action_url": request.path,
            },
        )

    def post(self, request, *args, **kwargs):
        existing_ids = self.project.connections.values_list("connection_id", flat=True)
        form = AttachConnectionForm(request.POST, category="scm", exclude_ids=list(existing_ids))

        if form.is_valid():
            ProjectConnection.objects.create(
                project=self.project,
                connection=form.cleaned_data["connection"],
                is_default=form.cleaned_data.get("is_default", False),
                created_by=request.user.username,
            )
            messages.success(request, "Connection attached successfully.")

        if request.headers.get("HX-Request"):
            response = render(
                request,
                "core/projects/_connections_list.html",
                {
                    "project": self.project,
                    "connections": self.project.connections.select_related("connection").all(),
                    "user_project_role": self.user_project_role,
                },
            )
            response["HX-Trigger"] = "closeModal"
            return response

        return redirect("projects:detail", project_name=self.project.name)


class ProjectDetachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Detach a connection from a project."""

    def post(self, request, *args, **kwargs):
        connection_id = kwargs.get("connection_id")
        attachment = get_object_or_404(ProjectConnection, project=self.project, connection_id=connection_id)

        # TODO: Check if any services use this connection (Phase 5+)
        # For now, allow detachment

        attachment.delete()
        messages.success(request, "Connection detached.")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "core/projects/_connections_list.html",
                {
                    "project": self.project,
                    "connections": self.project.connections.select_related("connection").all(),
                    "user_project_role": self.user_project_role,
                },
            )

        return redirect("projects:detail", project_name=self.project.name)


class EnvironmentAttachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Attach a deploy connection to an environment."""

    def get(self, request, *args, **kwargs):
        environment = get_object_or_404(Environment, name=kwargs.get("env_name"), project=self.project)
        existing_ids = environment.connections.values_list("connection_id", flat=True)
        form = AttachConnectionForm(category="deploy", exclude_ids=list(existing_ids))

        return render(
            request,
            "core/connections/_attach_modal.html",
            {
                "form": form,
                "environment": environment,
                "project": self.project,
                "title": "Attach Deploy Connection",
                "action_url": request.path,
            },
        )

    def post(self, request, *args, **kwargs):
        environment = get_object_or_404(Environment, name=kwargs.get("env_name"), project=self.project)
        existing_ids = environment.connections.values_list("connection_id", flat=True)
        form = AttachConnectionForm(request.POST, category="deploy", exclude_ids=list(existing_ids))

        if form.is_valid():
            EnvironmentConnection.objects.create(
                environment=environment,
                connection=form.cleaned_data["connection"],
                is_default=form.cleaned_data.get("is_default", False),
                created_by=request.user.username,
            )
            messages.success(request, "Connection attached successfully.")

        if request.headers.get("HX-Request"):
            response = render(
                request,
                "core/projects/_env_connections_list.html",
                {
                    "environment": environment,
                    "project": self.project,
                    "connections": environment.connections.select_related("connection").all(),
                    "user_project_role": self.user_project_role,
                },
            )
            response["HX-Trigger"] = "closeModal"
            return response

        return redirect(
            "projects:environment_detail",
            project_name=self.project.name,
            env_name=environment.name,
        )


class EnvironmentDetachConnectionView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Detach a connection from an environment."""

    def post(self, request, *args, **kwargs):
        environment = get_object_or_404(Environment, name=kwargs.get("env_name"), project=self.project)
        connection_id = kwargs.get("connection_id")
        attachment = get_object_or_404(EnvironmentConnection, environment=environment, connection_id=connection_id)

        attachment.delete()
        messages.success(request, "Connection detached.")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "core/projects/_env_connections_list.html",
                {
                    "environment": environment,
                    "project": self.project,
                    "connections": environment.connections.select_related("connection").all(),
                    "user_project_role": self.user_project_role,
                },
            )

        return redirect(
            "projects:environment_detail",
            project_name=self.project.name,
            env_name=environment.name,
        )


# ============================================================================
# Project CI Configuration Views
# ============================================================================


def _render_approved_workflows_section(request, project, user_project_role):
    """Helper to render the approved workflows partial for HTMX responses."""
    try:
        ci_config = project.ci_config
    except ProjectCIConfig.DoesNotExist:
        ci_config = None

    approved_workflows = project.approved_workflows.select_related("workflow").order_by("workflow__name")
    already_approved_ids = project.approved_workflows.values_list("workflow_id", flat=True)

    context = {
        "project": project,
        "user_project_role": user_project_role,
        "ci_config": ci_config,
        "approved_workflows": approved_workflows,
        "available_workflows": CIWorkflow.objects.filter(status="published").exclude(id__in=already_approved_ids),
        "approve_workflow_form": ApproveWorkflowForm(project=project),
    }
    return render(request, "core/projects/_approved_workflows_section.html", context)


class ProjectCIConfigView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Update project CI configuration (default workflow, approve-all toggle)."""

    def post(self, request, *args, **kwargs):
        ci_config, _ = ProjectCIConfig.objects.get_or_create(project=self.project)

        form = ProjectCIConfigForm(request.POST, project=self.project)
        if form.is_valid():
            ci_config.default_workflow = form.cleaned_data["default_workflow"]
            ci_config.approve_all_published = form.cleaned_data["approve_all_published"]
            ci_config.save()
            messages.success(request, "CI configuration updated.")

        return _render_approved_workflows_section(request, self.project, self.user_project_role)


class ProjectApproveWorkflowView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Add a workflow to the project's approved list."""

    def post(self, request, *args, **kwargs):
        form = ApproveWorkflowForm(request.POST, project=self.project)
        if form.is_valid():
            workflow = form.cleaned_data["workflow"]
            ProjectApprovedWorkflow.objects.get_or_create(
                project=self.project,
                workflow=workflow,
                defaults={"approved_by": request.user.username},
            )
            messages.success(request, f'Workflow "{workflow.name}" approved.')

        return _render_approved_workflows_section(request, self.project, self.user_project_role)


class ProjectUpdateCIConfigView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Update project CI configuration settings (e.g., Allow Drafts toggle)."""

    def post(self, request, *args, **kwargs):
        ci_config, _ = ProjectCIConfig.objects.get_or_create(project=self.project)

        setting = request.POST.get("setting", "")
        if setting == "allow_draft_workflows":
            ci_config.allow_draft_workflows = request.POST.get("allow_draft_workflows") == "true"
            ci_config.save(update_fields=["allow_draft_workflows"])
            messages.success(request, "Draft workflows setting updated.")

        return redirect("projects:detail", project_name=self.project.name)


class ProjectRemoveApprovedWorkflowView(LoginRequiredMixin, ProjectOwnerMixin, View):
    """Remove a workflow from the project's approved list."""

    def delete(self, request, *args, **kwargs):
        workflow_id = kwargs.get("workflow_id")
        ProjectApprovedWorkflow.objects.filter(project=self.project, workflow_id=workflow_id).delete()

        # If the removed workflow was the default, clear it
        try:
            ci_config = self.project.ci_config
            if ci_config.default_workflow_id == workflow_id:
                ci_config.default_workflow = None
                ci_config.save()
        except ProjectCIConfig.DoesNotExist:
            pass

        return _render_approved_workflows_section(request, self.project, self.user_project_role)
