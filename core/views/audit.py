from django.shortcuts import render
from django.views import View
from django.core.paginator import Paginator
from auditlog.models import LogEntry

from ..decorators import AdminRequiredMixin


class AuditLogView(AdminRequiredMixin, View):
    """Display audit log entries."""
    template_name = 'core/audit/list.html'
    paginate_by = 50

    def get(self, request):
        entries = LogEntry.objects.all().select_related('actor', 'content_type').order_by('-timestamp')

        # Basic filtering
        action_filter = request.GET.get('action')
        if action_filter:
            entries = entries.filter(action=int(action_filter))

        model_filter = request.GET.get('model')
        if model_filter:
            entries = entries.filter(content_type__model=model_filter)

        # Pagination
        paginator = Paginator(entries, self.paginate_by)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'action_filter': action_filter,
            'model_filter': model_filter,
        })
