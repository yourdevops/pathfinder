"""Docker plugin views."""

from django.shortcuts import redirect
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from core.models import IntegrationConnection
from core.permissions import OperatorRequiredMixin
from .forms import DockerConnectionForm


class DockerConnectionCreateView(LoginRequiredMixin, OperatorRequiredMixin, FormView):
    """Single-page form for Docker connection creation."""

    template_name = "docker/create.html"
    form_class = DockerConnectionForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .plugin import DockerPlugin

        context["plugin"] = DockerPlugin()
        return context

    def form_valid(self, form):
        data = form.cleaned_data

        # Build config
        config = {
            "socket_path": data["socket_path"],
            "tls_enabled": data.get("tls_enabled", False),
        }
        if data.get("tls_ca_cert"):
            config["tls_ca_cert"] = data["tls_ca_cert"]
        if data.get("tls_client_cert"):
            config["tls_client_cert"] = data["tls_client_cert"]
        if data.get("tls_client_key"):
            config["tls_client_key"] = data["tls_client_key"]

        # Create connection
        connection = IntegrationConnection(
            name=data["name"],
            description=data.get("description", ""),
            plugin_name="docker",
            created_by=self.request.user.username,
        )
        connection.set_config(config)
        connection.save()

        messages.success(
            self.request, f'Docker connection "{connection.name}" created successfully.'
        )
        return redirect("connections:detail", connection_name=connection.name)
