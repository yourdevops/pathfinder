"""Project-level permission helpers and view mixins."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from core.models import GroupMembership, Project, ProjectMembership, User

ROLE_HIERARCHY = ["viewer", "contributor", "owner"]


def has_system_role(user: User, role: str | list[str]) -> bool:
    """Check if user has a specific SystemRole through any group.

    Args:
        user: The user to check
        role: Either a single role string or a list of roles to check

    Returns:
        True if user has any of the specified roles
    """
    if not user.is_authenticated:
        return False
    memberships = GroupMembership.objects.filter(user=user, group__status="active").select_related("group")

    # Support both single role string and list of roles
    if isinstance(role, (list, tuple)):
        return any(any(r in m.group.system_roles for r in role) for m in memberships)
    return any(role in m.group.system_roles for m in memberships)


def get_user_project_role(user: User, project: Project) -> str | None:
    """
    Return highest project role for user, or None if no access.

    Role priority: owner > contributor > viewer
    Admin and Operator system roles get owner-level access.
    """
    ROLE_PRIORITY = {"owner": 3, "contributor": 2, "viewer": 1}

    # System admins and operators get owner access
    if has_system_role(user, ["admin", "operator"]):
        return "owner"

    # Get all memberships through user's groups
    user_group_ids = GroupMembership.objects.filter(user=user, group__status="active").values_list(
        "group_id", flat=True
    )

    memberships = ProjectMembership.objects.filter(project=project, group_id__in=user_group_ids)

    if not memberships.exists():
        return None

    # Return highest role
    roles = [m.project_role for m in memberships]
    return max(roles, key=lambda r: ROLE_PRIORITY.get(r, 0))


def can_access_project(user: User, project: Project, required_role: str = "viewer") -> bool:
    """Check if user has at least the required role."""
    user_role = get_user_project_role(user, project)

    if not user_role:
        return False

    return ROLE_HIERARCHY.index(user_role) >= ROLE_HIERARCHY.index(required_role)


class ProjectPermissionMixin:
    """Base mixin for project-scoped views."""

    required_role = "viewer"  # Override in subclass

    def dispatch(self, request, *args, **kwargs):
        # Changed: lookup by name instead of uuid
        self.project = get_object_or_404(Project, name=kwargs.get("project_name"))
        self.user_project_role = get_user_project_role(request.user, self.project)

        if not self.user_project_role:
            messages.error(request, "You do not have access to this project.")
            return redirect("projects:list")

        if ROLE_HIERARCHY.index(self.user_project_role) < ROLE_HIERARCHY.index(self.required_role):
            messages.error(request, "You do not have permission for this action.")
            # Changed: use name instead of uuid
            return redirect("projects:detail", project_name=self.project.name)

        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # type: ignore[misc]
        context["project"] = self.project
        context["user_project_role"] = self.user_project_role
        return context


class ProjectViewerMixin(ProjectPermissionMixin):
    """Mixin for views requiring viewer access (read-only)."""

    required_role = "viewer"


class ProjectContributorMixin(ProjectPermissionMixin):
    """Mixin for views requiring contributor access (modify services/environments)."""

    required_role = "contributor"


class ProjectOwnerMixin(ProjectPermissionMixin):
    """Mixin for views requiring owner access (settings, membership management)."""

    required_role = "owner"


class OperatorRequiredMixin:
    """Mixin that requires user to have 'operator' or 'admin' system role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # type: ignore[attr-defined]
        if not has_system_role(request.user, ["admin", "operator"]):
            messages.error(request, "You need operator permissions to access this page.")
            return redirect("projects:list")
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]


class IntegrationsReadMixin:
    """Mixin for read-only integrations access (admin, operator, or auditor)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # type: ignore[attr-defined]
        if not has_system_role(request.user, ["admin", "operator", "auditor"]):
            messages.error(
                request,
                "You need operator or auditor permissions to view connection details.",
            )
            return redirect("connections:list")
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
