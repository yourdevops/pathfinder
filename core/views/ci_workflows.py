"""CI Workflows views: repository management, steps catalog, workflow composer."""

import json
from collections import OrderedDict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from core.ci_manifest import get_compatible_steps, is_step_compatible
from core.forms.ci_workflows import StepsRepoRegisterForm, WorkflowCreateForm
from core.models import (
    CIStep,
    CIWorkflow,
    CIWorkflowStep,
    RuntimeFamily,
    StepsRepository,
)
from core.permissions import OperatorRequiredMixin, has_system_role
from plugins.base import get_available_engines, get_ci_plugin_for_engine


class StepsRepoListView(LoginRequiredMixin, View):
    """List all registered CI steps repositories."""

    def get(self, request):
        repos = StepsRepository.objects.all().order_by("name")
        can_manage = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )
        # Annotate step counts and engine display
        for repo in repos:
            repo.step_count = repo.steps.count()
            repo.runtime_count = repo.runtimes.count()
            plugin = get_ci_plugin_for_engine(repo.engine)
            repo.engine_display = plugin.engine_display_name if plugin else repo.engine
        return render(
            request,
            "core/ci_workflows/repo_list.html",
            {
                "repos": repos,
                "can_manage": can_manage,
            },
        )


class StepsRepoRegisterView(OperatorRequiredMixin, View):
    """Register a new CI steps repository."""

    def get(self, request):
        form = StepsRepoRegisterForm()
        return render(
            request,
            "core/ci_workflows/repo_register.html",
            {
                "form": form,
            },
        )

    def post(self, request):
        form = StepsRepoRegisterForm(request.POST)
        if form.is_valid():
            repo = StepsRepository.objects.create(
                name=form.cleaned_data["name"],
                git_url=form.cleaned_data["git_url"],
                engine=form.cleaned_data["engine"],
                connection=form.cleaned_data.get("connection"),
                created_by=request.user.username,
            )
            # Enqueue scan task
            from core.tasks import scan_steps_repository

            scan_steps_repository.enqueue(repository_id=repo.id)
            return redirect("ci_workflows:repo_detail", repo_name=repo.name)
        return render(
            request,
            "core/ci_workflows/repo_register.html",
            {
                "form": form,
            },
        )


class StepsRepoDetailView(LoginRequiredMixin, View):
    """Show repository details with imported steps and runtimes."""

    def get(self, request, repo_name):
        repo = get_object_or_404(StepsRepository, name=repo_name)
        steps = repo.steps.all().order_by("phase", "name")
        runtimes = repo.runtimes.all().order_by("name")

        # Group steps by phase
        phase_order = ["setup", "build", "test", "package"]
        phase_labels = {
            "setup": "Setup",
            "build": "Build",
            "test": "Test",
            "package": "Package",
        }
        steps_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in steps if s.phase == phase]
            if phase_steps:
                steps_by_phase[phase_labels[phase]] = phase_steps
        # Steps without a phase
        uncategorized = [s for s in steps if s.phase not in phase_order]
        if uncategorized:
            steps_by_phase["Other"] = uncategorized

        can_manage = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )

        return render(
            request,
            "core/ci_workflows/repo_detail.html",
            {
                "repo": repo,
                "steps_by_phase": steps_by_phase,
                "runtimes": runtimes,
                "total_steps": steps.count(),
                "can_manage": can_manage,
            },
        )


class StepsRepoScanView(OperatorRequiredMixin, View):
    """Trigger a rescan of a steps repository."""

    def post(self, request, repo_name):
        repo = get_object_or_404(StepsRepository, name=repo_name)
        repo.scan_status = "scanning"
        repo.scan_error = ""
        repo.save(update_fields=["scan_status", "scan_error"])

        from core.tasks import scan_steps_repository

        scan_steps_repository.enqueue(repository_id=repo.id)

        if request.headers.get("HX-Request"):
            return render(
                request,
                "core/ci_workflows/_scan_status.html",
                {
                    "repo": repo,
                },
            )
        return redirect("ci_workflows:repo_detail", repo_name=repo.name)


class StepsRepoScanStatusView(LoginRequiredMixin, View):
    """HTMX partial for scan status polling."""

    def get(self, request, repo_name):
        repo = get_object_or_404(StepsRepository, name=repo_name)
        return render(
            request,
            "core/ci_workflows/_scan_status.html",
            {
                "repo": repo,
            },
        )


