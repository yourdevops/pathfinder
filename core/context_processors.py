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
