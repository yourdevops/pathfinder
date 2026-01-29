"""
GitHub plugin package.

This package provides GitHub integration for Pathfinder, including
repository management, branch creation, and webhook configuration
via GitHub App authentication.
"""
from plugins.base import registry
from .plugin import GitHubPlugin

# Register the plugin with the global registry
github_plugin = GitHubPlugin()
registry.register(github_plugin)
