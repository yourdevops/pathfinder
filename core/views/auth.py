from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from ..forms import LoginForm


def get_default_redirect_url():
    """Get default redirect URL after login, with fallback."""
    try:
        return reverse("dashboard:home")
    except NoReverseMatch:
        return "/dashboard/"


class LoginView(View):
    """Handle user login."""

    template_name = "core/auth/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(get_default_redirect_url())
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(request, request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Handle "remember me"
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(604800)  # 7 days
            else:
                request.session.set_expiry(86400)  # 1 day

            # Redirect to next URL or default (validate to prevent open redirect)
            next_url = request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect(get_default_redirect_url())

        return render(request, self.template_name, {"form": form})


class LogoutView(LoginRequiredMixin, View):
    """Handle user logout (POST only to prevent CSRF logout via GET)."""

    http_method_names = ["post"]

    def post(self, request):
        logout(request)
        return redirect("auth:login")
