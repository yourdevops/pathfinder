# SPDX-License-Identifier: Apache-2.0
"""
Plugin framework base classes.

This module provides the abstract BasePlugin class and the PluginRegistry
singleton that manages plugin registration and discovery.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Optional


class PluginRegistry:
    """
    Singleton registry for managing plugin instances.

    Plugins register themselves with the registry, typically during
    module import. The registry provides methods to retrieve plugins
    by name or category.
    """

    _plugins: dict[str, "BasePlugin"] = {}

    @classmethod
    def register(cls, plugin: "BasePlugin") -> None:
        """
        Register a plugin instance.

        Args:
            plugin: The plugin instance to register.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        if plugin.name in cls._plugins:
            raise ValueError(f"Plugin '{plugin.name}' is already registered")
        cls._plugins[plugin.name] = plugin

    @classmethod
    def get(cls, name: str) -> Optional["BasePlugin"]:
        """
        Get a plugin by name.

        Args:
            name: The unique plugin identifier.

        Returns:
            The plugin instance or None if not found.
        """
        return cls._plugins.get(name)

    @classmethod
    def all(cls) -> dict[str, "BasePlugin"]:
        """
        Get all registered plugins.

        Returns:
            Dictionary mapping plugin names to instances.
        """
        return cls._plugins.copy()

    @classmethod
    def by_category(cls, category: str) -> list["BasePlugin"]:
        """
        Get plugins filtered by category.

        Args:
            category: The category to filter by ('scm', 'ci', 'deploy').

        Returns:
            List of plugins matching the category.
        """
        return [p for p in cls._plugins.values() if p.category == category]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins. Primarily for testing."""
        cls._plugins.clear()


# Module-level registry instance for convenience
registry = PluginRegistry


class CICapableMixin:
    """Mixin for plugins that provide CI engine capabilities."""

    @property
    def engine_name(self) -> str:
        """CI engine identifier, e.g., 'github_actions'."""
        raise NotImplementedError

    @property
    def engine_display_name(self) -> str:
        """Human-readable engine name, e.g., 'GitHub Actions'."""
        raise NotImplementedError

    @property
    def engine_file_name(self) -> str:
        """Filename to discover in step repos, e.g., 'action.yml'."""
        raise NotImplementedError

    def parse_step_file(self, file_content: dict) -> dict:
        """Parse engine-native step file and extract x-pathfinder metadata.

        Returns dict with: name, description, inputs, phase, runtime_constraints,
        tags, produces, raw_metadata.
        """
        raise NotImplementedError

    def derive_step_slug(self, file_content: dict, directory_path: str) -> str:
        """Derive a URL-safe slug for a step using three-tier fallback.

        Resolution order:
          1. x-pathfinder.name (Pathfinder-specific metadata)
          2. Engine-native name (plugin-specific, e.g., action.yml 'name' field)
          3. Full relative directory path (e.g., 'setup/python' -> 'setup-python')

        Args:
            file_content: Parsed YAML dict of the step definition file.
            directory_path: Relative path from repo root to the step directory.

        Returns:
            Slug string, or empty string if none could be derived.
        """
        raise NotImplementedError

    def generate_manifest(self, workflow, version: str | None = None) -> str:
        """Generate CI manifest YAML string for a CIWorkflow instance.

        Args:
            workflow: CIWorkflow instance.
            version: Optional version string for the manifest header.
        """
        raise NotImplementedError

    def manifest_id(self, workflow) -> str:
        """Return manifest identifier (e.g., .github/workflows/ci-python-uv.yml).

        Based on workflow name, not service name."""
        raise NotImplementedError

    def extract_manifest_id(self, run_data: dict) -> str | None:
        """Extract manifest identifier from CI run data.

        Returns None if not Pathfinder-managed."""
        raise NotImplementedError

    def get_manifest_id_pattern(self) -> re.Pattern:
        """Return regex pattern for validating manifest IDs."""
        raise NotImplementedError

    def map_run_status(self, status: str, conclusion: str | None) -> str:
        """Map CI engine run status/conclusion to Build status string.

        Args:
            status: Engine-specific run status string.
            conclusion: Engine-specific conclusion string (may be None).

        Returns:
            One of: 'pending', 'running', 'success', 'failed', 'cancelled'.
        """
        raise NotImplementedError

    def fetch_manifest_content(self, config: dict, repo_name: str, manifest_id: str, commit_sha: str) -> str | None:
        """Fetch manifest file content from repo at a specific commit.

        Returns None if file not found."""
        raise NotImplementedError

    def check_branch_protection(self, config: dict, repo_name: str, branch: str) -> dict:
        """Check branch protection rules for a repository branch.

        Returns dict with:
            valid: bool -- True if all required rules are in place
            rules: dict -- individual rule check results
            message: str -- human-readable summary
        """
        raise NotImplementedError

    def find_open_pr(self, config: dict, repo_name: str, branch_name: str) -> dict | None:
        """Find an open PR for the given branch.

        Returns dict with number, html_url, title if found, or None.
        """
        raise NotImplementedError

    def resolve_artifact_ref(self, config: dict, repo_name: str, run_id: int) -> str:
        """Resolve actual artifact reference (container image ref) from CI engine API.

        Queries the CI engine's container registry or packages API to find the
        container image produced by a specific CI run.

        Args:
            config: Decrypted connection configuration.
            repo_name: Full repository name (owner/repo).
            run_id: CI engine run identifier.

        Returns:
            Image reference string (e.g., 'ghcr.io/owner/repo:sha-abc1234')
            or empty string if no artifact found.
        """
        raise NotImplementedError

    def format_step_id(self, step_slug: str) -> str:
        """Return the engine-native step ID derived from slug.

        Args:
            step_slug: The URL-safe slug of the step.

        Returns:
            Engine-native step ID string.
        """
        raise NotImplementedError

    def format_output_reference(self, step_slug: str, output_name: str) -> str:
        """Return the engine-native output reference string for copy-paste.

        Args:
            step_slug: The URL-safe slug of the step.
            output_name: The name of the output.

        Returns:
            Engine-native output reference expression.
        """
        raise NotImplementedError

    def parse_output_reference(self, value: str) -> dict | None:
        """Parse an input value to check if it matches the engine's output reference pattern.

        Args:
            value: The input value string to check.

        Returns:
            Dict with 'step_slug' and 'output_name' if matched, None otherwise.
        """
        raise NotImplementedError

    def provision_ci_variables(self, config: dict, repo_name: str, variables: dict[str, str]) -> dict:
        """Provision CI-level variables on the repository. Idempotent (create or update).

        Args:
            config: Decrypted connection configuration.
            repo_name: Full repository name (owner/repo).
            variables: Dict of variable name -> value (e.g., {"PTF_PROJECT": "my-project"}).

        Returns:
            Dict with status per variable: {"PTF_PROJECT": "created", "PTF_SERVICE": "updated"}
        """
        raise NotImplementedError


class BasePlugin(ABC):
    """
    Abstract base class for all integration plugins.

    Subclasses must implement all abstract methods and define
    the required class attributes.

    Attributes:
        name: Unique plugin identifier (e.g., 'github', 'docker').
        display_name: Human-readable name for UI.
        category: Plugin category ('scm', 'ci', 'deploy').
        capabilities: List of capabilities this plugin provides.
        icon: CSS class name for the plugin icon.
        sensitive_field_patterns: Field name patterns that should be encrypted.
    """

    name: str
    display_name: str
    category: str  # 'scm', 'ci', 'deploy'
    capabilities: list[str] = []
    icon: str = ""

    # Fields matching these patterns will be encrypted
    sensitive_field_patterns: list[str] = [
        "password",
        "token",
        "secret",
        "private_key",
        "api_key",
        "client_secret",
    ]

    def is_sensitive_field(self, field_name: str) -> bool:
        """
        Check if a field should be encrypted based on its name.

        Args:
            field_name: The field name to check.

        Returns:
            True if the field matches any sensitive pattern.
        """
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in self.sensitive_field_patterns)

    def get_clone_credentials(self, config: dict[str, Any]) -> tuple[str, str] | None:
        """Return credentials for HTTPS git clone operations.

        Plugins override this to provide the appropriate credentials
        for their auth type. Core code calls this without knowing the
        auth mechanism, keeping core plugin-agnostic.

        Args:
            config: The decrypted configuration dictionary.

        Returns:
            (username, token) tuple for URL embedding, or None if unavailable.
            The URL will be built as: https://{username}:{token}@host/path
        """
        # Default: PAT-style — token as username, empty password
        for key in ("personal_token", "token", "access_token"):
            if config.get(key):
                return (config[key], "")
        return None

    def get_webhook_url(self, external_url: str) -> str:
        """Return the full external webhook URL for this plugin.

        Plugins that receive webhooks override this to return their
        webhook endpoint URL. Core code calls this without knowing
        the plugin name, keeping core plugin-agnostic.

        Args:
            external_url: The site's external URL (e.g., 'https://pathfinder.example.com').

        Returns:
            Full webhook URL string, or empty string if plugin has no webhook.
        """
        return ""

    @abstractmethod
    def get_config_schema(self) -> dict[str, Any]:
        """
        Return the configuration schema for this plugin.

        The schema defines the fields required to configure a connection
        using this plugin.

        Returns:
            Dictionary describing the configuration fields.
        """
        pass

    @abstractmethod
    def get_wizard_forms(self) -> list[Any]:
        """
        Return the wizard form classes for connection setup.

        Returns:
            List of form classes to be used in the connection wizard.
        """
        pass

    @abstractmethod
    def health_check(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Perform a health check on the connection.

        Args:
            config: The decrypted configuration for the connection.

        Returns:
            Dictionary with 'healthy' (bool) and 'message' (str) keys.
        """
        pass

    @abstractmethod
    def get_urlpatterns(self) -> list[Any]:
        """
        Return URL patterns for this plugin's views.

        Returns:
            List of URL patterns to be included in the application.
        """
        pass


def get_ci_plugin_for_engine(engine_name: str):
    """Find the installed plugin that provides a given CI engine."""
    for plugin in PluginRegistry.all().values():
        if isinstance(plugin, CICapableMixin) and plugin.engine_name == engine_name:
            return plugin
    return None


def get_available_engines() -> list[tuple[str, str]]:
    """Return list of (engine_name, display_name) for all installed CI-capable plugins."""
    engines = []
    for plugin in PluginRegistry.all().values():
        if isinstance(plugin, CICapableMixin):
            engines.append((plugin.engine_name, plugin.engine_display_name))
    return sorted(engines, key=lambda x: x[1])
