from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


class ConnectionsListView(LoginRequiredMixin, View):
    """Placeholder for connections list.

    Will be replaced by actual implementation in Phase 3.
    For now, shows empty state to satisfy FNDN-13 (authenticated
    users can view connections list).
    """

    template_name = "core/placeholders/connections.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "connections": [],  # Empty for now
            },
        )


class ServicesPlaceholderView(LoginRequiredMixin, View):
    """Placeholder for services list.

    Services will be the deployed instances from the Service Catalog.
    Will be implemented in Phase 5.
    """

    template_name = "core/placeholders/services.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "title": "Services",
            },
        )


class ResourcesPlaceholderView(LoginRequiredMixin, View):
    """Placeholder for infrastructure resources.

    Resources will be infrastructure components (databases, caches, etc.)
    Will be implemented in a future version.
    """

    template_name = "core/placeholders/resources.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "title": "Resources",
            },
        )
