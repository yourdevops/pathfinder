import pytest

import core.utils
from core.models import Group, GroupMembership, Project, ProjectMembership, User


@pytest.fixture(autouse=True)
def _bypass_setup_middleware():
    """Set the per-worker setup cache so view tests skip the unlock redirect."""
    core.utils._setup_complete = True
    yield
    core.utils._setup_complete = False


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
