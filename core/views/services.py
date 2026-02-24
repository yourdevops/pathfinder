"""Service views including creation wizard and detail pages."""

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.html import format_html
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
    ProjectCIConfig,
    ProjectMembership,
    Service,
    get_available_workflows_for_project,
)
from core.permissions import can_access_project, get_user_project_role, has_system_role
from core.tasks import scaffold_repository
from core.utils import resolve_env_vars
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
                # Default PTF_SERVICE variable (locked)
                context["default_service_var"] = {
                    "key": "PTF_SERVICE",
                    "value": service_name,
                    "lock": True,
                }

        elif self.steps.current == "workflow":
            # Add workflow list and detail context for step 3
            project_data = self.get_cleaned_data_for_step("project")
            if project_data:
                from core.models import CIWorkflowVersion, ProjectCIConfig

                project = project_data.get("project") or self.project
                workflows = get_available_workflows_for_project(project)
                context["available_workflows"] = workflows
                context["workflow_data_json"] = {
                    str(wf.id): {
                        "name": wf.name,
                        "runtime_constraints": wf.runtime_constraints or {},
                        "description": wf.description or "",
                        "dev_workflow": wf.dev_workflow or "trunk_based",
                    }
                    for wf in workflows
                }

                # Build versions map for all available workflows (same logic as CI tab)
                workflow_ids = list(workflows.values_list("id", flat=True))
                all_versions_qs = CIWorkflowVersion.objects.filter(
                    workflow_id__in=workflow_ids,
                    status__in=[CIWorkflowVersion.Status.AUTHORIZED, CIWorkflowVersion.Status.DRAFT],
                ).order_by("-published_at", "-created_at")

                allow_drafts = False
                try:
                    ci_config = project.ci_config
                    allow_drafts = ci_config.allow_draft_workflows
                except ProjectCIConfig.DoesNotExist:
                    pass

                versions_map = {}
                for wf_id in workflow_ids:
                    versions_for_wf = []
                    for v in all_versions_qs:
                        if v.workflow_id != wf_id:
                            continue
                        if not allow_drafts and v.status == "draft":
                            continue
                        versions_for_wf.append(
                            {
                                "id": str(v.id),
                                "version": v.version or "",
                                "status": v.status,
                                "label": "Draft"
                                if v.status == "draft"
                                else ("v" + v.version if v.version else "Draft"),
                                "author": str(v.author) if v.author else "",
                            }
                        )
                    versions_map[str(wf_id)] = versions_for_wf
                context["workflow_versions_json"] = json.dumps(versions_map)

                # Defaults: pre-select project's default workflow and its latest version
                default_workflow_id = ""
                default_version_id = "none"
                try:
                    ci_config = project.ci_config
                    if ci_config.default_workflow:
                        dw_id = str(ci_config.default_workflow_id)
                        if dw_id in versions_map:
                            default_workflow_id = dw_id
                            versions_for_default = versions_map[dw_id]
                            if versions_for_default:
                                default_version_id = versions_for_default[0]["id"]
                except ProjectCIConfig.DoesNotExist:
                    pass
                context["default_workflow_id"] = default_workflow_id
                context["default_version_id"] = default_version_id

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

        # Resolve version label for review display
        version_id = workflow_data.get("version_id", "")
        ci_workflow_version = None
        ci_workflow_version_label = "Not pinned"
        if version_id and version_id != "none" and ci_workflow:
            from core.models import CIWorkflowVersion

            try:
                ci_workflow_version = CIWorkflowVersion.objects.get(id=int(version_id), workflow=ci_workflow)
                ci_workflow_version_label = (
                    "Draft" if ci_workflow_version.status == "draft" else f"v{ci_workflow_version.version}"
                )
            except (CIWorkflowVersion.DoesNotExist, ValueError):
                pass

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
            "ci_workflow_version": ci_workflow_version,
            "ci_workflow_version_label": ci_workflow_version_label,
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

        # Add default PTF_SERVICE variable (locked)
        env_vars = [{"key": "PTF_SERVICE", "value": service_name, "lock": True}] + [
            v for v in env_vars if v.get("key") != "PTF_SERVICE"
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

        # Resolve version if provided
        ci_workflow_version = None
        version_id = workflow_data.get("version_id", "")
        if version_id and version_id != "none" and ci_workflow:
            import contextlib

            from core.models import CIWorkflowVersion

            with contextlib.suppress(CIWorkflowVersion.DoesNotExist, ValueError):
                ci_workflow_version = CIWorkflowVersion.objects.get(id=int(version_id), workflow=ci_workflow)

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
            ci_workflow_version=ci_workflow_version,
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
            context["merged_env_vars"] = resolve_env_vars(self.project, service=self.service)
            # Can edit if contributor or owner
            context["can_edit"] = self.user_project_role in ("contributor", "owner")

        elif tab == "ci":
            # CI Workflow tab context
            context["ci_workflow"] = self.service.ci_workflow
            context["ci_manifest_status"] = self.service.ci_manifest_status
            context["ci_manifest_out_of_sync"] = self.service.ci_manifest_out_of_sync
            context["ci_manifest_pr_url"] = self.service.ci_manifest_pr_url
            context["ci_manifest_pushed_at"] = self.service.ci_manifest_pushed_at
            available_workflows = get_available_workflows_for_project(self.project)
            context["available_workflows"] = available_workflows
            context["can_edit"] = self.user_project_role in ("contributor", "owner")

            # Version pinning dropdown
            from core.models import CIWorkflowVersion

            available_versions = []
            if self.service.ci_workflow:
                available_versions = list(
                    CIWorkflowVersion.objects.filter(
                        workflow=self.service.ci_workflow,
                        status__in=[CIWorkflowVersion.Status.AUTHORIZED, CIWorkflowVersion.Status.DRAFT],
                    ).order_by("-published_at", "-created_at")
                )
                # Filter out drafts if project doesn't allow them
                try:
                    ci_config = self.project.ci_config
                    if not ci_config.allow_draft_workflows:
                        available_versions = [v for v in available_versions if v.status != "draft"]
                except Exception:
                    available_versions = [v for v in available_versions if v.status != "draft"]
            context["available_versions"] = available_versions

            # Build versions map for ALL available workflows (for client-side dynamic swap)
            workflow_ids = list(available_workflows.values_list("id", flat=True))
            all_versions_qs = CIWorkflowVersion.objects.filter(
                workflow_id__in=workflow_ids,
                status__in=[CIWorkflowVersion.Status.AUTHORIZED, CIWorkflowVersion.Status.DRAFT],
            ).order_by("-published_at", "-created_at")

            # Check draft permission
            allow_drafts = False
            try:
                ci_config = self.project.ci_config
                allow_drafts = ci_config.allow_draft_workflows
            except ProjectCIConfig.DoesNotExist:
                pass

            # Build the map: {workflow_id_str: [{id, version, status, label, author}, ...]}
            versions_map = {}
            for wf_id in workflow_ids:
                versions_for_wf = []
                for v in all_versions_qs:
                    if v.workflow_id != wf_id:
                        continue
                    if not allow_drafts and v.status == "draft":
                        continue
                    versions_for_wf.append(
                        {
                            "id": str(v.id),
                            "version": v.version or "",
                            "status": v.status,
                            "label": "Draft" if v.status == "draft" else ("v" + v.version if v.version else "Draft"),
                            "author": str(v.author) if v.author else "",
                        }
                    )
                versions_map[str(wf_id)] = versions_for_wf

            context["workflow_versions_json"] = json.dumps(versions_map)

            # Show manifest preview: pinned version content if available, else fresh draft
            if self.service.ci_workflow:
                engine = self.service.ci_workflow.engine
                ci_plugin = get_ci_plugin_for_engine(engine)
                pinned = self.service.ci_workflow_version
                if pinned and pinned.manifest_content:
                    context["manifest_yaml"] = pinned.manifest_content
                else:
                    context["manifest_yaml"] = (
                        ci_plugin.generate_manifest(self.service.ci_workflow)
                        if ci_plugin
                        else "# No CI plugin available"
                    )
                context["manifest_file_path"] = ci_plugin.manifest_id(self.service.ci_workflow) if ci_plugin else None
            else:
                context["manifest_yaml"] = None

        elif tab == "builds":
            # Get current workflow name for categorization
            current_workflow_name = self.service.ci_workflow.name if self.service.ci_workflow else None

            # Get all builds for this service
            all_builds = Build.objects.filter(service=self.service)

            # Categorize builds
            if current_workflow_name:
                current_builds_qs = all_builds.filter(workflow_name=current_workflow_name)
                other_builds_qs = all_builds.exclude(workflow_name=current_workflow_name)
            else:
                current_builds_qs = Build.objects.none()
                other_builds_qs = all_builds

            # Determine if tabs should be shown (only when there are "Other" builds)
            show_workflow_tabs = other_builds_qs.exists()
            context["show_workflow_tabs"] = show_workflow_tabs
            context["other_builds_count"] = other_builds_qs.count()
            context["current_workflow_name"] = current_workflow_name

            # Handle build_tab parameter (default to "current" if tabs shown, otherwise show all)
            build_tab = self.request.GET.get("build_tab", "current")
            if not show_workflow_tabs:
                # No tabs needed - show all builds (which are all current or all other)
                builds_qs = all_builds
                build_tab = "current"
            elif build_tab == "other":
                builds_qs = other_builds_qs
            else:
                builds_qs = current_builds_qs
                build_tab = "current"

            context["active_build_tab"] = build_tab

            # Apply search filter
            search_query = self.request.GET.get("q", "").strip()
            if search_query:
                builds_qs = builds_qs.filter(
                    Q(commit_sha__icontains=search_query) | Q(commit_message__icontains=search_query)
                )
            context["search_query"] = search_query

            # Apply status filter if provided
            status_filter = self.request.GET.get("status", "all")
            if status_filter and status_filter != "all":
                builds_qs = builds_qs.filter(status=status_filter)

            # Apply sorting (default: newest first)
            sort_by = self.request.GET.get("sort", "-started_at")
            valid_sorts = [
                "started_at",
                "-started_at",
                "status",
                "-status",
                "duration_seconds",
                "-duration_seconds",
            ]
            if sort_by not in valid_sorts:
                sort_by = "-started_at"
            builds_qs = builds_qs.order_by(sort_by)
            context["sort_by"] = sort_by

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
            # Show per-environment resolved cascade views
            environments = self.project.environments.filter(status="active").order_by("order", "name")
            env_resolved = []
            for env in environments:
                resolved = resolve_env_vars(self.project, service=self.service, environment=env)
                env_resolved.append({"environment": env, "resolved_vars": resolved})
            context["env_resolved"] = env_resolved
            context["environments"] = environments

        elif tab == "settings":
            from core.views.env_vars import _get_env_var_urls

            context["resolved_vars"] = resolve_env_vars(self.project, service=self.service)
            context["is_editable_env_vars"] = self.user_project_role in ("contributor", "owner")
            context["can_edit"] = self.user_project_role in ("contributor", "owner")
            context.update(_get_env_var_urls("service", self.project.name, service_name=self.service.name))

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
            html = format_html(
                '<span class="px-2 py-1 text-xs rounded {}"'
                ' hx-get="{}"'
                ' hx-trigger="every 3s"'
                ' hx-swap="outerHTML">Scaffold: {}</span>',
                status_class,
                request.path,
                status_label,
            )
        else:
            html = format_html(
                '<span class="px-2 py-1 text-xs rounded {}">Scaffold: {}</span>',
                status_class,
                status_label,
            )

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
        from core.models import CIWorkflow, CIWorkflowVersion

        workflow_id = request.POST.get("ci_workflow")
        version_id = request.POST.get("version_id", "")
        update_fields = ["ci_workflow", "ci_manifest_status", "ci_workflow_version", "updated_at"]

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
                self.service.ci_manifest_status = "out_of_sync"

            # Handle version pinning in the same request
            if version_id and version_id != "none":
                try:
                    version = CIWorkflowVersion.objects.get(
                        id=int(version_id),
                        workflow=workflow,
                        status__in=[CIWorkflowVersion.Status.AUTHORIZED, CIWorkflowVersion.Status.DRAFT],
                    )
                    if version.status == CIWorkflowVersion.Status.DRAFT:
                        try:
                            ci_config = self.project.ci_config
                            if not ci_config.allow_draft_workflows:
                                messages.error(request, "This project does not allow draft workflow versions.")
                                return redirect(f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci")
                        except self.project.ci_config.RelatedObjectDoesNotExist:
                            messages.error(request, "This project does not allow draft workflow versions.")
                            return redirect(f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci")
                    self.service.ci_workflow_version = version
                except (CIWorkflowVersion.DoesNotExist, ValueError):
                    self.service.ci_workflow_version = None
            else:
                self.service.ci_workflow_version = None

            self.service.save(update_fields=update_fields)
            messages.success(request, f'CI Workflow updated to "{workflow.name}".')
        else:
            # Unassign workflow and version
            self.service.ci_workflow = None
            self.service.ci_workflow_version = None
            self.service.save(update_fields=update_fields)
            messages.success(request, "CI Workflow unassigned.")

        return redirect(
            f"{self.service.get_absolute_url()}?tab=ci"
            if hasattr(self.service, "get_absolute_url")
            else f"/projects/{self.project.name}/services/{self.service.name}/?tab=ci"
        )


class ServiceFetchBuildsView(LoginRequiredMixin, View):
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
            workflow_name_prefix = f"ci-{service.ci_workflow.name}" if service.ci_workflow else None

            queued = 0
            for run_data in runs:
                # Skip if workflow name doesn't match (when CI workflow is assigned)
                if workflow_name_prefix and not run_data["name"].startswith("ci-"):
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
                messages.success(request, f"Fetching {queued} workflow run(s) from GitHub...")
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
        webhook_url = plugin.get_webhook_url(site_config.external_url)

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


class ServiceProvisionVariablesView(LoginRequiredMixin, View):
    """Retry CI variable provisioning for a service."""

    def post(self, request, project_name, service_name):
        from core.git_utils import parse_git_url
        from core.models import ProjectConnection
        from plugins.base import CICapableMixin

        project = get_object_or_404(Project, name=project_name, status="active")
        service = get_object_or_404(Service, project=project, name=service_name)

        # Check contributor permission
        role = can_access_project(request.user, project)
        if not role or role == "viewer":
            messages.error(request, "You don't have permission to modify this service.")
            return redirect(f"/projects/{project_name}/services/{service_name}/?tab=ci")

        if not service.repo_url:
            messages.error(request, "Service has no repository configured.")
            return redirect(f"/projects/{project_name}/services/{service_name}/?tab=ci")

        # Get SCM connection
        project_connection = (
            ProjectConnection.objects.filter(project=project, is_default=True).select_related("connection").first()
        )
        if not project_connection:
            messages.error(request, "No SCM connection configured for this project.")
            return redirect(f"/projects/{project_name}/services/{service_name}/?tab=ci")

        connection = project_connection.connection
        plugin = connection.get_plugin()

        if not plugin or not isinstance(plugin, CICapableMixin):
            messages.error(request, "SCM plugin does not support CI variable provisioning.")
            return redirect(f"/projects/{project_name}/services/{service_name}/?tab=ci")

        parsed = parse_git_url(service.repo_url)
        if not parsed:
            messages.error(request, "Invalid repository URL.")
            return redirect(f"/projects/{project_name}/services/{service_name}/?tab=ci")

        repo_full_name = f"{parsed['owner']}/{parsed['repo']}"
        variables = {
            "PTF_PROJECT": service.project.name,
            "PTF_SERVICE": service.name,
        }

        try:
            result = plugin.provision_ci_variables(connection.get_config(), repo_full_name, variables)
            has_errors = any("error" in str(v) for v in result.values())
            if has_errors:
                service.ci_variables_status = "failed"
                service.ci_variables_error = str(result)
                messages.error(request, f"CI variable provisioning partially failed: {result}")
            else:
                service.ci_variables_status = "provisioned"
                service.ci_variables_error = ""
                messages.success(request, "CI variables provisioned successfully.")
            service.save(update_fields=["ci_variables_status", "ci_variables_error"])
        except Exception as e:
            service.ci_variables_status = "failed"
            service.ci_variables_error = str(e)
            service.save(update_fields=["ci_variables_status", "ci_variables_error"])
            messages.error(request, f"CI variable provisioning failed: {e}")

        return redirect(f"/projects/{project_name}/services/{service_name}/?tab=ci")


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


class ServiceAutoUpdateToggleView(LoginRequiredMixin, View):
    """Toggle auto_update_patch for a service via HTMX."""

    def post(self, request, project_name, service_name):
        project = get_object_or_404(Project, name=project_name, status="active")
        service = get_object_or_404(Service, project=project, name=service_name)

        # Check contributor permission
        role = can_access_project(request.user, project)
        if not role or role == "viewer":
            return HttpResponse("Permission denied", status=403)

        # Toggle based on checkbox value (checkbox sends value when checked, absent when unchecked)
        service.auto_update_patch = "auto_update_patch" in request.POST
        service.save(update_fields=["auto_update_patch", "updated_at"])

        # Return the updated toggle partial for HTMX swap
        return render(
            request,
            "core/services/_auto_update_toggle.html",
            {"service": service, "project": project, "can_edit": True},
        )


class ServicePinVersionView(LoginRequiredMixin, View):
    """Pin a service to a specific CIWorkflowVersion."""

    def _redirect_ci_tab(self, project_name, service_name):
        return redirect(f"/projects/{project_name}/services/{service_name}/?tab=ci")

    def post(self, request, project_name, service_name):
        from core.models import CIWorkflowVersion

        project = get_object_or_404(Project, name=project_name)
        service = get_object_or_404(Service, project=project, name=service_name)

        version_id = request.POST.get("version_id", "")

        if version_id == "" or version_id == "none":
            # Unpin: clear the FK
            service.ci_workflow_version = None
            service.save(update_fields=["ci_workflow_version"])
            messages.success(request, "Version unpinned. Service will not use a specific version.")
        else:
            try:
                version = CIWorkflowVersion.objects.get(
                    id=int(version_id),
                    workflow=service.ci_workflow,  # Must belong to the service's assigned workflow
                    status__in=[CIWorkflowVersion.Status.AUTHORIZED, CIWorkflowVersion.Status.DRAFT],
                )
                # If draft, check project allows drafts
                if version.status == CIWorkflowVersion.Status.DRAFT:
                    try:
                        ci_config = project.ci_config
                        if not ci_config.allow_draft_workflows:
                            messages.error(
                                request,
                                "This project does not allow draft workflow versions. Enable 'Allow Drafts' in Project CI Settings first.",
                            )
                            return self._redirect_ci_tab(project_name, service_name)
                    except project.ci_config.RelatedObjectDoesNotExist:
                        messages.error(
                            request,
                            "This project does not allow draft workflow versions. Enable 'Allow Drafts' in Project CI Settings first.",
                        )
                        return self._redirect_ci_tab(project_name, service_name)

                service.ci_workflow_version = version
                service.save(update_fields=["ci_workflow_version"])
                messages.success(request, f"Service pinned to version {version.version or 'draft'}.")
            except (CIWorkflowVersion.DoesNotExist, ValueError):
                messages.error(request, "Invalid version selected.")

        return self._redirect_ci_tab(project_name, service_name)


class BuildLogsView(LoginRequiredMixin, View):
    """HTMX endpoint to fetch and cache build logs."""

    # Error patterns to detect and highlight
    ERROR_PATTERNS = ["error", "failed", "failure", "exception", "traceback", "fatal"]
    # Warning patterns for yellow highlighting
    WARNING_PATTERNS = ["warning", "warn", "deprecated"]

    def _is_error_line(self, line: str) -> bool:
        """Check if a line contains error-related keywords."""
        lower_line = line.lower()
        return any(pattern in lower_line for pattern in self.ERROR_PATTERNS)

    def _is_warning_line(self, line: str) -> bool:
        """Check if a line contains warning-related keywords."""
        lower_line = line.lower()
        return any(pattern in lower_line for pattern in self.WARNING_PATTERNS)

    def _extract_step_logs(self, logs: str, step_name: str) -> str | None:
        """
        Extract logs for a specific step from GitHub Actions job logs.

        GitHub Actions logs have format:
        TIMESTAMP ##[group]Step Name
        ...log content...
        TIMESTAMP ##[endgroup]

        Args:
            logs: Full job logs from GitHub API
            step_name: Name of the step to extract

        Returns:
            Extracted step logs or None if not found
        """
        import re

        lines = logs.split("\n")
        result_lines = []
        in_target_step = False
        found_step = False

        for line in lines:
            # Check for step start marker: ##[group]Step Name
            if "##[group]" in line:
                # Extract step name from the line
                match = re.search(r"##\[group\](.+)$", line)
                if match:
                    current_step = match.group(1).strip()
                    # Check if this is our target step (fuzzy match)
                    if step_name and (
                        step_name.lower() in current_step.lower() or current_step.lower() in step_name.lower()
                    ):
                        in_target_step = True
                        found_step = True
                        result_lines.append(f"=== Step: {current_step} ===")
                        continue

            # Check for step end marker
            if "##[endgroup]" in line:
                if in_target_step:
                    in_target_step = False
                    # Don't break - there might be post-step content
                continue

            # Collect lines if we're in the target step
            if in_target_step:
                # Clean up timestamp prefix if present (e.g., "2024-01-01T12:00:00.0000000Z ")
                cleaned = re.sub(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*", "", line)
                result_lines.append(cleaned)

        if found_step and result_lines:
            return "\n".join(result_lines)
        return None

    def _process_logs(self, logs: str, build_status: str, failed_step_name: str = "") -> tuple[list[dict], bool]:
        """
        Process logs for display.

        For failed builds: extract only the failed step's logs.
        For successful builds: show last 100 lines.

        Returns list of dicts with: text, is_error, is_warning
        """
        if not logs:
            return [], False

        def classify_line(line: str) -> dict:
            """Classify a line as error, warning, or normal."""
            is_error = self._is_error_line(line)
            # Only mark as warning if not already an error (error takes precedence)
            is_warning = not is_error and self._is_warning_line(line)
            return {"text": line, "is_error": is_error, "is_warning": is_warning}

        if build_status == "failed" and failed_step_name:
            # Try to extract only the failed step's logs
            step_logs = self._extract_step_logs(logs, failed_step_name)
            if step_logs:
                lines = step_logs.split("\n")
                return [classify_line(line) for line in lines], False

        # Fallback: show all logs with error/warning highlighting
        lines = logs.split("\n")

        # For non-failed or if step extraction failed, show last 200 lines
        max_lines = 200
        if len(lines) <= max_lines:
            return [classify_line(line) for line in lines], False

        return [classify_line(line) for line in lines[-max_lines:]], True

    def get(self, request, project_name, service_name, build_uuid):
        from django.core.cache import cache

        from core.git_utils import parse_git_url
        from core.models import ProjectConnection

        project = get_object_or_404(Project, name=project_name, status="active")
        service = get_object_or_404(Service, project=project, name=service_name)
        build = get_object_or_404(Build, uuid=build_uuid, service=service)

        # Check permissions
        role = get_user_project_role(request.user, project)
        if not role:
            return HttpResponse("Access denied", status=403)

        # Only fetch logs for non-successful builds
        if build.status == "success":
            return render(
                request,
                "core/services/_build_logs_partial.html",
                {
                    "logs": None,
                    "log_lines": [],
                    "logs_truncated": False,
                    "failed_job_name": "",
                    "failed_step_name": "",
                    "build": build,
                    "skip_reason": "Logs not fetched for successful builds",
                },
            )

        # Check cache first
        cache_key = f"build_logs_{build_uuid}"
        cached = cache.get(cache_key)
        if cached:
            log_lines, truncated = self._process_logs(cached.get("logs"), build.status, build.failed_step_name)
            return render(
                request,
                "core/services/_build_logs_partial.html",
                {
                    "logs": cached.get("logs"),
                    "log_lines": log_lines,
                    "logs_truncated": truncated,
                    "failed_job_name": build.failed_job_name,
                    "failed_step_name": build.failed_step_name,
                    "build": build,
                },
            )

        # Need to fetch from GitHub
        if not service.repo_url:
            return render(request, "core/services/_build_logs_partial.html", {"error": "No repository configured"})

        project_connection = (
            ProjectConnection.objects.filter(project=project, is_default=True).select_related("connection").first()
        )
        if not project_connection:
            return render(request, "core/services/_build_logs_partial.html", {"error": "No SCM connection configured"})

        connection = project_connection.connection
        plugin = connection.get_plugin()
        config = connection.get_config()

        parsed = parse_git_url(service.repo_url)
        if not parsed:
            return render(request, "core/services/_build_logs_partial.html", {"error": "Invalid repository URL"})

        repo_name = f"{parsed['owner']}/{parsed['repo']}"

        # Fetch jobs to find failed one and get job_id for logs
        try:
            jobs = plugin.get_workflow_run_jobs(config, repo_name, build.ci_run_id)
        except Exception as e:
            return render(request, "core/services/_build_logs_partial.html", {"error": f"Failed to fetch jobs: {e}"})

        # Find failed job/step and update build if not already set
        failed_job = None
        failed_step = None
        job_id_for_logs = None

        for job in jobs:
            if job["conclusion"] == "failure":
                failed_job = job["name"]
                job_id_for_logs = job["id"]
                for step in job.get("steps", []):
                    if step["conclusion"] == "failure":
                        failed_step = step["name"]
                        break
                break
            # Also capture the first job for logs if no failure
            if job_id_for_logs is None:
                job_id_for_logs = job["id"]

        # Update build with failed info if not set
        if build.status == "failed" and not build.failed_job_name and failed_job:
            build.failed_job_name = failed_job
            build.failed_step_name = failed_step or ""
            build.save(update_fields=["failed_job_name", "failed_step_name", "updated_at"])

        # Fetch logs
        logs = None
        if job_id_for_logs:
            import contextlib

            with contextlib.suppress(Exception):
                logs = plugin.get_job_logs(config, repo_name, job_id_for_logs)

        # Cache raw logs
        cache.set(cache_key, {"logs": logs})

        # Use updated failed_step_name (either from DB or just set)
        step_name = build.failed_step_name or failed_step or ""

        # Process logs for display - extract only failed step if available
        log_lines, truncated = self._process_logs(logs, build.status, step_name)

        return render(
            request,
            "core/services/_build_logs_partial.html",
            {
                "logs": logs,
                "log_lines": log_lines,
                "logs_truncated": truncated,
                "failed_job_name": build.failed_job_name,
                "failed_step_name": build.failed_step_name,
                "build": build,
            },
        )
