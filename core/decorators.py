from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import GroupMembership


def has_system_role(user, role):
    """Check if user has a specific SystemRole through any group."""
    if not user.is_authenticated:
        return False
    return GroupMembership.objects.filter(
        user=user,
        group__status='active',
        group__system_roles__contains=[role]
    ).exists()


def admin_required(view_func):
    """Decorator requiring user to have admin SystemRole."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not has_system_role(request.user, 'admin'):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('auth:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def operator_required(view_func):
    """Decorator requiring user to have operator or admin SystemRole."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (has_system_role(request.user, 'admin') or has_system_role(request.user, 'operator')):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('auth:login')
        return view_func(request, *args, **kwargs)
    return wrapper


class AdminRequiredMixin:
    """Mixin for class-based views requiring admin role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth:login')
        if not has_system_role(request.user, 'admin'):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('auth:login')
        return super().dispatch(request, *args, **kwargs)
