"""CI Workflows views: repository management, steps catalog, workflow composer."""

import json
import logging
from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, Count, IntegerField, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from core.ci_manifest import compute_runtime_constraints
from core.forms.ci_workflows import StepsRepoRegisterForm, WorkflowCreateForm
from core.git_utils import parse_git_url
from core.models import (
    CIStep,
    CIWorkflow,
    CIWorkflowStep,
    CIWorkflowVersion,
    StepsRepository,
    compute_manifest_hash,
)
from core.permissions import OperatorRequiredMixin, has_system_role
from plugins.base import get_available_engines, get_ci_plugin_for_engine

logger = logging.getLogger(__name__)


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

            # Register webhook for push events on the steps repository
            if repo.connection:
                from core.models import SiteConfiguration

                site_config = SiteConfiguration.get_instance()
                if site_config and site_config.external_url:
                    try:
                        plugin = repo.connection.get_plugin()
                        config = repo.connection.get_config()
                        parsed = parse_git_url(repo.git_url)
                        if plugin and parsed:
                            repo_full_name = f"{parsed['owner']}/{parsed['repo']}"
                            webhook_url = plugin.get_webhook_url(site_config.external_url)
                            plugin.configure_webhook(
                                config,
                                repo_full_name,
                                webhook_url,
                                events=["push"],
                            )
                            logger.info(f"Registered webhook for steps repo {repo.name}")
                    except Exception as e:
                        # Log but don't fail registration
                        logger.warning(f"Failed to register webhook for steps repo {repo.name}: {e}")

            # Enqueue scan task
            from core.tasks import scan_steps_repository

            scan_steps_repository.enqueue(repository_id=repo.id, trigger="manual")
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

        # Sync history (most recent 20)
        sync_logs = repo.sync_logs.prefetch_related("entries").order_by("-started_at")[:20]

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
                "sync_logs": sync_logs,
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

        scan_steps_repository.enqueue(repository_id=repo.id, trigger="manual")

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


