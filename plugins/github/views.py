"""GitHub plugin views."""

import json
import re
import secrets
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from core.models import IntegrationConnection, SiteConfiguration
from core.permissions import OperatorRequiredMixin

from .forms import GitHubConnectionForm
from .plugin import GitHubPlugin

_CREATE_URL_NAME = "github:create"


def get_default_app_name():
    """Generate a default GitHub App name based on hostname."""
    config = SiteConfiguration.get_instance()
    if config.external_url:
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
            return redirect(_CREATE_URL_NAME)

        # Store pending connection data in session
        state = secrets.token_urlsafe(32)
        request.session["github_manifest"] = {
            "state": state,
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
        response = render(
            request,
            "github/manifest_redirect.html",
            {
                "manifest_url": f"{manifest_url}?{urlencode({'state': state})}",
                "manifest_json": json.dumps(manifest),
                "organization": org,
            },
        )

        # Override CSP to allow form-action to the GitHub manifest URL.
        # Django's CSP middleware reads response._csp_config if set.
        parsed = urlparse(manifest_url)
        target_origin = f"{parsed.scheme}://{parsed.netloc}"
        csp_config = {k: list(v) for k, v in settings.SECURE_CSP.items()}
        csp_config["form-action"] = [*csp_config.get("form-action", []), target_origin]
        response._csp_config = csp_config

        return response

    def _build_manifest(self, external_url, data):
        """Build the GitHub App manifest JSON."""
        external_url = external_url.rstrip("/")
        # Use provided app_name, or generate from organization
        app_name = data.get("app_name")
        if not app_name and data.get("organization"):
            app_name = f"pathfinder-{data['organization']}"
        if not app_name:
            app_name = get_default_app_name()

        callback_path = reverse("github:manifest_callback")
        install_path = reverse("github:installation_callback")
        webhook_path = reverse("github:webhook")

        return {
            "name": app_name,
            "url": external_url,
            "hook_attributes": {
                "url": f"{external_url}{webhook_path}",
                "active": True,
            },
            "redirect_url": f"{external_url}{callback_path}",
            "setup_url": f"{external_url}{install_path}",
            "setup_on_update": True,
            "callback_urls": [f"{external_url}{webhook_path}"],
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
        return redirect(_CREATE_URL_NAME, connection_name=connection.name)


class GitHubManifestCallbackView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Handle callback from GitHub after app manifest creation."""

    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")

        # Retrieve and consume session data atomically
        manifest_data = request.session.pop("github_manifest", None)
        if not manifest_data:
            messages.error(request, "Session expired. Please try connecting again.")
            return redirect(_CREATE_URL_NAME)

        # Validate state
        if not state or state != manifest_data.get("state"):
            messages.error(request, "Invalid state parameter. Please try again.")
            return redirect(_CREATE_URL_NAME)

        # Validate code format (alphanumeric) to prevent URL injection/SSRF
        if not code or not re.fullmatch(r"[a-zA-Z0-9_\-]+", code):
            messages.error(request, "No authorization code received from GitHub.")
            return redirect(_CREATE_URL_NAME)

        # Exchange code for app credentials
        app_data = self._exchange_code(manifest_data, code)
        if not app_data:
            messages.error(request, "Failed to complete GitHub App setup.")
            return redirect(_CREATE_URL_NAME)

        # Extract and validate credentials
        app_id = str(app_data.get("id", ""))
        private_key = app_data.get("pem", "")
        if not app_id or not private_key:
            messages.error(request, "GitHub did not return valid app credentials.")
            return redirect(_CREATE_URL_NAME)

        connection = self._create_connection(request, manifest_data, app_data, app_id, private_key)

        # Store connection ID in session for installation callback matching
        request.session["github_install"] = {"connection_id": connection.id}

        return self._redirect_to_installation(request, manifest_data, app_data, connection)

    @staticmethod
    def _get_api_base(base_url):
        """Resolve a base URL to the GitHub API root."""
        github_base = base_url.rstrip("/") or "https://api.github.com"
        if github_base.startswith("https://api.") or "api/v3" in github_base:
            return github_base
        github_base = github_base.replace("https://", "https://api.")
        if "github.com" in github_base:
            return "https://api.github.com"
        return f"{github_base}/api/v3"

    def _exchange_code(self, manifest_data, code):
        """Exchange the manifest code for app credentials via GitHub API."""
        github_base = self._get_api_base(manifest_data.get("base_url", ""))
        conversion_url = f"{github_base}/app-manifests/{code}/conversions"

        try:
            api_response = requests.post(
                conversion_url,
                headers={"Accept": "application/vnd.github+json"},
                timeout=30,
            )
            api_response.raise_for_status()
            return api_response.json()
        except requests.RequestException:
            return None

    @staticmethod
    def _create_connection(request, manifest_data, app_data, app_id, private_key):
        """Create an IntegrationConnection in pending status."""
        config = {
            "auth_type": "app",
            "app_id": app_id,
            "private_key": private_key,
            "webhook_secret": app_data.get("webhook_secret", ""),
            "client_id": app_data.get("client_id", ""),
            "client_secret": app_data.get("client_secret", ""),
            "organization": manifest_data.get("organization", ""),
        }
        if manifest_data.get("base_url"):
            config["base_url"] = manifest_data["base_url"]

        connection = IntegrationConnection(
            name=manifest_data["name"],
            plugin_name="github",
            description=f"GitHub App for {manifest_data.get('organization', 'unknown')}",
            status="pending",
            created_by=request.user.username,
        )
        connection.set_config(config)
        connection.save()
        return connection

    @staticmethod
    def _redirect_to_installation(request, manifest_data, app_data, connection):
        """Redirect user to install the newly created GitHub App."""
        github_web = manifest_data.get("base_url", "").rstrip("/") or "https://github.com"
        if "api" in github_web:
            github_web = github_web.replace("api.", "").replace("/api/v3", "")

        app_slug = app_data.get("slug", "")
        if app_slug:
            install_url = f"{github_web}/apps/{app_slug}/installations/new"
            owner_id = app_data.get("owner", {}).get("id")
            if owner_id:
                install_url += f"?target_id={owner_id}"
            return redirect(install_url)

        messages.success(
            request,
            "GitHub App created successfully. Please install it on your organization.",
        )
        return redirect("connections:detail", connection_name=connection.name)


class GitHubInstallationCallbackView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Handle callback after GitHub App installation."""

    def get(self, request):
        raw_installation_id = request.GET.get("installation_id")
        # Validate installation_id is numeric to prevent injection
        installation_id = raw_installation_id if raw_installation_id and raw_installation_id.isdigit() else None

        # Retrieve and consume session data
        install_data = request.session.pop("github_install", None)

        if installation_id and install_data:
            # Best case: session + installation_id — match by stored connection ID
            try:
                connection = IntegrationConnection.objects.get(
                    id=install_data["connection_id"],
                )
                config = connection.get_config()
                config["installation_id"] = installation_id
                connection.set_config(config)
                connection.status = "active"
                connection.save()
                messages.success(request, "GitHub App installed successfully on your organization!")
                return redirect("connections:detail", connection_name=connection.name)
            except IntegrationConnection.DoesNotExist:
                messages.error(request, "Connection record not found. Please try again.")
                return redirect("connections:list")
        elif installation_id:
            # No session but have installation_id — webhook should handle it
            messages.info(
                request,
                "Installation received. The connection will be updated shortly.",
            )
        else:
            messages.info(request, "App setup in progress. Installation will complete via webhook.")

        return redirect("connections:list")
