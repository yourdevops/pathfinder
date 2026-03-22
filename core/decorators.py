from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .permissions import has_system_role


def admin_required(view_func):
    """Decorator requiring user to have admin SystemRole."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not has_system_role(request.user, "admin"):
            messages.error(request, "You do not have permission to access this page.")
            return redirect("dashboard:home")
        return view_func(request, *args, **kwargs)

    return wrapper


def operator_required(view_func):
    """Decorator requiring user to have operator or admin SystemRole."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not has_system_role(request.user, ["admin", "operator"]):
            messages.error(request, "You do not have permission to access this page.")
            return redirect("dashboard:home")
        return view_func(request, *args, **kwargs)

    return wrapper


class AdminRequiredMixin:
    """Mixin for class-based views requiring admin role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("auth:login")
        if not has_system_role(request.user, "admin"):
            messages.error(request, "You do not have permission to access this page.")
            return redirect("dashboard:home")
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
