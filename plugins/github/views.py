"""GitHub plugin views."""

import json
import secrets

import requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from core.models import IntegrationConnection, SiteConfiguration
from core.permissions import OperatorRequiredMixin

from .forms import GitHubConnectionForm
from .plugin import GitHubPlugin


def get_default_app_name():
    """Generate a default GitHub App name based on hostname."""
    config = SiteConfiguration.get_instance()
    if config.external_url:
        from urllib.parse import urlparse

        parsed = urlparse(config.external_url)
        hostname = parsed.netloc.split(":")[0]  # Remove port if present
        # Create a readable name from hostname
        name_parts = hostname.replace(".", "-").split("-")
        return f"pathfinder-{'-'.join(name_parts[:2])}"
    return "Pathfinder"


def get_default_connection_name(org_name=None):
    """Generate a default connection name."""
    base = f"github-{org_name}" if org_name else "github"
    # Check for uniqueness
    name = base
    counter = 1
    while IntegrationConnection.objects.filter(name=name).exists():
        name = f"{base}-{counter}"
        counter += 1
    return name


class GitHubConnectionCreateView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Single-page GitHub connection creation."""

    template_name = "github/create.html"

    def get_context(self, form=None):
        config = SiteConfiguration.get_instance()
        external_url_configured = bool(config.external_url)

        if form is None:
            initial = {
                "name": get_default_connection_name(),
                "app_name": get_default_app_name(),
                "auth_type": "app",
                "setup_mode": "automatic" if external_url_configured else "manual",
            }
            form = GitHubConnectionForm(initial=initial)

        return {
            "form": form,
            "plugin": GitHubPlugin(),
            "external_url_configured": external_url_configured,
            "external_url": config.external_url,
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        form = GitHubConnectionForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, self.get_context(form))

        auth_type = form.cleaned_data["auth_type"]
        setup_mode = form.cleaned_data.get("setup_mode")

        # GitHub App with automatic setup - redirect to manifest flow
        if auth_type == "app" and setup_mode == "automatic":
            return self._initiate_manifest_flow(request, form.cleaned_data)

        # Manual GitHub App or PAT - create connection directly
        return self._create_connection(request, form.cleaned_data)

    def _initiate_manifest_flow(self, request, data):
        """Start the GitHub App manifest flow."""
        config = SiteConfiguration.get_instance()
        if not config.external_url:
            messages.error(
                request,
                "External URL must be configured for automatic GitHub App setup.",
            )
            return redirect("github:create")

        # Store pending connection data in session
        state = secrets.token_urlsafe(32)
        request.session["github_manifest_state"] = state
        request.session["github_manifest_data"] = {
            "name": data["name"],
            "organization": data["organization"],
            "app_name": data.get("app_name") or f"pathfinder-{data['organization']}",
            "base_url": data.get("base_url", ""),
        }

        # Build the manifest
        manifest = self._build_manifest(config.external_url, data)

        # Determine GitHub URL (support for GitHub Enterprise)
        github_base = data.get("base_url", "").rstrip("/") or "https://github.com"
        # For GHE, the API URL format is different from the web URL
        if "api/v3" in github_base:
            github_base = github_base.replace("/api/v3", "")

        # Build the manifest creation URL
        org = data["organization"]
        manifest_url = f"{github_base}/organizations/{org}/settings/apps/new"

        # Render an intermediate page that auto-posts to GitHub
        return render(
            request,
            "github/manifest_redirect.html",
            {
                "manifest_url": manifest_url,
                "manifest_json": json.dumps(manifest),
                "organization": org,
            },
        )

    def _build_manifest(self, external_url, data):
        """Build the GitHub App manifest JSON."""
        external_url = external_url.rstrip("/")
        # Use provided app_name, or generate from organization
        app_name = data.get("app_name")
        if not app_name and data.get("organization"):
            app_name = f"pathfinder-{data['organization']}"
        if not app_name:
            app_name = get_default_app_name()

        return {
            "name": app_name,
            "url": external_url,
            "hook_attributes": {
                "url": f"{external_url}/plugins/github/webhook/",
                "active": True,
            },
            "redirect_url": f"{external_url}/plugins/github/manifest/callback/",
            "callback_urls": [f"{external_url}/plugins/github/webhook/"],
            "public": False,
            "default_permissions": {
                "contents": "write",
                "metadata": "read",
                "pull_requests": "write",
                "workflows": "write",
                "actions": "read",
            },
            "default_events": [
                "push",
                "pull_request",
                "workflow_run",
            ],
        }

    def _create_connection(self, request, data):
        """Create connection with provided credentials."""
        auth_type = data["auth_type"]

        config = {
            "auth_type": auth_type,
        }

        if auth_type == "app":
            config.update(
                {
                    "app_id": data["app_id"],
                    "private_key": data["private_key"],
                    "installation_id": data["installation_id"],
                }
            )
        else:  # token
            config["personal_token"] = data["personal_token"]

        # Common optional fields
        if data.get("base_url"):
            config["base_url"] = data["base_url"]
        if data.get("organization"):
            config["organization"] = data["organization"]

        # Create the connection
        connection = IntegrationConnection(
            name=data["name"],
            plugin_name="github",
            description=f"GitHub {'App' if auth_type == 'app' else 'PAT'} connection",
            status="active",
            created_by=request.user.username,
        )
        connection.set_config(config)
        connection.save()

        messages.success(request, f'GitHub connection "{connection.name}" created successfully.')
        return redirect("connections:detail", connection_name=connection.name)


class GitHubManifestCallbackView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Handle callback from GitHub after app manifest creation."""

    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")

        # Validate state
        stored_state = request.session.get("github_manifest_state")
        if not state or state != stored_state:
            messages.error(request, "Invalid state parameter. Please try again.")
            return redirect("github:create")

        if not code:
            messages.error(request, "No authorization code received from GitHub.")
            return redirect("github:create")

        # Get stored data
        manifest_data = request.session.get("github_manifest_data", {})
        if not manifest_data:
            messages.error(request, "Session expired. Please try again.")
            return redirect("github:create")

        # Exchange code for app credentials
        github_base = manifest_data.get("base_url", "").rstrip("/") or "https://api.github.com"
        # Convert web URL to API URL if needed
        if not github_base.startswith("https://api.") and "api/v3" not in github_base:
            github_base = github_base.replace("https://", "https://api.")
            if not github_base.endswith("/api/v3"):
                github_base = f"{github_base}/api/v3" if "github.com" not in github_base else "https://api.github.com"

        conversion_url = f"{github_base}/app-manifests/{code}/conversions"

        try:
            response = requests.post(
                conversion_url,
                headers={"Accept": "application/vnd.github+json"},
                timeout=30,
            )
            response.raise_for_status()
            app_data = response.json()
        except requests.RequestException as e:
            messages.error(request, f"Failed to complete GitHub App setup: {e}")
            return redirect("github:create")

        # Extract credentials from response
        app_id = str(app_data.get("id", ""))
        private_key = app_data.get("pem", "")
        webhook_secret = app_data.get("webhook_secret", "")
        client_id = app_data.get("client_id", "")
        client_secret = app_data.get("client_secret", "")

        if not app_id or not private_key:
            messages.error(request, "GitHub did not return valid app credentials.")
            return redirect("github:create")

        # Create connection in pending status (needs installation)
        config = {
            "auth_type": "app",
            "app_id": app_id,
            "private_key": private_key,
            "webhook_secret": webhook_secret,
            "client_id": client_id,
            "client_secret": client_secret,
            "organization": manifest_data.get("organization", ""),
        }
        if manifest_data.get("base_url"):
            config["base_url"] = manifest_data["base_url"]

        connection = IntegrationConnection(
            name=manifest_data["name"],
            plugin_name="github",
            description=f"GitHub App for {manifest_data.get('organization', 'unknown')}",
            status="pending",  # Pending until installed
            created_by=request.user.username,
        )
        connection.set_config(config)
        connection.save()

        # Clean up session
        del request.session["github_manifest_state"]
        del request.session["github_manifest_data"]

        # Redirect to installation
        # The app needs to be installed on the organization
        github_web = manifest_data.get("base_url", "").rstrip("/") or "https://github.com"
        if "api" in github_web:
            github_web = github_web.replace("api.", "").replace("/api/v3", "")

        app_slug = app_data.get("slug", "")
        if app_slug:
            install_url = f"{github_web}/apps/{app_slug}/installations/new"
            messages.info(
                request,
                f"GitHub App created! Please install it on your organization to complete setup. "
                f'<a href="{install_url}" target="_blank" class="underline">Install App</a>',
            )
        else:
            messages.success(
                request,
                "GitHub App created successfully. Please install it on your organization.",
            )

        return redirect("connections:detail", connection_name=connection.name)


class GitHubInstallationCallbackView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Handle callback after GitHub App installation."""

    def get(self, request):
        installation_id = request.GET.get("installation_id")

        if not installation_id:
            messages.error(request, "No installation ID received.")
            return redirect("connections:list")

        # Find the pending connection for this installation
        # This is tricky - we need to match by app_id or other criteria
        # For now, we'll update the most recent pending GitHub connection
        try:
            connection = (
                IntegrationConnection.objects.filter(plugin_name="github", status="pending")
                .order_by("-created_at")
                .first()
            )

            if connection:
                config = connection.get_config()
                config["installation_id"] = installation_id
                connection.set_config(config)
                connection.status = "active"
                connection.save()
                messages.success(request, "GitHub App installed successfully on your organization!")
                return redirect("connections:detail", connection_name=connection.name)
        except Exception as e:
            messages.error(request, f"Error completing installation: {e}")

        return redirect("connections:list")