class SyncDetailView(LoginRequiredMixin, View):
    """HTMX partial for sync log detail with per-step entries."""

    def get(self, request, repo_name, sync_id):
        from core.models import StepsRepoSyncLog

        sync_log = get_object_or_404(StepsRepoSyncLog, id=sync_id, repository__name=repo_name)
        return render(
            request,
            "core/ci_workflows/_sync_detail.html",
            {"sync_log": sync_log, "entries": sync_log.entries.all()},
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
    if selected_engine:
        steps = steps.filter(engine=selected_engine)

    steps_list = list(steps)

    if selected_runtime:
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

    return {
        "steps": steps_list,
        "engines": engines,
        "runtimes": sorted(all_runtimes),
        "selected_engine": selected_engine,
        "selected_runtime": selected_runtime,
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
            # Redirect to composer with params (no runtime fields)
            from urllib.parse import urlencode

            params = urlencode(
                {
                    "name": form.cleaned_data["name"],
                    "description": form.cleaned_data.get("description", ""),
                    "engine": form.cleaned_data["engine"],
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


def _validate_output_references(steps_data, ci_plugin=None):
    """Validate all output references in step input configs.

    For each step's input_config values, detect output references
    and validate:
    1. Referenced step exists in the workflow
    2. Referenced step appears before the consuming step
    3. Referenced output exists in the step's outputs_schema
    """
    if not ci_plugin:
        return []

    errors = []
    # Build slug -> (index, CIStep) mapping from ordered steps
    step_map = {}  # slug -> (index, CIStep)
    ordered_steps = []

    for i, entry in enumerate(steps_data):
        try:
            ci_step = CIStep.objects.get(uuid=entry.get("id"))
            step_map[ci_step.slug] = (i, ci_step)
            ordered_steps.append((i, ci_step, entry.get("input_config", {})))
        except CIStep.DoesNotExist:
            continue

    for step_index, ci_step, input_config in ordered_steps:
        for input_name, value in input_config.items():
            if not isinstance(value, str):
                continue
            ref = ci_plugin.parse_output_reference(value)
            if not ref:
                continue
            ref_slug = ref["step_slug"]
            ref_output = ref["output_name"]

            if ref_slug not in step_map:
                errors.append(f'"{ci_step.name}" input "{input_name}": step "{ref_slug}" not found in workflow')
                continue
            ref_index, ref_step = step_map[ref_slug]
            if ref_index >= step_index:
                errors.append(f'"{ci_step.name}" input "{input_name}": step "{ref_slug}" must appear before this step')
                continue
            outputs = ref_step.outputs_schema or {}
            if ref_output not in outputs:
                errors.append(
                    f'"{ci_step.name}" input "{input_name}": output "{ref_output}" not found on step "{ref_slug}"'
                )
    return errors


class WorkflowComposerView(LoginRequiredMixin, View):
    """Step 2: Compose workflow steps with drag-and-drop ordering.

    Handles both create (GET /composer/?name=...&engine=...)
    and edit (GET /<workflow_name>/edit/) modes.
    Shows ALL active steps for the selected engine; runtime constraints
    are derived from step intersection, not upfront selection.
    """

    def _build_all_steps_context(self, engine):
        """Build all active steps for the engine, grouped by phase."""
        all_steps = (
            CIStep.objects.filter(status="active", engine=engine).select_related("repository").order_by("phase", "name")
        )

        phase_order = ["setup", "test", "build", "package"]
        phase_labels = {
            "setup": "Setup",
            "build": "Build",
            "test": "Test",
            "package": "Package",
        }
        steps_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in all_steps if s.phase == phase]
            if phase_steps:
                steps_by_phase[phase_labels[phase]] = phase_steps
        # Steps without a phase
        uncategorized = [s for s in all_steps if s.phase not in phase_order]
        if uncategorized:
            steps_by_phase["Other"] = uncategorized

        step_inputs_map = {str(s.uuid): s.inputs_schema or {} for s in all_steps}
        step_constraints_map = {str(s.uuid): s.runtime_constraints or {} for s in all_steps}

        # Output maps for step output wiring
        step_outputs_map = {str(s.uuid): s.outputs_schema or {} for s in all_steps}
        step_slug_map = {str(s.uuid): s.slug for s in all_steps}

        # Build output reference strings using CI plugin
        ci_plugin = get_ci_plugin_for_engine(engine)
        step_output_refs_map = {}
        if ci_plugin:
            for s in all_steps:
                if s.outputs_schema:
                    refs = {}
                    for output_name in s.outputs_schema:
                        refs[output_name] = ci_plugin.format_output_reference(s.slug, output_name)
                    step_output_refs_map[str(s.uuid)] = refs

        # Collect distinct runtime families for optional filter
        runtime_families = set()
        for s in all_steps:
            if s.runtime_constraints:
                for family in s.runtime_constraints:
                    if family != "*":
                        runtime_families.add(family)

        return (
            steps_by_phase,
            list(all_steps),
            step_inputs_map,
            step_constraints_map,
            sorted(runtime_families),
            step_outputs_map,
            step_output_refs_map,
            step_slug_map,
        )

    def get(self, request, workflow_name=None):
        # Edit mode: load existing workflow
        if workflow_name:
            workflow = get_object_or_404(CIWorkflow, name=workflow_name)
            name = workflow.name
            description = workflow.description
            workflow_uuid = str(workflow.uuid)
            engine = workflow.engine

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
                        "slug": ws.step.slug,
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
            engine = request.GET.get("engine", "github_actions")
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
                                "slug": ws.step.slug,
                                "order": ws.order,
                                "input_config": ws.input_config or {},
                                "expanded": False,
                            }
                        )
                except CIWorkflow.DoesNotExist:
                    pass

            if not name:
                return redirect("ci_workflows:workflow_create")

        (
            steps_by_phase,
            all_steps,
            step_inputs_map,
            step_constraints_map,
            runtime_families,
            step_outputs_map,
            step_output_refs_map,
            step_slug_map,
        ) = self._build_all_steps_context(engine)

        return render(
            request,
            "core/ci_workflows/workflow_composer.html",
            {
                "workflow_name": name,
                "workflow_description": description,
                "workflow_uuid": workflow_uuid,
                "engine": engine,
                "initial_steps_json": initial_steps_json,
                "steps_by_phase": steps_by_phase,
                "all_steps": all_steps,
                "step_inputs_map": step_inputs_map,
                "step_constraints_map": step_constraints_map,
                "runtime_families": runtime_families,
                "step_outputs_map": step_outputs_map,
                "step_output_refs_map": step_output_refs_map,
                "step_slug_map": step_slug_map,
            },
        )

    def post(self, request, workflow_name=None):
        name = request.POST.get("name", "")
        description = request.POST.get("description", "")
        steps_json = request.POST.get("steps_json", "[]")
        workflow_uuid = request.POST.get("workflow_uuid", "")

        if not name:
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
            engine_val = request.POST.get("engine") or request.GET.get("engine", "github_actions")
            (
                steps_by_phase,
                all_steps,
                step_inputs_map,
                step_constraints_map,
                runtime_families,
                step_outputs_map,
                step_output_refs_map,
                step_slug_map,
            ) = self._build_all_steps_context(engine_val)
            return render(
                request,
                "core/ci_workflows/workflow_composer.html",
                {
                    "workflow_name": name,
                    "workflow_description": description,
                    "workflow_uuid": workflow_uuid,
                    "engine": engine_val,
                    "initial_steps_json": steps_data,
                    "steps_by_phase": steps_by_phase,
                    "all_steps": all_steps,
                    "step_inputs_map": step_inputs_map,
                    "step_constraints_map": step_constraints_map,
                    "runtime_families": runtime_families,
                    "step_outputs_map": step_outputs_map,
                    "step_output_refs_map": step_output_refs_map,
                    "step_slug_map": step_slug_map,
                },
            )

        # Compute runtime constraints from steps
        step_objects = []
        for s in steps_data:
            try:
                step_objects.append(CIStep.objects.get(uuid=s.get("id")))
            except CIStep.DoesNotExist:
                continue

        constraint_result = compute_runtime_constraints(step_objects)
        if constraint_result["conflicts"]:
            for conflict in constraint_result["conflicts"]:
                messages.error(
                    request,
                    f"Runtime conflict for {conflict['runtime']}: "
                    f"steps {', '.join(conflict['steps'])} have incompatible constraints",
                )
            engine_val = request.POST.get("engine") or request.GET.get("engine", "github_actions")
            (
                steps_by_phase,
                all_steps,
                step_inputs_map,
                step_constraints_map,
                runtime_families,
                step_outputs_map,
                step_output_refs_map,
                step_slug_map,
            ) = self._build_all_steps_context(engine_val)
            return render(
                request,
                "core/ci_workflows/workflow_composer.html",
                {
                    "workflow_name": name,
                    "workflow_description": description,
                    "workflow_uuid": workflow_uuid,
                    "engine": engine_val,
                    "initial_steps_json": steps_data,
                    "steps_by_phase": steps_by_phase,
                    "all_steps": all_steps,
                    "step_inputs_map": step_inputs_map,
                    "step_constraints_map": step_constraints_map,
                    "runtime_families": runtime_families,
                    "step_outputs_map": step_outputs_map,
                    "step_output_refs_map": step_output_refs_map,
                    "step_slug_map": step_slug_map,
                },
            )

        # Validate output references
        engine_val = request.POST.get("engine") or request.GET.get("engine", "github_actions")
        ci_plugin_for_refs = get_ci_plugin_for_engine(engine_val)
        output_ref_errors = _validate_output_references(steps_data, ci_plugin_for_refs)
        if output_ref_errors:
            for err in output_ref_errors:
                messages.error(request, err)
            (
                steps_by_phase,
                all_steps,
                step_inputs_map,
                step_constraints_map,
                runtime_families,
                step_outputs_map,
                step_output_refs_map,
                step_slug_map,
            ) = self._build_all_steps_context(engine_val)
            return render(
                request,
                "core/ci_workflows/workflow_composer.html",
                {
                    "workflow_name": name,
                    "workflow_description": description,
                    "workflow_uuid": workflow_uuid,
                    "engine": engine_val,
                    "initial_steps_json": steps_data,
                    "steps_by_phase": steps_by_phase,
                    "all_steps": all_steps,
                    "step_inputs_map": step_inputs_map,
                    "step_constraints_map": step_constraints_map,
                    "runtime_families": runtime_families,
                    "step_outputs_map": step_outputs_map,
                    "step_output_refs_map": step_output_refs_map,
                    "step_slug_map": step_slug_map,
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
            workflow.runtime_constraints = constraint_result["constraints"]
            workflow.runtime_family = ""
            workflow.runtime_version = ""
            workflow.artifact_type = artifact_type
            workflow.save()
            # Replace all steps
            workflow.workflow_steps.all().delete()
        else:
            # Create mode: new workflow
            workflow = CIWorkflow.objects.create(
                name=name,
                description=description,
                runtime_constraints=constraint_result["constraints"],
                runtime_family="",
                runtime_version="",
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
                    step_commit_sha=ci_step.commit_sha,
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

        # Check for step warnings via per-workflow SHA comparison
        has_step_warnings = False
        for ws in workflow_steps:
            ws.is_archived = ws.step.status == "archived"
            ws.is_updated = ws.step_commit_sha and ws.step.commit_sha and ws.step_commit_sha != ws.step.commit_sha
            ws.change_badge = ""
            if ws.is_updated:
                if ws.step.last_change_type == "interface":
                    ws.change_badge = "interface"
                elif ws.step.last_change_type == "metadata":
                    ws.change_badge = "metadata"
                else:
                    ws.change_badge = "updated"
            if ws.is_archived or ws.is_updated:
                has_step_warnings = True

        engine = workflow.engine
        ci_plugin = get_ci_plugin_for_engine(engine)

        # Version info for UI
        draft_version = workflow.versions.filter(status=CIWorkflowVersion.Status.DRAFT).first()
        latest_version = (
            workflow.versions.filter(status=CIWorkflowVersion.Status.AUTHORIZED).order_by("-published_at").first()
        )

        # Show versioned manifest: draft first, then latest authorized, then fresh generate
        if draft_version and draft_version.manifest_content:
            manifest_yaml = draft_version.manifest_content
        elif latest_version and latest_version.manifest_content:
            manifest_yaml = latest_version.manifest_content
        else:
            manifest_yaml = ci_plugin.generate_manifest(workflow) if ci_plugin else "# No CI plugin available"

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

        # Auto-update eligible services
        from core.models import Service

        eligible_count = Service.objects.filter(
            ci_workflow=workflow,
            auto_update_patch=True,
            ci_workflow_version__isnull=False,
        ).count()

        if eligible_count > 0:
            from core.tasks import auto_update_services

            auto_update_services.enqueue(workflow_id=workflow.id, version_id=draft.id)
            messages.success(
                request,
                f"Version {version_number} published. Auto-update queued for {eligible_count} service(s).",
            )
        else:
            messages.success(request, f"Version {version_number} published.")

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
