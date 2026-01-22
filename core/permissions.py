"""Project-level permission helpers and view mixins."""
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from core.models import Project, ProjectMembership, GroupMembership


def has_system_role(user, role):
    """Check if user has a system role via group membership."""
    if not user.is_authenticated:
        return False
    return GroupMembership.objects.filter(
        user=user,
        group__status='active',
        group__system_roles__contains=[role]
    ).exists()


def get_user_project_role(user, project):
    """
    Return highest project role for user, or None if no access.

    Role priority: owner > contributor > viewer
    Admin and Operator system roles get owner-level access.
    """
    ROLE_PRIORITY = {'owner': 3, 'contributor': 2, 'viewer': 1}

    # System admins and operators get owner access
    if has_system_role(user, 'admin') or has_system_role(user, 'operator'):
        return 'owner'

    # Get all memberships through user's groups
    user_group_ids = GroupMembership.objects.filter(
        user=user,
        group__status='active'
    ).values_list('group_id', flat=True)

    memberships = ProjectMembership.objects.filter(
        project=project,
        group_id__in=user_group_ids
    )

    if not memberships.exists():
        return None

    # Return highest role
    roles = [m.project_role for m in memberships]
    return max(roles, key=lambda r: ROLE_PRIORITY.get(r, 0))


def can_access_project(user, project, required_role='viewer'):
    """Check if user has at least the required role."""
    ROLE_HIERARCHY = ['viewer', 'contributor', 'owner']
    user_role = get_user_project_role(user, project)

    if not user_role:
        return False

    return ROLE_HIERARCHY.index(user_role) >= ROLE_HIERARCHY.index(required_role)


class ProjectPermissionMixin:
    """Base mixin for project-scoped views."""
    required_role = 'viewer'  # Override in subclass

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, uuid=kwargs.get('project_uuid'))
        self.user_project_role = get_user_project_role(request.user, self.project)

        if not self.user_project_role:
            messages.error(request, 'You do not have access to this project.')
            return redirect('projects:list')

        ROLE_HIERARCHY = ['viewer', 'contributor', 'owner']
        if ROLE_HIERARCHY.index(self.user_project_role) < ROLE_HIERARCHY.index(self.required_role):
            messages.error(request, 'You do not have permission for this action.')
            return redirect('projects:detail', project_uuid=self.project.uuid)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['user_project_role'] = self.user_project_role
        return context


class ProjectViewerMixin(ProjectPermissionMixin):
    """Mixin for views requiring viewer access (read-only)."""
    required_role = 'viewer'


class ProjectContributorMixin(ProjectPermissionMixin):
    """Mixin for views requiring contributor access (modify services/environments)."""
    required_role = 'contributor'


class ProjectOwnerMixin(ProjectPermissionMixin):
    """Mixin for views requiring owner access (settings, membership management)."""
    required_role = 'owner'
