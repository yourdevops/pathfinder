"""CI Workflows views: repository management, steps catalog, workflow composer."""

import json
from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, Count, IntegerField, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from core.ci_manifest import get_compatible_steps, is_step_compatible
from core.forms.ci_workflows import StepsRepoRegisterForm, WorkflowCreateForm
from core.models import (
    CIStep,
    CIWorkflow,
    CIWorkflowStep,
    CIWorkflowVersion,
    RuntimeFamily,
    StepsRepository,
    compute_manifest_hash,
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
        active_steps = repo.steps.filter(status="active").order_by("phase", "name")
        archived_steps = repo.steps.filter(status="archived").order_by("name")
        runtimes = repo.runtimes.all().order_by("name")

        # Group active steps by phase
        phase_order = ["setup", "test", "build", "package"]
        phase_labels = {
            "setup": "Setup",
            "build": "Build",
            "test": "Test",
            "package": "Package",
        }
        steps_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in active_steps if s.phase == phase]
            if phase_steps:
                steps_by_phase[phase_labels[phase]] = phase_steps
        # Steps without a phase
        uncategorized = [s for s in active_steps if s.phase not in phase_order]
        if uncategorized:
            steps_by_phase["Other"] = uncategorized

        can_manage = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )

        workflows_using = CIWorkflow.objects.filter(workflow_steps__step__repository=repo).distinct().order_by("name")
        can_delete = can_manage and not workflows_using.exists()

        return render(
            request,
            "core/ci_workflows/repo_detail.html",
            {
                "repo": repo,
                "steps_by_phase": steps_by_phase,
                "runtimes": runtimes,
                "total_steps": active_steps.count(),
                "archived_steps": archived_steps,
                "can_manage": can_manage,
                "workflows_using": workflows_using,
                "can_delete": can_delete,
                "repo_delete_url": reverse("ci_workflows:repo_delete", kwargs={"repo_name": repo.name}),
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


class StepsRepoDeleteView(OperatorRequiredMixin, View):
    """Delete a steps repository and all its steps."""

    def post(self, request, repo_name):
        repo = get_object_or_404(StepsRepository, name=repo_name)
        if CIWorkflowStep.objects.filter(step__repository=repo).exists():
            messages.error(request, "Cannot delete repository: its steps are used by workflows.")
            return redirect("ci_workflows:repo_detail", repo_name=repo.name)
        repo.delete()
        return redirect("ci_workflows:repo_list")


def _filter_steps(request):
    """Apply engine/runtime/version filters to CIStep queryset and return filtered list + filter context."""
    phase_ordering = Case(
        When(phase="setup", then=Value(0)),
        When(phase="test", then=Value(1)),
        When(phase="build", then=Value(2)),
        When(phase="package", then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )
    steps = (
        CIStep.objects.filter(status="active")
        .select_related("repository")
        .annotate(phase_order=phase_ordering)
        .order_by("phase_order", "name")
    )

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

    # Annotate engine display names
    engines = get_available_engines()
    engine_display_map = dict(engines)
    for s in steps_list:
        s.engine_display = engine_display_map.get(s.engine, s.engine)

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

        # Build source URL for the step's file in its repository
        ci_plugin = get_ci_plugin_for_engine(step.engine)
        engine_file = ci_plugin.engine_file_name if ci_plugin else "action.yml"
        engine_display = ci_plugin.engine_display_name if ci_plugin else step.engine

        source_url = ""
        if step.commit_sha and step.repository:
            base_url = step.repository.git_url.rstrip("/")
            if base_url.endswith(".git"):
                base_url = base_url[:-4]
            if step.file_path:
                source_url = f"{base_url}/blob/{step.commit_sha}/{step.file_path}"
            else:
                source_url = f"{base_url}/blob/{step.commit_sha}/ci-steps/{step.directory_name}/{engine_file}"

        return render(
            request,
            "core/ci_workflows/step_detail.html",
            {
                "step": step,
                "source_url": source_url,
                "engine_file": engine_file,
                "engine_display": engine_display,
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

            params = urlencode(
                {
                    "name": form.cleaned_data["name"],
                    "description": form.cleaned_data.get("description", ""),
                    "engine": form.cleaned_data["engine"],
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
        family = request.GET.get("runtime_family", "") or request.GET.get("runtime", "")
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


class EngineRuntimesView(LoginRequiredMixin, View):
    """HTMX endpoint: return runtime family <option> elements for a selected engine."""

    def get(self, request):
        engine = request.GET.get("engine", "")
        if not engine:
            return HttpResponse('<option value="">-- Select engine first --</option>')
        families = (
            RuntimeFamily.objects.filter(repository__engine=engine)
            .values_list("name", flat=True)
            .distinct()
            .order_by("name")
        )
        options = ['<option value="">-- Select runtime --</option>']
        for f in families:
            options.append(f'<option value="{f}">{f.title()}</option>')
        return HttpResponse("\n".join(options))


def _validate_step_order(steps_data):
    """Validate setup-before-use rule for workflow steps.

    For each non-setup step with runtime_constraints, verify a setup step
    for the same runtime appears earlier in the list.
    """
    provided_runtimes = set()
    errors = []

    for step_entry in steps_data:
        try:
            ci_step = CIStep.objects.get(uuid=step_entry.get("id"))
        except CIStep.DoesNotExist:
            continue

        if ci_step.phase == "setup":
            for rt in ci_step.runtime_constraints or {}:
                provided_runtimes.add(rt)
        elif ci_step.runtime_constraints:
            for rt in ci_step.runtime_constraints:
                if rt != "*" and rt not in provided_runtimes:
                    errors.append(
                        f'"{ci_step.name}" requires {rt} runtime setup. Add a setup step for {rt} before this step.'
                    )
    return errors


class WorkflowComposerView(LoginRequiredMixin, View):
    """Step 2: Compose workflow steps with drag-and-drop ordering.

    Handles both create (GET /composer/?name=...&runtime_family=...&runtime_version=...)
    and edit (GET /<workflow_name>/edit/) modes.
    """

    def _build_compatible_context(self, runtime_family, runtime_version):
        """Build compatible/incompatible steps grouped by phase."""
        compatible, incompatible = get_compatible_steps(runtime_family, runtime_version)
        phase_order = ["setup", "test", "build", "package"]
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

            # Handle fork_from: pre-populate steps from source workflow
            fork_from = request.GET.get("fork_from", "")
            if fork_from:
                try:
                    source_wf = CIWorkflow.objects.get(name=fork_from)
                    workflow_steps = source_wf.workflow_steps.select_related("step").order_by("order")
                    for ws in workflow_steps:
                        initial_steps_json.append(
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
                except CIWorkflow.DoesNotExist:
                    pass

            if not name or not runtime_family or not runtime_version:
                return redirect("ci_workflows:workflow_create")

        compatible_by_phase, incompatible, compatible, step_inputs_map = self._build_compatible_context(
            runtime_family, runtime_version
        )

        engine = workflow.engine if workflow_name else request.GET.get("engine", "github_actions")

        return render(
            request,
            "core/ci_workflows/workflow_composer.html",
            {
                "workflow_name": name,
                "workflow_description": description,
                "runtime_family": runtime_family,
                "runtime_version": runtime_version,
                "workflow_uuid": workflow_uuid,
                "engine": engine,
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

        # Validate step ordering (setup-before-use)
        ordering_errors = _validate_step_order(steps_data)
        if ordering_errors:
            for err in ordering_errors:
                messages.error(request, err)
            # Re-render composer with current data so user can fix ordering
            engine_val = request.POST.get("engine") or request.GET.get("engine", "github_actions")
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
                    "engine": engine_val,
                    "initial_steps_json": steps_data,
                    "compatible_by_phase": compatible_by_phase,
                    "incompatible_steps": incompatible,
                    "compatible_steps": compatible,
                    "step_inputs_map": step_inputs_map,
                },
            )

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

        engine_value = request.POST.get("engine") or request.GET.get("engine", "github_actions")

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
                engine=engine_value,
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

        # Auto-create or update draft CIWorkflowVersion
        engine = workflow.engine
        ci_plugin = get_ci_plugin_for_engine(engine)

        if ci_plugin:
            # Generate draft manifest (version=None produces "draft" in header)
            manifest_content = ci_plugin.generate_manifest(workflow, version=None)
            manifest_hash = compute_manifest_hash(manifest_content)

            # Create or update the single draft slot
            CIWorkflowVersion.objects.update_or_create(
                workflow=workflow,
                status=CIWorkflowVersion.Status.DRAFT,
                defaults={
                    "manifest_hash": manifest_hash,
                    "manifest_content": manifest_content,
                    "author": request.user,
                },
            )

        return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)


class CompatibleStepsView(LoginRequiredMixin, View):
    """HTMX endpoint: return compatible/incompatible steps partial."""

    def get(self, request):
        runtime_family = request.GET.get("runtime_family", "")
        runtime_version = request.GET.get("runtime_version", "")

        if not runtime_family or not runtime_version:
            return HttpResponse('<p class="text-dark-muted text-sm">Select a runtime to see available steps.</p>')

        compatible, incompatible = get_compatible_steps(runtime_family, runtime_version)

        phase_order = ["setup", "test", "build", "package"]
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

        # Check for step warnings (archived or interface changes)
        has_step_warnings = False
        for ws in workflow_steps:
            if ws.step.status == "archived" or ws.step.last_change_type == "interface":
                has_step_warnings = True
                break

        engine = workflow.engine
        ci_plugin = get_ci_plugin_for_engine(engine)
        manifest_yaml = ci_plugin.generate_manifest(workflow) if ci_plugin else "# No CI plugin available"

        # Version info for UI
        draft_version = workflow.versions.filter(status=CIWorkflowVersion.Status.DRAFT).first()
        latest_version = (
            workflow.versions.filter(status=CIWorkflowVersion.Status.AUTHORIZED).order_by("-published_at").first()
        )

        # Services using this workflow
        services_using = workflow.services.select_related("project").order_by("project__name", "name")

        # All versions for version history tab (annotate reference counts for delete eligibility)
        versions = workflow.versions.annotate(
            pinned_count=Count("pinned_services"),
            build_count=Count("builds"),
        ).order_by("-created_at")

        # Suggested next version for publish modal
        import semver as semver_lib

        if latest_version and latest_version.version:
            try:
                suggested_version = str(semver_lib.Version.parse(latest_version.version).bump_patch())
            except ValueError:
                suggested_version = "1.0.0"
        else:
            suggested_version = "1.0.0"

        is_operator = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )
        can_delete = is_operator and not services_using.exists()

        # Active tab from query param
        active_tab = request.GET.get("tab", "steps")

        return render(
            request,
            "core/ci_workflows/workflow_detail.html",
            {
                "workflow": workflow,
                "workflow_steps": workflow_steps,
                "manifest_yaml": manifest_yaml,
                "draft_version": draft_version,
                "latest_version": latest_version,
                "versions": versions,
                "suggested_version": suggested_version,
                "can_delete": can_delete,
                "is_operator": is_operator,
                "services_using": services_using,
                "has_step_warnings": has_step_warnings,
                "active_tab": active_tab,
                "workflow_delete_url": reverse("ci_workflows:workflow_delete", kwargs={"workflow_name": workflow.name}),
            },
        )


class WorkflowManifestView(LoginRequiredMixin, View):
    """HTMX endpoint: return manifest preview partial."""

    def get(self, request, workflow_name):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        engine = workflow.engine
        ci_plugin = get_ci_plugin_for_engine(engine)

        # Show versioned manifest: draft first, then latest authorized, then fresh generate
        draft_version = workflow.versions.filter(status="draft").first()
        if draft_version:
            manifest_yaml = draft_version.manifest_content
        elif latest_version := workflow.versions.filter(status="authorized").order_by("-published_at").first():
            manifest_yaml = latest_version.manifest_content
        else:
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
        if workflow.services.exists():
            messages.error(request, "Cannot delete workflow: it is still used by services.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)
        if workflow.versions.exists():
            messages.error(
                request,
                "Cannot delete workflow: it still has versions. Delete all versions first (Version History tab).",
            )
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)
        workflow.delete()
        return redirect("ci_workflows:workflow_list")


class WorkflowArchiveView(OperatorRequiredMixin, View):
    """Toggle workflow archived status."""

    def post(self, request, workflow_name):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        if workflow.status == "archived":
            workflow.status = "published"
            messages.success(request, f'Workflow "{workflow.name}" restored.')
        else:
            workflow.status = "archived"
            messages.success(request, f'Workflow "{workflow.name}" archived.')
        workflow.save(update_fields=["status"])
        return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)


# --- Version Management Views ---


class PublishVersionView(LoginRequiredMixin, View):
    """Publish a draft CIWorkflowVersion with a version number."""

    def post(self, request, workflow_name):
        import semver as semver_lib
        from django.utils import timezone

        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        draft = workflow.versions.filter(status=CIWorkflowVersion.Status.DRAFT).first()

        if not draft:
            messages.error(request, "No draft version to publish.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)

        version_number = request.POST.get("version", "").strip()
        changelog = request.POST.get("changelog", "").strip()

        # Validate semver
        try:
            v = semver_lib.Version.parse(version_number)
        except ValueError:
            messages.error(
                request,
                f"Invalid version number: {version_number}. Must be valid semver (e.g., 1.0.0).",
            )
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)

        # Check uniqueness
        if CIWorkflowVersion.objects.filter(workflow=workflow, version=version_number).exists():
            messages.error(request, f"Version {version_number} already exists.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)

        # Check ordering (must be > latest authorized)
        latest = (
            CIWorkflowVersion.objects.filter(
                workflow=workflow,
                status=CIWorkflowVersion.Status.AUTHORIZED,
            )
            .exclude(version="")
            .order_by("-published_at")
            .first()
        )
        if latest and latest.version:
            try:
                latest_v = semver_lib.Version.parse(latest.version)
                if v <= latest_v:
                    messages.error(request, f"Version must be greater than {latest.version}.")
                    return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)
            except ValueError:
                pass  # Latest version not parseable, allow any new version

        # Regenerate manifest with version number (changes header, changes hash)
        engine = workflow.engine
        ci_plugin = get_ci_plugin_for_engine(engine)

        if ci_plugin:
            manifest_content = ci_plugin.generate_manifest(workflow, version=version_number)
            manifest_hash = compute_manifest_hash(manifest_content)
        else:
            messages.error(request, "No CI plugin available.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)

        # Transition draft -> authorized
        draft.version = version_number
        draft.status = CIWorkflowVersion.Status.AUTHORIZED
        draft.manifest_content = manifest_content
        draft.manifest_hash = manifest_hash
        draft.changelog = changelog
        draft.published_at = timezone.now()
        draft.save()

        messages.success(request, f"Version {version_number} published successfully.")
        return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)


class RevokeVersionView(OperatorRequiredMixin, View):
    """Revoke an authorized CIWorkflowVersion."""

    def post(self, request, workflow_name, version_id):
        from django.utils import timezone

        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        version = get_object_or_404(
            CIWorkflowVersion,
            id=version_id,
            workflow=workflow,
            status=CIWorkflowVersion.Status.AUTHORIZED,
        )

        version.status = CIWorkflowVersion.Status.REVOKED
        version.revoked_at = timezone.now()
        version.revoked_by = request.user
        version.manifest_content = ""  # Clear content on revocation per design doc
        version.save(update_fields=["status", "revoked_at", "revoked_by", "manifest_content"])

        messages.success(request, f"Version {version.version} has been revoked.")
        return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)


class DiscardDraftView(LoginRequiredMixin, View):
    """Discard (delete) a draft CIWorkflowVersion."""

    def post(self, request, workflow_name):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        draft = workflow.versions.filter(status=CIWorkflowVersion.Status.DRAFT).first()
        if draft:
            draft.delete()
            messages.success(request, "Draft discarded.")
        return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)


class DeleteVersionView(OperatorRequiredMixin, View):
    """Delete a CIWorkflowVersion that has no remaining references."""

    def post(self, request, workflow_name, version_id):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        version = get_object_or_404(CIWorkflowVersion, id=version_id, workflow=workflow)

        # Block deletion if any services or builds still reference this version
        if version.pinned_services.exists():
            messages.error(request, f"Cannot delete version {version.version}: still pinned by services.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)
        if version.builds.exists():
            messages.error(request, f"Cannot delete version {version.version}: still referenced by builds.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)

        label = version.version or "draft"
        version.delete()
        messages.success(request, f"Version {label} deleted.")
        return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)


class ForkWorkflowView(LoginRequiredMixin, View):
    """Fork an existing workflow -- redirects to composer pre-populated with existing steps."""

    def get(self, request, workflow_name):
        """Show fork form (rendered inline on workflow detail page)."""
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        return render(
            request,
            "core/ci_workflows/workflow_detail.html",
            {
                "workflow": workflow,
                "show_fork_form": True,
            },
        )

    def post(self, request, workflow_name):
        """Redirect to composer with pre-populated data from source workflow."""
        from urllib.parse import urlencode

        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        new_name = request.POST.get("name", "").strip()

        if not new_name:
            messages.error(request, "Fork name is required.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)

        # Check uniqueness
        if CIWorkflow.objects.filter(name=new_name).exists():
            messages.error(request, f"A workflow named '{new_name}' already exists.")
            return redirect("ci_workflows:workflow_detail", workflow_name=workflow.name)

        # Redirect to composer in create mode with pre-populated params
        engine = workflow.engine

        params = urlencode(
            {
                "name": new_name,
                "description": f"Forked from {workflow.name}. {workflow.description}",
                "engine": engine,
                "runtime_family": workflow.runtime_family,
                "runtime_version": workflow.runtime_version,
                "fork_from": workflow.name,  # Composer will load steps from this workflow
            }
        )
        return redirect(f"{reverse('ci_workflows:workflow_composer')}?{params}")


class SuggestVersionView(LoginRequiredMixin, View):
    """HTMX endpoint: suggest next version number for publishing."""

    def get(self, request, workflow_name):
        import semver as semver_lib

        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        latest = (
            CIWorkflowVersion.objects.filter(workflow=workflow, status="authorized")
            .exclude(version="")
            .order_by("-published_at")
            .first()
        )
        if latest and latest.version:
            try:
                v = semver_lib.Version.parse(latest.version)
                suggested = str(v.bump_patch())
            except ValueError:
                suggested = "1.0.0"
        else:
            suggested = "1.0.0"
        return HttpResponse(suggested)