def _filter_steps(request):
    """Apply engine/runtime/version filters to CIStep queryset and return filtered list + filter context."""
    steps = CIStep.objects.all().select_related("repository").order_by("phase", "name")

    selected_engine = request.GET.get("engine", "")
    selected_runtime = request.GET.get("runtime", "")
    selected_runtime_version = request.GET.get("runtime_version", "")

    if selected_engine:
        steps = steps.filter(engine=selected_engine)

    steps_list = list(steps)

    if selected_runtime and selected_runtime_version:
        steps_list = [s for s in steps_list if is_step_compatible(s, selected_runtime, selected_runtime_version)]
    elif selected_runtime:
        steps_list = [s for s in steps_list if selected_runtime in (s.runtime_constraints or {})]

    # Collect distinct runtimes from all steps
    all_runtimes = set()
    for s in CIStep.objects.values_list("runtime_constraints", flat=True):
        if s:
            all_runtimes.update(s.keys())

    # Collect runtime versions from RuntimeFamily if a runtime is selected
    runtime_versions = []
    if selected_runtime:
        for rt in RuntimeFamily.objects.filter(name=selected_runtime):
            for v in rt.versions:
                if str(v) not in runtime_versions:
                    runtime_versions.append(str(v))
        runtime_versions.sort(reverse=True)

    engines = get_available_engines()

    return {
        "steps": steps_list,
        "engines": engines,
        "runtimes": sorted(all_runtimes),
        "selected_engine": selected_engine,
        "selected_runtime": selected_runtime,
        "selected_runtime_version": selected_runtime_version,
        "runtime_versions": runtime_versions,
    }


class StepsCatalogView(LoginRequiredMixin, View):
    """Browse all imported CI steps with engine/runtime filtering."""

    def get(self, request):
        context = _filter_steps(request)

        # HTMX partial request for table body
        if request.headers.get("HX-Request") and request.headers.get("HX-Target") == "steps-table-body":
            return render(request, "core/ci_workflows/_steps_table.html", context)

        return render(request, "core/ci_workflows/steps_catalog.html", context)


class StepsTableView(LoginRequiredMixin, View):
    """HTMX endpoint: return filtered steps table partial."""

    def get(self, request):
        context = _filter_steps(request)
        return render(request, "core/ci_workflows/_steps_table.html", context)


class StepDetailView(LoginRequiredMixin, View):
    """Show full details for a single CI step."""

    def get(self, request, step_uuid):
        step = get_object_or_404(CIStep, uuid=step_uuid)
        return render(
            request,
            "core/ci_workflows/step_detail.html",
            {
                "step": step,
            },
        )


# --- Workflow Creation and Composer Views ---


class WorkflowListView(LoginRequiredMixin, View):
    """List all CI workflows."""

    def get(self, request):
        workflows = CIWorkflow.objects.all().order_by("name")
        return render(
            request,
            "core/ci_workflows/workflow_list.html",
            {
                "workflows": workflows,
            },
        )


class WorkflowCreateView(LoginRequiredMixin, View):
    """Step 1: Create workflow with name, description, and runtime selection."""

    def get(self, request):
        form = WorkflowCreateForm()
        return render(
            request,
            "core/ci_workflows/workflow_create.html",
            {
                "form": form,
            },
        )

    def post(self, request):
        form = WorkflowCreateForm(request.POST)
        if form.is_valid():
            # Redirect to composer with params
            from urllib.parse import urlencode

            from django.urls import reverse

            params = urlencode(
                {
                    "name": form.cleaned_data["name"],
                    "description": form.cleaned_data.get("description", ""),
                    "runtime_family": form.cleaned_data["runtime_family"],
                    "runtime_version": form.cleaned_data["runtime_version"],
                }
            )
            return redirect(f"{reverse('ci_workflows:workflow_composer')}?{params}")
        return render(
            request,
            "core/ci_workflows/workflow_create.html",
            {
                "form": form,
            },
        )


class RuntimeVersionsView(LoginRequiredMixin, View):
    """HTMX endpoint: return version <option> elements for a runtime family."""

    def get(self, request):
        family = request.GET.get("runtime_family", "")
        if not family:
            return HttpResponse('<option value="">-- Select family first --</option>')

        runtimes = RuntimeFamily.objects.filter(name=family)
        versions = set()
        for rt in runtimes:
            for v in rt.versions:
                versions.add(str(v))

        options = ['<option value="">-- Select version --</option>']
        for v in sorted(versions, reverse=True):
            options.append(f'<option value="{v}">{v}</option>')
        return HttpResponse("\n".join(options))


