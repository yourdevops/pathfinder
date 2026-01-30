"""
URL configuration for pathfinder project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, register_converter
from django.views.generic import RedirectView

from core.converters import DnsLabelConverter

# Register custom URL converters BEFORE importing URL patterns that use them
register_converter(DnsLabelConverter, "dns")

from core.urls import (  # noqa: E402
    setup_patterns,
    auth_patterns,
    dashboard_patterns,
    users_patterns,
    groups_patterns,
    audit_patterns,
    ci_workflows_patterns,
    connections_patterns,
    projects_patterns,
    settings_patterns,
    services_patterns,
    resources_patterns,
)
from plugins import autodiscover  # noqa: E402
from plugins.base import registry  # noqa: E402

autodiscover()

urlpatterns = [
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="root"),
    path("admin/", admin.site.urls),
    path("setup/", include((setup_patterns, "setup"), namespace="setup")),
    path("auth/", include((auth_patterns, "auth"), namespace="auth")),
    path(
        "dashboard/", include((dashboard_patterns, "dashboard"), namespace="dashboard")
    ),
    path("users/", include((users_patterns, "users"), namespace="users")),
    path("groups/", include((groups_patterns, "groups"), namespace="groups")),
    path("audit/", include((audit_patterns, "audit"), namespace="audit")),
    path(
        "ci-workflows/",
        include((ci_workflows_patterns, "ci_workflows"), namespace="ci_workflows"),
    ),
    path(
        "connections/",
        include((connections_patterns, "connections"), namespace="connections"),
    ),
    path("projects/", include((projects_patterns, "projects"), namespace="projects")),
    path("settings/", include((settings_patterns, "settings"), namespace="settings")),
    path("services/", include((services_patterns, "services"), namespace="services")),
    path(
        "resources/", include((resources_patterns, "resources"), namespace="resources")
    ),
]

# Add plugin-specific URLs dynamically
for plugin_name, plugin in registry.all().items():
    patterns = plugin.get_urlpatterns()
    if patterns:
        urlpatterns.append(
            path(
                f"integrations/{plugin_name}/",
                include((patterns, plugin_name), namespace=plugin_name),
            )
        )
