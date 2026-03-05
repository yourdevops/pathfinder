# SPDX-License-Identifier: Apache-2.0
"""
Docker plugin for container deployment operations.

This plugin provides connectivity to Docker daemons via socket or TCP,
enabling container lifecycle management for deployments.
"""

from typing import Any

import docker
from docker.errors import DockerException, NotFound

from plugins.base import BasePlugin


class DockerPlugin(BasePlugin):
    """
    Docker integration plugin for container deployments.

    Supports connecting to Docker via Unix socket or TCP (with optional TLS).
    Provides container lifecycle operations: run, status, stop, logs.
    """

    name = "docker"
    display_name = "Docker"
    category = "deploy"
    capabilities = ["deploy", "get_status", "stop", "logs"]
    icon = "docker"

    def get_config_schema(self) -> dict[str, Any]:
        """Return configuration schema for Docker connections."""
        return {
            "socket_path": {
                "type": "string",
                "required": True,
                "default": "/var/run/docker.sock",
                "label": "Docker Socket Path",
                "editable": True,
            },
            "tls_enabled": {
                "type": "boolean",
                "required": False,
                "default": False,
                "label": "TLS Enabled",
            },
            "tls_ca_cert": {
                "type": "string",
                "required": False,
                "sensitive": True,
                "label": "TLS CA Certificate",
            },
            "tls_client_cert": {
                "type": "string",
                "required": False,
                "sensitive": True,
                "label": "TLS Client Certificate",
            },
            "tls_client_key": {
                "type": "string",
                "required": False,
                "sensitive": True,
                "label": "TLS Client Key",
            },
        }

    def get_wizard_forms(self) -> list:
        """Return form classes for connection setup."""
        from .forms import DockerConnectionForm

        return [DockerConnectionForm]  # Single form, not a wizard

    def _get_docker_client(self, config: dict[str, Any]) -> docker.DockerClient:
        """
        Get Docker client from config.

        Args:
            config: Connection configuration with socket_path and TLS settings.

        Returns:
            Configured Docker client instance.
        """
        socket_path = config.get("socket_path", "/var/run/docker.sock")

        # Determine base URL format
        base_url = socket_path if socket_path.startswith(("tcp://", "https://", "http://")) else f"unix://{socket_path}"

        # TLS configuration
        tls_config = None
        if config.get("tls_enabled"):
            cert = config.get("tls_client_cert")
            key = config.get("tls_client_key")
            tls_config = docker.tls.TLSConfig(
                ca_cert=config.get("tls_ca_cert"),
                client_cert=(cert, key) if cert and key else None,
                verify=True,
            )

        return docker.DockerClient(base_url=base_url, tls=tls_config)

    def health_check(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Check Docker daemon connectivity.

        Args:
            config: Connection configuration.

        Returns:
            Health status dict with 'status', 'message', and 'details'.
        """
        try:
            client = self._get_docker_client(config)
            client.ping()

            version = client.version()
            info = client.info()

            return {
                "status": "healthy",
                "message": f"Docker {version.get('Version', 'unknown')} - {info.get('ContainersRunning', 0)} containers running",
                "details": {
                    "version": version.get("Version"),
                    "api_version": version.get("ApiVersion"),
                    "os": version.get("Os"),
                    "arch": version.get("Arch"),
                    "containers_running": info.get("ContainersRunning", 0),
                    "containers_total": info.get("Containers", 0),
                    "images": info.get("Images", 0),
                },
            }
        except DockerException as e:
            return {"status": "unhealthy", "message": str(e), "details": {}}
        except Exception as e:
            return {
                "status": "unknown",
                "message": f"Unexpected error: {e}",
                "details": {},
            }

    def run_container(self, config: dict[str, Any], image: str, name: str | None = None, **kwargs) -> dict[str, Any]:
        """
        Run a container.

        Args:
            config: Connection configuration.
            image: Docker image to run.
            name: Optional container name.
            **kwargs: Additional arguments passed to containers.run().

        Returns:
            Container info dict with id, short_id, name, status.
        """
        client = self._get_docker_client(config)
        container = client.containers.run(image, name=name, detach=True, **kwargs)
        return {
            "id": container.id,
            "short_id": container.short_id,
            "name": container.name,
            "status": container.status,
        }

    def get_container_status(self, config: dict[str, Any], container_id: str) -> dict[str, Any]:
        """
        Get container status.

        Args:
            config: Connection configuration.
            container_id: Container ID or name.

        Returns:
            Status dict with id, name, status, health, running.
        """
        client = self._get_docker_client(config)
        try:
            container = client.containers.get(container_id)
            container.reload()
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "none"),
                "running": container.status == "running",
            }
        except NotFound:
            return {
                "id": container_id,
                "status": "not_found",
                "running": False,
                "error": "Container not found",
            }

    def stop_container(self, config: dict[str, Any], container_id: str, timeout: int = 10) -> dict[str, Any]:
        """
        Stop a container.

        Args:
            config: Connection configuration.
            container_id: Container ID or name.
            timeout: Seconds to wait before killing.

        Returns:
            Status dict with 'status' and 'id'.
        """
        client = self._get_docker_client(config)
        container = client.containers.get(container_id)
        container.stop(timeout=timeout)
        return {"status": "stopped", "id": container_id}

    def get_container_logs(self, config: dict[str, Any], container_id: str, tail: int = 100) -> str:
        """
        Get container logs.

        Args:
            config: Connection configuration.
            container_id: Container ID or name.
            tail: Number of lines to return from end.

        Returns:
            Log output as string.
        """
        client = self._get_docker_client(config)
        container = client.containers.get(container_id)
        return container.logs(tail=tail, timestamps=True).decode("utf-8")

    def get_urlpatterns(self):
        """Return URL patterns for this plugin's views."""
        from . import urls

        return urls.urlpatterns