class WorkflowComposerView(LoginRequiredMixin, View):
    """Step 2: Compose workflow steps with drag-and-drop ordering.

    Handles both create (GET /composer/?name=...&runtime_family=...&runtime_version=...)
    and edit (GET /<workflow_name>/edit/) modes.
    """

    def _build_compatible_context(self, runtime_family, runtime_version):
        """Build compatible/incompatible steps grouped by phase."""
        compatible, incompatible = get_compatible_steps(runtime_family, runtime_version)
        phase_order = ["setup", "build", "test", "package"]
        phase_labels = {
            "setup": "Setup",
            "build": "Build",
            "test": "Test",
            "package": "Package",
        }
        compatible_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in compatible if s.phase == phase]
            if phase_steps:
                compatible_by_phase[phase_labels[phase]] = phase_steps
        step_inputs_map = {str(s.uuid): s.inputs_schema or {} for s in compatible}
        return compatible_by_phase, incompatible, compatible, step_inputs_map

    def get(self, request, workflow_name=None):
        # Edit mode: load existing workflow
        if workflow_name:
            workflow = get_object_or_404(CIWorkflow, name=workflow_name)
            name = workflow.name
            description = workflow.description
            runtime_family = workflow.runtime_family
            runtime_version = workflow.runtime_version
            workflow_uuid = str(workflow.uuid)

            # Build initial steps JSON from existing workflow steps
            workflow_steps = workflow.workflow_steps.select_related("step").order_by("order")
            initial_steps = []
            for ws in workflow_steps:
                initial_steps.append(
                    {
                        "id": str(ws.step.uuid),
                        "name": ws.step.name,
                        "phase": ws.step.phase,
                        "description": ws.step.description[:80] if ws.step.description else "",
                        "inputs_schema": ws.step.inputs_schema or {},
                        "order": ws.order,
                        "input_config": ws.input_config or {},
                        "expanded": False,
                    }
                )
            initial_steps_json = initial_steps
        else:
            # Create mode: read from query params
            name = request.GET.get("name", "")
            description = request.GET.get("description", "")
            runtime_family = request.GET.get("runtime_family", "")
            runtime_version = request.GET.get("runtime_version", "")
            workflow_uuid = ""
            initial_steps_json = []

            if not name or not runtime_family or not runtime_version:
                return redirect("ci_workflows:workflow_create")

        compatible_by_phase, incompatible, compatible, step_inputs_map = self._build_compatible_context(
            runtime_family, runtime_version
        )

        return render(
            request,
            "core/ci_workflows/workflow_composer.html",
            {
                "workflow_name": name,
                "workflow_description": description,
                "runtime_family": runtime_family,
                "runtime_version": runtime_version,
                "workflow_uuid": workflow_uuid,
                "initial_steps_json": initial_steps_json,
                "compatible_by_phase": compatible_by_phase,
                "incompatible_steps": incompatible,
                "compatible_steps": compatible,
                "step_inputs_map": step_inputs_map,
            },
        )

    def post(self, request, workflow_name=None):
        name = request.POST.get("name", "")
        description = request.POST.get("description", "")
        runtime_family = request.POST.get("runtime_family", "")
        runtime_version = request.POST.get("runtime_version", "")
        steps_json = request.POST.get("steps_json", "[]")
        workflow_uuid = request.POST.get("workflow_uuid", "")

        if not name or not runtime_family or not runtime_version:
            return redirect("ci_workflows:workflow_create")

        try:
            steps_data = json.loads(steps_json)
        except json.JSONDecodeError:
            steps_data = []

        # Determine artifact_type from last package step
        artifact_type = ""
        for step_entry in reversed(steps_data):
            try:
                ci_step = CIStep.objects.get(uuid=step_entry.get("id"))
                if ci_step.phase == "package" and ci_step.produces:
                    artifact_type = ci_step.produces.get("type", "")
                    break
            except CIStep.DoesNotExist:
                continue

        if workflow_uuid:
            # Edit mode: update existing workflow
            workflow = get_object_or_404(CIWorkflow, uuid=workflow_uuid)
            workflow.name = name
            workflow.description = description
            workflow.runtime_family = runtime_family
            workflow.runtime_version = runtime_version
            workflow.artifact_type = artifact_type
            workflow.save()
            # Replace all steps
            workflow.workflow_steps.all().delete()
        else:
            # Create mode: new workflow
            workflow = CIWorkflow.objects.create(
                name=name,
                description=description,
                runtime_family=runtime_family,
                runtime_version=runtime_version,
                artifact_type=artifact_type,
                created_by=request.user.username,
            )

        # Create workflow steps
        for i, step_entry in enumerate(steps_data):
            try:
                ci_step = CIStep.objects.get(uuid=step_entry.get("id"))
                CIWorkflowStep.objects.create(
                    workflow=workflow,
                    step=ci_step,
                    order=i,
                    input_config=step_entry.get("input_config", {}),
                )
            except CIStep.DoesNotExist:
                continue

        return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)


