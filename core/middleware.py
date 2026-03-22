from django.shortcuts import redirect

from .utils import generate_unlock_token, is_setup_complete


class SetupMiddleware:
    """Enforce setup flow: redirect to unlock if setup incomplete,
    redirect away from setup pages if setup is complete.
    """

    EXEMPT_PREFIXES = ["/static/", "/favicon.ico"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Allow static files and favicon
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        is_setup_url = path.startswith("/setup/")

        if is_setup_complete():
            if is_setup_url:
                return redirect("auth:login")
        else:
            # Generate token if it doesn't exist yet
            generate_unlock_token()
            if not is_setup_url:
                return redirect("setup:unlock")

        return self.get_response(request)
