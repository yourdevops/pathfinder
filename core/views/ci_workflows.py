"""CI Workflows views: repository management, steps catalog, runtimes."""
from collections import OrderedDict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from core.forms.ci_workflows import StepsRepoRegisterForm
from core.models import StepsRepository, CIStep, RuntimeFamily
from core.permissions import OperatorRequiredMixin, has_system_role


class StepsRepoListView(LoginRequiredMixin, View):
    """List all registered CI steps repositories."""

    def get(self, request):
        repos = StepsRepository.objects.all().order_by('name')
        can_manage = (
            request.user.is_authenticated
            and (has_system_role(request.user, 'admin') or has_system_role(request.user, 'operator'))
        )
        # Annotate step counts
        for repo in repos:
            repo.step_count = repo.steps.count()
            repo.runtime_count = repo.runtimes.count()
        return render(request, 'core/ci_workflows/repo_list.html', {
            'repos': repos,
            'can_manage': can_manage,
        })


class StepsRepoRegisterView(OperatorRequiredMixin, View):
    """Register a new CI steps repository."""

    def get(self, request):
        form = StepsRepoRegisterForm()
        return render(request, 'core/ci_workflows/repo_register.html', {
            'form': form,
        })

    def post(self, request):
        form = StepsRepoRegisterForm(request.POST)
        if form.is_valid():
            repo = StepsRepository.objects.create(
                name=form.cleaned_data['name'],
                git_url=form.cleaned_data['git_url'],
                connection=form.cleaned_data.get('connection'),
                created_by=request.user.username,
            )
            # Enqueue scan task
            from core.tasks import scan_steps_repository
            scan_steps_repository.enqueue(repository_id=repo.id)
            return redirect('ci_workflows:repo_detail', repo_name=repo.name)
        return render(request, 'core/ci_workflows/repo_register.html', {
            'form': form,
        })


class StepsRepoDetailView(LoginRequiredMixin, View):
    """Show repository details with imported steps and runtimes."""

    def get(self, request, repo_name):
        repo = get_object_or_404(StepsRepository, name=repo_name)
        steps = repo.steps.all().order_by('phase', 'name')
        runtimes = repo.runtimes.all().order_by('name')

        # Group steps by phase
        phase_order = ['setup', 'build', 'test', 'package']
        phase_labels = {
            'setup': 'Setup',
            'build': 'Build',
            'test': 'Test',
            'package': 'Package',
        }
        steps_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in steps if s.phase == phase]
            if phase_steps:
                steps_by_phase[phase_labels[phase]] = phase_steps
        # Steps without a phase
        uncategorized = [s for s in steps if s.phase not in phase_order]
        if uncategorized:
            steps_by_phase['Other'] = uncategorized

        can_manage = (
            request.user.is_authenticated
            and (has_system_role(request.user, 'admin') or has_system_role(request.user, 'operator'))
        )

        return render(request, 'core/ci_workflows/repo_detail.html', {
            'repo': repo,
            'steps_by_phase': steps_by_phase,
            'runtimes': runtimes,
            'total_steps': steps.count(),
            'can_manage': can_manage,
        })


class StepsRepoScanView(OperatorRequiredMixin, View):
    """Trigger a rescan of a steps repository."""

    def post(self, request, repo_name):
        repo = get_object_or_404(StepsRepository, name=repo_name)
        repo.scan_status = 'scanning'
        repo.scan_error = ''
        repo.save(update_fields=['scan_status', 'scan_error'])

        from core.tasks import scan_steps_repository
        scan_steps_repository.enqueue(repository_id=repo.id)

        if request.headers.get('HX-Request'):
            return render(request, 'core/ci_workflows/_scan_status.html', {
                'repo': repo,
            })
        return redirect('ci_workflows:repo_detail', repo_name=repo.name)


class StepsRepoScanStatusView(LoginRequiredMixin, View):
    """HTMX partial for scan status polling."""

    def get(self, request, repo_name):
        repo = get_object_or_404(StepsRepository, name=repo_name)
        return render(request, 'core/ci_workflows/_scan_status.html', {
            'repo': repo,
        })


class StepsCatalogView(LoginRequiredMixin, View):
    """Browse all imported CI steps organized by phase."""

    def get(self, request):
        steps = CIStep.objects.all().select_related('repository').order_by('phase', 'name')

        phase_order = ['setup', 'build', 'test', 'package']
        phase_labels = {
            'setup': 'Setup',
            'build': 'Build',
            'test': 'Test',
            'package': 'Package',
        }
        steps_by_phase = OrderedDict()
        for phase in phase_order:
            phase_steps = [s for s in steps if s.phase == phase]
            steps_by_phase[phase_labels[phase]] = phase_steps
        # Uncategorized
        uncategorized = [s for s in steps if s.phase not in phase_order]
        if uncategorized:
            steps_by_phase['Other'] = uncategorized

        return render(request, 'core/ci_workflows/steps_catalog.html', {
            'steps_by_phase': steps_by_phase,
            'total_steps': steps.count(),
        })


class StepDetailView(LoginRequiredMixin, View):
    """Show full details for a single CI step."""

    def get(self, request, step_uuid):
        step = get_object_or_404(CIStep, uuid=step_uuid)
        return render(request, 'core/ci_workflows/step_detail.html', {
            'step': step,
        })


class RuntimesView(LoginRequiredMixin, View):
    """List all runtime families grouped by repository."""

    def get(self, request):
        runtimes = RuntimeFamily.objects.all().select_related('repository').order_by('repository__name', 'name')

        # Group by repository
        runtimes_by_repo = OrderedDict()
        for rt in runtimes:
            repo_name = rt.repository.name
            if repo_name not in runtimes_by_repo:
                runtimes_by_repo[repo_name] = []
            runtimes_by_repo[repo_name].append(rt)

        return render(request, 'core/ci_workflows/runtimes.html', {
            'runtimes_by_repo': runtimes_by_repo,
            'total_runtimes': runtimes.count(),
        })
