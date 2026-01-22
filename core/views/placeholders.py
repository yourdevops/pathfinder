from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class BlueprintsListView(LoginRequiredMixin, View):
    """Placeholder for blueprints list.

    Will be replaced by actual implementation in Phase 4.
    For now, shows empty state to satisfy FNDN-12 (authenticated
    users can view blueprints list).
    """
    template_name = 'core/placeholders/blueprints.html'

    def get(self, request):
        return render(request, self.template_name, {
            'blueprints': [],  # Empty for now
        })


class ConnectionsListView(LoginRequiredMixin, View):
    """Placeholder for connections list.

    Will be replaced by actual implementation in Phase 3.
    For now, shows empty state to satisfy FNDN-13 (authenticated
    users can view connections list).
    """
    template_name = 'core/placeholders/connections.html'

    def get(self, request):
        return render(request, self.template_name, {
            'connections': [],  # Empty for now
        })
