from core.models import GroupMembership


def user_roles(request):
    """Add user's system roles to template context."""
    if not request.user.is_authenticated:
        return {'user_roles': [], 'is_admin': False, 'is_operator': False, 'is_auditor': False}

    roles = set()
    memberships = GroupMembership.objects.filter(
        user=request.user,
        group__status='active'
    ).select_related('group')

    for membership in memberships:
        roles.update(membership.group.system_roles)

    return {
        'user_roles': list(roles),
        'is_admin': 'admin' in roles,
        'is_operator': 'operator' in roles,
        'is_auditor': 'auditor' in roles,
    }


def navigation_context(request):
    """Provide navigation context including active project.

    This context processor provides:
    - in_project_context: True when viewing a project-scoped page
    - current_project: The Project instance when in project context

    Project context detection will be fully implemented in Plan 03.
    """
    context = {
        'in_project_context': False,
        'current_project': None,
    }
    # Project context detection will be added in Plan 03
    # when project detail views are created with project_uuid in URL
    return context
