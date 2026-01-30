"""
Plugin framework base classes.

This module provides the abstract BasePlugin class and the PluginRegistry
singleton that manages plugin registration and discovery.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PluginRegistry:
    """
    Singleton registry for managing plugin instances.

    Plugins register themselves with the registry, typically during
    module import. The registry provides methods to retrieve plugins
    by name or category.
    """

    _plugins: Dict[str, "BasePlugin"] = {}

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
    def all(cls) -> Dict[str, "BasePlugin"]:
        """
        Get all registered plugins.

        Returns:
            Dictionary mapping plugin names to instances.
        """
        return cls._plugins.copy()

    @classmethod
    def by_category(cls, category: str) -> List["BasePlugin"]:
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
    capabilities: List[str] = []
    icon: str = ""

    # Fields matching these patterns will be encrypted
    sensitive_field_patterns: List[str] = [
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

    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return the configuration schema for this plugin.

        The schema defines the fields required to configure a connection
        using this plugin.

        Returns:
            Dictionary describing the configuration fields.
        """
        pass

    @abstractmethod
    def get_wizard_forms(self) -> List[Any]:
        """
        Return the wizard form classes for connection setup.

        Returns:
            List of form classes to be used in the connection wizard.
        """
        pass

    @abstractmethod
    def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a health check on the connection.

        Args:
            config: The decrypted configuration for the connection.

        Returns:
            Dictionary with 'healthy' (bool) and 'message' (str) keys.
        """
        pass

    @abstractmethod
    def get_urlpatterns(self) -> List[Any]:
        """
        Return URL patterns for this plugin's views.

        Returns:
            List of URL patterns to be included in the application.
        """
        pass
