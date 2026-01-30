"""CI Workflows views: repository management, steps catalog, runtimes, workflow composer."""

import json
from collections import OrderedDict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from core.ci_manifest import generate_github_actions_manifest, get_compatible_steps
from core.forms.ci_workflows import StepsRepoRegisterForm, WorkflowCreateForm
from core.models import (
    CIStep,
    CIWorkflow,
    CIWorkflowStep,
    RuntimeFamily,
    StepsRepository,
)
from core.permissions import OperatorRequiredMixin, has_system_role


class StepsRepoListView(LoginRequiredMixin, View):
    """List all registered CI steps repositories."""

    def get(self, request):
        repos = StepsRepository.objects.all().order_by("name")
        can_manage = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )
        # Annotate step counts
        for repo in repos:
            repo.step_count = repo.steps.count()
            repo.runtime_count = repo.runtimes.count()
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


class StepsCatalogView(LoginRequiredMixin, View):
    """Browse all imported CI steps organized by phase."""

    def get(self, request):
        steps = CIStep.objects.all().select_related("repository").order_by("phase", "name")

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
            steps_by_phase[phase_labels[phase]] = phase_steps
        # Uncategorized
        uncategorized = [s for s in steps if s.phase not in phase_order]
        if uncategorized:
            steps_by_phase["Other"] = uncategorized

        return render(
            request,
            "core/ci_workflows/steps_catalog.html",
            {
                "steps_by_phase": steps_by_phase,
                "total_steps": steps.count(),
            },
        )


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


class RuntimesView(LoginRequiredMixin, View):
    """List all runtime families grouped by repository."""

    def get(self, request):
        runtimes = RuntimeFamily.objects.all().select_related("repository").order_by("repository__name", "name")

        # Group by repository
        runtimes_by_repo = OrderedDict()
        for rt in runtimes:
            repo_name = rt.repository.name
            if repo_name not in runtimes_by_repo:
                runtimes_by_repo[repo_name] = []
            runtimes_by_repo[repo_name].append(rt)

        return render(
            request,
            "core/ci_workflows/runtimes.html",
            {
                "runtimes_by_repo": runtimes_by_repo,
                "total_runtimes": runtimes.count(),
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
    """Step 2: Compose workflow steps with drag-and-drop ordering."""

    def get(self, request):
        name = request.GET.get("name", "")
        description = request.GET.get("description", "")
        runtime_family = request.GET.get("runtime_family", "")
        runtime_version = request.GET.get("runtime_version", "")

        if not name or not runtime_family or not runtime_version:
            return redirect("ci_workflows:workflow_create")

        compatible, incompatible = get_compatible_steps(runtime_family, runtime_version)

        # Group compatible steps by phase
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

        return render(
            request,
            "core/ci_workflows/workflow_composer.html",
            {
                "workflow_name": name,
                "workflow_description": description,
                "runtime_family": runtime_family,
                "runtime_version": runtime_version,
                "compatible_by_phase": compatible_by_phase,
                "incompatible_steps": incompatible,
                "compatible_steps": compatible,
            },
        )

    def post(self, request):
        name = request.POST.get("name", "")
        description = request.POST.get("description", "")
        runtime_family = request.POST.get("runtime_family", "")
        runtime_version = request.POST.get("runtime_version", "")
        steps_json = request.POST.get("steps_json", "[]")

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

        # Create the workflow
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

        return render(
            request,
            "core/ci_workflows/_compatible_steps.html",
            {
                "compatible_by_phase": compatible_by_phase,
                "incompatible_steps": incompatible,
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
        manifest_yaml = generate_github_actions_manifest(workflow)

        can_delete = request.user.is_authenticated and (
            has_system_role(request.user, "admin") or has_system_role(request.user, "operator")
        )

        return render(
            request,
            "core/ci_workflows/workflow_detail.html",
            {
                "workflow": workflow,
                "workflow_steps": workflow_steps,
                "manifest_yaml": manifest_yaml,
                "can_delete": can_delete,
            },
        )


class WorkflowManifestView(LoginRequiredMixin, View):
    """HTMX endpoint: return manifest preview partial."""

    def get(self, request, workflow_name):
        workflow = get_object_or_404(CIWorkflow, name=workflow_name)
        manifest_yaml = generate_github_actions_manifest(workflow)
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
