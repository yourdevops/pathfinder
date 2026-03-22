from unittest.mock import patch

import pytest

from core.models import Group, GroupMembership, Project, ProjectMembership, User


@pytest.fixture(autouse=True)
def _bypass_setup_middleware():
    """Skip the SetupMiddleware unlock redirect so view tests hit actual views."""
    with patch("core.middleware.is_setup_complete", return_value=True):
        yield


@pytest.fixture()
def project(db):
    return Project.objects.create(name="test-project", status="active")


@pytest.fixture()
def make_user_with_role(db):
    """Factory fixture: call make_user_with_role(username, project, role) in tests."""

    def _factory(username, project, role):
        user = User.objects.create_user(username=username, password="testpass123")
        group = Group.objects.create(name=f"{username}-group")
        GroupMembership.objects.create(group=group, user=user)
        ProjectMembership.objects.create(project=project, group=group, project_role=role)
        return user

    return _factory
