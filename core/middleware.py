from django.shortcuts import redirect
from django.urls import reverse
from .utils import is_setup_complete, generate_unlock_token


class SetupMiddleware:
    """Enforce setup flow: redirect to unlock if setup incomplete,
    redirect away from setup pages if setup is complete.
    """

    SETUP_URL_NAMES = ["setup:unlock", "setup:register"]
    EXEMPT_PREFIXES = ["/static/", "/favicon.ico"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Allow static files and favicon
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        setup_complete = is_setup_complete()

        # Check if current URL is a setup URL
        is_setup_url = False
        if hasattr(request, "resolver_match") and request.resolver_match:
            url_name = request.resolver_match.view_name
            is_setup_url = url_name in self.SETUP_URL_NAMES
        else:
            # Fallback for when resolver hasn't run yet
            is_setup_url = path.startswith("/setup/")

        if not setup_complete:
            # Generate token if it doesn't exist yet
            generate_unlock_token()

            if not is_setup_url:
                # Redirect to unlock page
                return redirect("setup:unlock")
        else:
            if is_setup_url:
                # Setup is done, redirect to login
                return redirect("auth:login")

        return self.get_response(request)