class CompatibleStepsView(LoginRequiredMixin, View):
    """HTMX endpoint: return compatible/incompatible steps partial."""

    def get(self, request):
        runtime_family = request.GET.get("runtime_family", "")
        runtime_version = request.GET.get("runtime_version", "")

        if not runtime_family or not runtime_version:
            return HttpResponse('<p class="text-dark-muted text-sm">Select a runtime to see available steps.</p>')

        compatible, incompatible = get_compatible_steps(runtime_family, runtime_version)

        phase_order = ["setup", "build", "test", "package"]
        phase_labels = {
            "setup": "Setup",
            "build": "Build",
            "test": "Test",
            "package": "Package",
        }
        compatible_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in compatible if s.phase == phase]
            if phase_steps:
                compatible_by_phase[phase_labels[phase]] = phase_steps
        step_inputs_map = {str(s.uuid): s.inputs_schema or {} for s in compatible}

        return render(
            request,
            "core/ci_workflows/_compatible_steps.html",
            {
                "compatible_by_phase": compatible_by_phase,
                "incompatible_steps": incompatible,
                "step_inputs_map": step_inputs_map,
                "runtime_family": runtime_family,
                "runtime_version": runtime_version,
            },
        )


class StepConfigView(LoginRequiredMixin, View):
    """HTMX endpoint: return per-step input configuration form."""

    def get(self, request, step_uuid):
        step = get_object_or_404(CIStep, uuid=step_uuid)
        return render(
            request,
            "core/ci_workflows/_step_config.html",
            {
                "step": step,
            },
        )


# --- Workflow Detail, Manifest, and Delete Views ---


class WorkflowDetailView(LoginRequiredMixin, View):
    """Show workflow details with steps and generated manifest."""

    def get(self, request, workflow_name):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        workflow_steps = workflow.workflow_steps.select_related("step").order_by("order")
        first_step = workflow_steps.first()
        engine = first_step.step.engine if first_step else "github_actions"
        ci_plugin = get_ci_plugin_for_engine(engine)
        manifest_yaml = ci_plugin.generate_manifest(workflow) if ci_plugin else "# No CI plugin available"

        can_delete = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )

        # Services using this workflow
        services_using = workflow.services.select_related("project").order_by("project__name", "name")

        return render(
            request,
            "core/ci_workflows/workflow_detail.html",
            {
                "workflow": workflow,
                "workflow_steps": workflow_steps,
                "manifest_yaml": manifest_yaml,
                "can_delete": can_delete,
                "services_using": services_using,
            },
        )


class WorkflowManifestView(LoginRequiredMixin, View):
    """HTMX endpoint: return manifest preview partial."""

    def get(self, request, workflow_name):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        first_step = workflow.workflow_steps.select_related("step").first()
        engine = first_step.step.engine if first_step else "github_actions"
        ci_plugin = get_ci_plugin_for_engine(engine)
        manifest_yaml = ci_plugin.generate_manifest(workflow) if ci_plugin else "# No CI plugin available"
        return render(
            request,
            "core/ci_workflows/_manifest_preview.html",
            {
                "manifest_yaml": manifest_yaml,
            },
        )


class WorkflowDeleteView(OperatorRequiredMixin, View):
    """Delete a CI workflow."""

    def post(self, request, workflow_name):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        workflow.delete()
        return redirect("ci_workflows:workflow_list")
