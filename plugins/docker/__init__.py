"""
Docker plugin for container deployment operations.

This module registers the Docker plugin with the plugin registry,
enabling Docker daemon connectivity and container management.
"""
from plugins.base import registry
from .plugin import DockerPlugin

# Register the plugin
docker_plugin = DockerPlugin()
registry.register(docker_plugin)
