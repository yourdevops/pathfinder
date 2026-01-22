from django.urls import path
from .views import (
    UnlockView, AdminRegistrationView,
    LoginView, LogoutView,
    UserListView, UserCreateView, UserEditView, UserDeleteView,
)

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

# User management URLs
users_patterns = [
    path('', UserListView.as_view(), name='list'),
    path('create/', UserCreateView.as_view(), name='create'),
    path('<uuid:uuid>/edit/', UserEditView.as_view(), name='edit'),
    path('<uuid:uuid>/delete/', UserDeleteView.as_view(), name='delete'),
]

# These will be included with namespaces in devssp/urls.py
