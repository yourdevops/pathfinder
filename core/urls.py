from django.urls import path
from .views import UnlockView, AdminRegistrationView, LoginView, LogoutView

# Setup URLs
setup_patterns = [
    path('unlock/', UnlockView.as_view(), name='unlock'),
    path('register/', AdminRegistrationView.as_view(), name='register'),
]

# Auth URLs
auth_patterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

# These will be included with namespaces in devssp/urls.py
