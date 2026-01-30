from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.views import View

from ..forms import LoginForm


def get_default_redirect_url():
    """Get default redirect URL after login, with fallback."""
    try:
        return reverse("users:list")
    except NoReverseMatch:
        return "/users/"


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

            # Redirect to next URL or default
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect(get_default_redirect_url())

        return render(request, self.template_name, {"form": form})


class LogoutView(LoginRequiredMixin, View):
    """Handle user logout."""

    def get(self, request):
        logout(request)
        return redirect("auth:login")

    def post(self, request):
        logout(request)
        return redirect("auth:login")
