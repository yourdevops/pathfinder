"""Tests for service view permission checks.

Verifies that viewers cannot access contributor-level service operations.
Regression test for the can_access_project bool-vs-string comparison bug.
"""

import pytest
from django.test import Client
from django.urls import reverse

from core.models import Group, GroupMembership, User


@pytest.mark.django_db
class TestServiceCreatePermission:
    """Viewers must not access the service creation wizard."""

    def test_viewer_is_denied(self, project, make_user_with_role):
        user = make_user_with_role("viewer", project, "viewer")
        client = Client()
        client.force_login(user)

        url = reverse("projects:service_create", kwargs={"project_name": project.name})
        resp = client.get(url)

        assert resp.status_code == 302
        expected = reverse("projects:detail", kwargs={"project_name": project.name})
        assert resp.url == expected

    def test_contributor_is_allowed(self, project, make_user_with_role):
        user = make_user_with_role("contributor", project, "contributor")
        client = Client()
        client.force_login(user)

        url = reverse("projects:service_create", kwargs={"project_name": project.name})
        resp = client.get(url)

        assert resp.status_code == 200

    def test_admin_is_allowed(self, project):
        user = User.objects.create_user(username="admin-user", password="testpass123")
        group = Group.objects.create(name="admins-group", system_roles=["admin"])
        GroupMembership.objects.create(group=group, user=user)
        client = Client()
        client.force_login(user)

        url = reverse("projects:service_create", kwargs={"project_name": project.name})
        resp = client.get(url)

        assert resp.status_code == 200
