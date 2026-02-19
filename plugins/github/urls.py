"""GitHub plugin URL configuration."""

from django.urls import path

from . import views, webhooks

app_name = "github"

urlpatterns = [
    path("create/", views.GitHubConnectionCreateView.as_view(), name="create"),
    path(
        "manifest/callback/",
        views.GitHubManifestCallbackView.as_view(),
        name="manifest_callback",
    ),
    path(
        "installation/callback/",
        views.GitHubInstallationCallbackView.as_view(),
        name="installation_callback",
    ),
    path("webhook/", webhooks.github_webhook, name="webhook"),
]
