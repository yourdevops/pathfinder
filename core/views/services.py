"""Service views including creation wizard and detail pages."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.views.generic import ListView, TemplateView, View
from formtools.wizard.views import SessionWizardView

from core.forms.services import (
    ConfigurationStepForm,
    ProjectStepForm,
    RepositoryStepForm,
    ReviewStepForm,
    WorkflowSelectionForm,
)
from core.models import (
    Build,
    GroupMembership,
    Project,
    ProjectMembership,
    Service,
    get_available_workflows_for_project,
)
from core.permissions import can_access_project, get_user_project_role, has_system_role
from core.tasks import scaffold_repository
from plugins.base import get_ci_plugin_for_engine


class ServiceListView(LoginRequiredMixin, ListView):
    """List all services the user has access to."""

    model = Service
    template_name = "core/services/list.html"
    context_object_name = "services"

    def get_queryset(self):
        user = self.request.user
        # Admin/superusers or system admins/operators see all services
        if user.is_superuser or user.is_staff or has_system_role(user, ["admin", "operator"]):
            return Service.objects.select_related("project").order_by("-created_at")

        # Regular users see services from projects they have access to
        # Get user's group IDs
        user_group_ids = GroupMembership.objects.filter(user=user, group__status="active").values_list(
            "group_id", flat=True
        )

        # Get project IDs where user has membership via their groups
        accessible_project_ids = ProjectMembership.objects.filter(group_id__in=user_group_ids).values_list(
            "project_id", flat=True
        )

        return (
            Service.objects.filter(project_id__in=accessible_project_ids)
            .select_related("project")
            .order_by("-created_at")
        )


WIZARD_FORMS = [
    ("project", ProjectStepForm),
    ("repository", RepositoryStepForm),
    ("workflow", WorkflowSelectionForm),
    ("configuration", ConfigurationStepForm),
    ("review", ReviewStepForm),
]

WIZARD_TEMPLATES = {
    "project": "core/services/wizard/step_project.html",
    "repository": "core/services/wizard/step_repository.html",
    "workflow": "core/services/wizard/step_workflow.html",
    "configuration": "core/services/wizard/step_configuration.html",
    "review": "core/services/wizard/step_review.html",
}

STEP_TITLES = {
    "project": "Service",
    "repository": "Repository",
    "workflow": "CI Workflow",
    "configuration": "Configuration",
    "review": "Review",
}


class ServiceCreateWizard(LoginRequiredMixin, SessionWizardView):
    """5-step service creation wizard (project, repository, configuration, workflow, review)."""

    form_list = WIZARD_FORMS

    def dispatch(self, request, *args, **kwargs):
        # Get project from URL if provided
        project_name = kwargs.get("project_name")
        if project_name:
            self.project = get_object_or_404(Project, name=project_name, status="active")
            # Check contributor permission
            access = can_access_project(request.user, self.project)
            if not access or access == "viewer":
                messages.error(
                    request,
                    "You don't have permission to create services in this project.",
                )
                return redirect("projects:detail", project_name=project_name)
        else:
            self.project = None

        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [WIZARD_TEMPLATES[self.steps.current]]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)

        if step == "project":
            kwargs["project"] = self.project

        elif step == "repository":
            # Pass project from step 1
            project_data = self.get_cleaned_data_for_step("project")
            if project_data:
                kwargs["project"] = project_data.get("project") or self.project

        elif step == "configuration":
            # Pass project and service name for env var inheritance display
            project_data = self.get_cleaned_data_for_step("project")
            if project_data:
                kwargs["project"] = project_data.get("project") or self.project
                kwargs["service_name"] = project_data.get("name")

        elif step == "workflow":
            project_data = self.get_cleaned_data_for_step("project")
            if project_data:
                kwargs["project"] = project_data.get("project") or self.project

        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)

        # Step metadata for progress bar
        context["steps"] = [
            {
                "key": key,
                "title": STEP_TITLES[key],
                "is_current": key == self.steps.current,
                "index": i,
            }
            for i, (key, _) in enumerate(WIZARD_FORMS)
        ]
        context["current_step_index"] = self.steps.index
        context["step_title"] = STEP_TITLES[self.steps.current]

        # Project context
        context["project"] = self.project

        # Step-specific context
        if self.steps.current == "repository":
            # Preview repo name
            project_data = self.get_cleaned_data_for_step("project")
            if project_data:
                project = project_data.get("project") or self.project
                service_name = project_data.get("name")
                if project and service_name:
                    context["preview_repo_name"] = f"{project.name}-{service_name}"

        elif self.steps.current == "configuration":
            # Show inherited project vars
            project_data = self.get_cleaned_data_for_step("project")
            if project_data:
                project = project_data.get("project") or self.project
                service_name = project_data.get("name")
                context["project_env_vars"] = project.env_vars or [] if project else []
                context["service_name"] = service_name
                # Default SERVICE_NAME variable (locked)
                context["default_service_var"] = {
                    "key": "SERVICE_NAME",
                    "value": service_name,
                    "lock": True,
                }

        elif self.steps.current == "workflow":
            # Add workflow list and detail context for step 3
            project_data = self.get_cleaned_data_for_step("project")
            if project_data:
                project = project_data.get("project") or self.project
                context["available_workflows"] = get_available_workflows_for_project(project)

        elif self.steps.current == "review":
            # Compile all data for review
            context["review_data"] = self._get_review_data()

        return context

    def _get_review_data(self):
        """Compile all wizard data for review step."""
        project_data = self.get_cleaned_data_for_step("project") or {}
        repository_data = self.get_cleaned_data_for_step("repository") or {}
        config_data = self.get_cleaned_data_for_step("configuration") or {}
        workflow_data = self.get_cleaned_data_for_step("workflow") or {}

        project = project_data.get("project") or self.project
        service_name = project_data.get("name")
        ci_workflow = workflow_data.get("ci_workflow")

        return {
            "project": project,
            "service_name": service_name,
            "handler": f"{project.name}-{service_name}" if project and service_name else "",
            "scm_connection": repository_data.get("scm_connection"),
            "repo_mode": repository_data.get("repo_mode"),
            "repo_mode_display": "New repository"
            if repository_data.get("repo_mode") == "new"
            else "Existing repository",
            "existing_repo_url": repository_data.get("existing_repo_url"),
            "branch": repository_data.get("branch"),
            "env_vars": config_data.get("env_vars_json", []),
            "ci_workflow": ci_workflow,
            "ci_workflow_name": ci_workflow.name if ci_workflow else "None",
        }

    def done(self, form_list, form_dict, **kwargs):
        """Create service and trigger repository scaffolding."""
        # Extract data from all forms
        project_data = form_dict["project"].cleaned_data
        repository_data = form_dict["repository"].cleaned_data
        config_data = form_dict["configuration"].cleaned_data

        project = project_data.get("project") or self.project
        service_name = project_data["name"]

        scm_connection = repository_data["scm_connection"]
        repo_mode = repository_data["repo_mode"]
        existing_repo_url = repository_data.get("existing_repo_url", "")
        branch = repository_data["branch"]

        env_vars = config_data.get("env_vars_json", [])

        # Add default SERVICE_NAME variable (locked)
        env_vars = [{"key": "SERVICE_NAME", "value": service_name, "lock": True}] + [
            v for v in env_vars if v.get("key") != "SERVICE_NAME"
        ]

        # Determine repo URL
        if repo_mode == "new":
            # Will be set by scaffolding task after repo creation
            repo_url = ""
            repo_is_new = True
        else:
            repo_url = existing_repo_url
            repo_is_new = False

        # Get workflow selection
        workflow_data = form_dict["workflow"].cleaned_data
        ci_workflow = workflow_data.get("ci_workflow")

        # Determine if scaffolding is needed:
        # - NEW repos: always scaffold (to create the repo), CI manifest optional
        # - EXISTING repos: only scaffold if CI workflow selected (to push manifest via PR)
        needs_scaffold = repo_is_new or ci_workflow
        scaffold_status = "pending" if needs_scaffold else "not_required"

        service = Service.objects.create(
            project=project,
            name=service_name,
            repo_url=repo_url,
            repo_branch=branch,
            repo_is_new=repo_is_new,
            env_vars=env_vars,
            ci_workflow=ci_workflow,
            status="draft",
            scaffold_status=scaffold_status,
            created_by=self.request.user.username,
        )

        if needs_scaffold:
            scaffold_repository.enqueue(
                service_id=service.id,
                scm_connection_id=scm_connection.connection.id,
            )
            if repo_is_new:
                if ci_workflow:
                    msg = f'Service "{service_name}" created. Repository scaffolding with CI workflow in progress...'
                else:
                    msg = f'Service "{service_name}" created. Repository creation in progress...'
            else:
                msg = f'Service "{service_name}" created. CI manifest scaffolding in progress...'
            messages.success(self.request, msg)
        else:
            messages.success(
                self.request,
                f'Service "{service_name}" created. You can assign a CI Workflow later to push a manifest.',
            )

        return redirect("projects:detail", project_name=project.name)


@method_decorator(vary_on_headers("HX-Request"), name="dispatch")
class ServiceDetailView(LoginRequiredMixin, TemplateView):
    """Service detail with HTMX tab navigation."""

    def dispatch(self, request, *args, **kwargs):
        # Get project and service from URL
        project_name = kwargs.get("project_name")
        service_name = kwargs.get("service_name")

        self.project = get_object_or_404(Project, name=project_name, status="active")
        self.service = get_object_or_404(Service, project=self.project, name=service_name)

        # Check viewer permission
        self.user_project_role = get_user_project_role(request.user, self.project)
        if not self.user_project_role or not can_access_project(request.user, self.project):
            messages.error(request, "You don't have permission to view this service.")
            return redirect("projects:list")

        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        tab = self.request.GET.get("tab", "details")
        valid_tabs = ["details", "ci", "builds", "environments", "settings"]
        if tab not in valid_tabs:
            tab = "details"

        if self.request.htmx:
            return [f"core/services/_{tab}_tab.html"]
        return ["core/services/detail.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get("tab", "details")
        valid_tabs = ["details", "ci", "builds", "environments", "settings"]
        if tab not in valid_tabs:
            tab = "details"

        context["project"] = self.project
        context["service"] = self.service
        context["active_tab"] = tab
        context["user_project_role"] = self.user_project_role
        # Pass tab template path for include (avoids invalid Django filter concatenation)
        context["tab_template"] = f"core/services/_{tab}_tab.html"

        # Tab-specific context
        if tab == "details":
            # Get merged env vars for display
            context["merged_env_vars"] = self.service.get_merged_env_vars()
            # Can edit if contributor or owner
            context["can_edit"] = self.user_project_role in ("contributor", "owner")

        elif tab == "ci":
            # CI Workflow tab context
            context["ci_workflow"] = self.service.ci_workflow
            context["ci_manifest_status"] = self.service.ci_manifest_status
            context["ci_manifest_out_of_date"] = self.service.ci_manifest_out_of_date
            context["ci_manifest_pr_url"] = self.service.ci_manifest_pr_url
            context["ci_manifest_pushed_at"] = self.service.ci_manifest_pushed_at
            context["available_workflows"] = get_available_workflows_for_project(self.project)
            context["can_edit"] = self.user_project_role in ("contributor", "owner")
            # Generate manifest preview if workflow is assigned
            if self.service.ci_workflow:
                first_step = self.service.ci_workflow.workflow_steps.select_related("step").first()
                engine = first_step.step.engine if first_step else "github_actions"
                ci_plugin = get_ci_plugin_for_engine(engine)
                context["manifest_yaml"] = (
                    ci_plugin.generate_manifest(self.service.ci_workflow) if ci_plugin else "# No CI plugin available"
                )
            else:
                context["manifest_yaml"] = None

        elif tab == "builds":
            # Get builds for this service
            builds_qs = Build.objects.filter(service=self.service).order_by("-created_at")

            # Apply status filter if provided
            status_filter = self.request.GET.get("status", "all")
            if status_filter and status_filter != "all":
                builds_qs = builds_qs.filter(status=status_filter)

            # Paginate (20 per page per CONTEXT.md)
            paginator = Paginator(builds_qs, 20)
            page_number = self.request.GET.get("page", 1)
            page_obj = paginator.get_page(page_number)

            context["builds"] = page_obj
            context["page_obj"] = page_obj
            context["status_filter"] = status_filter
            context["status_choices"] = [
                ("all", "All"),
                ("running", "Running"),
                ("success", "Success"),
                ("failed", "Failed"),
            ]

            # Check if any builds are in progress (for auto-refresh)
            context["has_running_builds"] = Build.objects.filter(
                service=self.service, status__in=["pending", "running"]
            ).exists()

            # Empty state check
            context["has_any_builds"] = Build.objects.filter(service=self.service).exists()

        elif tab == "environments":
            # Show environments with deployment info (placeholder for Phase 7)
            context["environments"] = self.project.environments.filter(status="active").order_by("order", "name")

        elif tab == "settings":
            context["merged_env_vars"] = self.service.get_merged_env_vars()
            context["can_edit"] = self.user_project_role in ("contributor", "owner")

        return context


class ServiceDeleteView(LoginRequiredMixin, View):
    """Delete a service (owner only)."""

    def dispatch(self, request, *args, **kwargs):
        project_name = kwargs.get("project_name")
        service_name = kwargs.get("service_name")

        self.project = get_object_or_404(Project, name=project_name, status="active")
        self.service = get_object_or_404(Service, project=self.project, name=service_name)

        # Check owner permission
        role = get_user_project_role(request.user, self.project)
        if role != "owner":
            messages.error(request, "Only project owners can delete services.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        service_name = self.service.name
        project_name = self.project.name

        # TODO: Consider cleanup of repository if we created it (future enhancement)
        self.service.delete()

        messages.success(request, f'Service "{service_name}" has been deleted.')
        return redirect("projects:detail", project_name=project_name)


class ServiceScaffoldStatusView(LoginRequiredMixin, View):
    """HTMX endpoint to poll scaffold status."""

    def get(self, request, project_name, service_name):
        project = get_object_or_404(Project, name=project_name)
        service = get_object_or_404(Service, project=project, name=service_name)

        # Return status badge HTML
        status_classes = {
            "pending": "bg-gray-500/20 text-gray-300",
            "running": "bg-blue-500/20 text-blue-300",
            "success": "bg-green-500/20 text-green-300",
            "failed": "bg-red-500/20 text-red-300",
        }

        status_class = status_classes.get(service.scaffold_status, "bg-gray-500/20 text-gray-300")
        status_label = service.get_scaffold_status_display()

        if service.scaffold_status in ("pending", "running"):
            html = f'''<span class="px-2 py-1 text-xs rounded {status_class}"
                      hx-get="{request.path}"
                      hx-trigger="every 3s"
                      hx-swap="outerHTML">Scaffold: {status_label}</span>'''
        else:
            html = f'<span class="px-2 py-1 text-xs rounded {status_class}">Scaffold: {status_label}</span>'

        return HttpResponse(html)


class ServiceAssignWorkflowView(LoginRequiredMixin, View):
    """Assign or change the CI Workflow for a service."""

    def dispatch(self, request, *args, **kwargs):
        project_name = kwargs.get("project_name")
        service_name = kwargs.get("service_name")

        self.project = get_object_or_404(Project, name=project_name, status="active")
        self.service = get_object_or_404(Service, project=self.project, name=service_name)

        # Check contributor permission
        role = can_access_project(request.user, self.project)
        if not role or role == "viewer":
            messages.error(request, "You don't have permission to modify this service.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core.models import CIWorkflow

        workflow_id = request.POST.get("ci_workflow")

        if workflow_id:
            # Validate workflow is in project's approved list
            available = get_available_workflows_for_project(self.project)
            try:
                workflow = available.get(id=workflow_id)
            except CIWorkflow.DoesNotExist:
                messages.error(request, "Selected workflow is not approved for this project.")
                return redirect(
                    "projects:service_detail",
                    project_name=self.project.name,
                    service_name=self.service.name,
                )

            # Check if workflow changed and manifest was previously pushed
            old_workflow = self.service.ci_workflow
            self.service.ci_workflow = workflow

            if old_workflow and old_workflow != workflow and self.service.ci_manifest_status == "synced":
                self.service.ci_manifest_status = "out_of_date"

            self.service.save(update_fields=["ci_workflow", "ci_manifest_status", "updated_at"])
            messages.success(request, f'CI Workflow updated to "{workflow.name}".')
        else:
            # Unassign workflow
            self.service.ci_workflow = None
            self.service.save(update_fields=["ci_workflow", "updated_at"])
            messages.success(request, "CI Workflow unassigned.")

        return redirect(
            f"{self.service.get_absolute_url()}?tab=ci"
            if hasattr(self.service, "get_absolute_url")
            else f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci"
        )


class ServiceSyncBuildsView(LoginRequiredMixin, View):
    """Manually poll GitHub for recent workflow runs."""

    def post(self, request, project_name, service_name):
        from core.git_utils import parse_git_url
        from core.models import ProjectConnection
        from core.tasks import poll_build_details

        project = get_object_or_404(Project, name=project_name, status="active")
        service = get_object_or_404(Service, project=project, name=service_name)

        # Check permissions (viewer can trigger sync)
        role = get_user_project_role(request.user, project)
        if not role:
            messages.error(request, "You don't have permission to access this service.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        # Guard: service must have a repo_url
        if not service.repo_url:
            messages.error(request, "Service has no repository URL.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        # Get SCM connection
        project_connection = (
            ProjectConnection.objects.filter(project=project, is_default=True).select_related("connection").first()
        )
        if not project_connection:
            messages.error(request, "No SCM connection configured for this project.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        connection = project_connection.connection
        plugin = connection.get_plugin()
        config = connection.get_config()

        if not plugin:
            messages.error(request, "SCM plugin not available.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        # Parse repo URL
        parsed = parse_git_url(service.repo_url)
        if not parsed:
            messages.error(request, "Invalid repository URL.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        repo_name = f"{parsed['owner']}/{parsed['repo']}"

        try:
            # Fetch recent workflow runs
            runs = plugin.list_workflow_runs(config, repo_name, per_page=10)

            # Filter to runs matching our CI workflow naming convention
            workflow_name_prefix = f"CI - {service.ci_workflow.name}" if service.ci_workflow else None

            queued = 0
            for run_data in runs:
                # Skip if workflow name doesn't match (when CI workflow is assigned)
                if workflow_name_prefix and not run_data["name"].startswith("CI - "):
                    continue

                # Enqueue polling task for each run
                poll_build_details.enqueue(
                    run_id=run_data["id"],
                    repo_name=repo_name,
                    connection_id=connection.id,
                    service_id=service.id,
                    artifact_ref="",  # Will be fetched by the task
                )
                queued += 1

            if queued > 0:
                messages.success(request, f"Syncing {queued} workflow run(s) from GitHub...")
            else:
                messages.info(request, "No matching workflow runs found.")

        except Exception as e:
            messages.error(request, f"Failed to fetch workflow runs: {e}")

        return redirect(f"/projects/{project_name}/services/{service_name}/?tab=builds")


class ServiceRegisterWebhookView(LoginRequiredMixin, View):
    """Manually register webhook for a service."""

    def post(self, request, project_name, service_name):
        from core.git_utils import parse_git_url
        from core.models import ProjectConnection, SiteConfiguration

        project = get_object_or_404(Project, name=project_name, status="active")
        service = get_object_or_404(Service, project=project, name=service_name)

        # Check permissions
        role = get_user_project_role(request.user, project)
        if role not in ["owner", "contributor"]:
            messages.error(request, "You don't have permission to configure webhooks.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        # Get site config for webhook URL
        site_config = SiteConfiguration.get_instance()
        if not site_config or not site_config.external_url:
            messages.error(request, "External URL not configured. Go to Settings > General to configure it.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        # Get SCM connection
        project_connection = (
            ProjectConnection.objects.filter(project=project, is_default=True).select_related("connection").first()
        )
        if not project_connection:
            messages.error(request, "No SCM connection configured for this project.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        connection = project_connection.connection
        plugin = connection.get_plugin()
        config = connection.get_config()

        if not plugin:
            messages.error(request, "SCM plugin not available.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        # Parse repo URL
        parsed = parse_git_url(service.repo_url)
        if not parsed:
            messages.error(request, "Invalid repository URL.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        repo_name = f"{parsed['owner']}/{parsed['repo']}"
        webhook_url = f"{site_config.external_url.rstrip('/')}/webhooks/build/"

        try:
            plugin.configure_webhook(
                config,
                repo_name,
                webhook_url,
                events=["workflow_run"],
            )
            service.webhook_registered = True
            service.save(update_fields=["webhook_registered", "updated_at"])
            messages.success(request, "Webhook registered successfully.")
        except Exception as e:
            messages.error(request, f"Failed to register webhook: {e}")

        return redirect("projects:service_detail", project_name=project_name, service_name=service_name)


class ServicePushManifestView(LoginRequiredMixin, View):
    """Enqueue push_ci_manifest background task for a service."""

    def dispatch(self, request, *args, **kwargs):
        project_name = kwargs.get("project_name")
        service_name = kwargs.get("service_name")

        self.project = get_object_or_404(Project, name=project_name, status="active")
        self.service = get_object_or_404(Service, project=self.project, name=service_name)

        # Check contributor permission
        role = can_access_project(request.user, self.project)
        if not role or role == "viewer":
            messages.error(request, "You don't have permission to modify this service.")
            return redirect("projects:service_detail", project_name=project_name, service_name=service_name)

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from core.models import ProjectConnection
        from core.tasks import push_ci_manifest

        # Guard: service must have a workflow assigned
        if not self.service.ci_workflow:
            messages.error(request, "No CI Workflow assigned. Assign a workflow first.")
            return redirect(f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci")

        # Guard: service must have a repo_url
        if not self.service.repo_url:
            messages.error(request, "Service has no repository URL. Repository must be set up first.")
            return redirect(f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci")

        # Guard: project must have an SCM connection
        scm_connection = (
            ProjectConnection.objects.filter(project=self.project, is_default=True, connection__plugin_name="github")
            .select_related("connection")
            .first()
        )

        if not scm_connection:
            messages.error(
                request, "No SCM connection configured for this project. Add a GitHub connection in project settings."
            )
            return redirect(f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci")

        # Enqueue the task
        push_ci_manifest.enqueue(service_id=self.service.id)
        messages.success(request, "CI manifest push started. A pull request will be created shortly.")

        return redirect(f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci")
