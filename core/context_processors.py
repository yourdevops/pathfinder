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
    """Provide navigation context including active project and settings.

    This context processor provides:
    - in_project_context: True when viewing a project-scoped page
    - current_project: The Project instance when in project context
    - current_project_role: User's role on the current project
    - in_settings_context: Always False (settings use main nav now)
    - active_settings_section: The specific settings section name when on settings URL
    """
    from core.models import Project
    from core.permissions import get_user_project_role

    context = {
        'in_project_context': False,
        'current_project': None,
        'current_project_role': None,
        'in_settings_context': False,  # Keep for backwards compatibility
        'active_settings_section': None,
    }

    # Detect active settings section for nav highlighting
    path = request.path
    if path.startswith('/settings/'):
        if path == '/settings/' or path == '/settings':
            context['active_settings_section'] = 'general'
        elif '/user-management/' in path:
            context['active_settings_section'] = 'user_management'
        elif '/audit-logs/' in path:
            context['active_settings_section'] = 'audit_logs'
        elif '/api-tokens/' in path:
            context['active_settings_section'] = 'api_tokens'
        elif '/notifications/' in path:
            context['active_settings_section'] = 'notifications'

    # Check if we're in a project-scoped URL
    if hasattr(request, 'resolver_match') and request.resolver_match:
        if 'project_uuid' in request.resolver_match.kwargs:
            try:
                project = Project.objects.get(
                    uuid=request.resolver_match.kwargs['project_uuid']
                )
                context['in_project_context'] = True
                context['current_project'] = project
                if request.user.is_authenticated:
                    context['current_project_role'] = get_user_project_role(
                        request.user, project
                    )
            except Project.DoesNotExist:
                pass

    return context
