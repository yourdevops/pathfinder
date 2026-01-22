from django.urls import path
from .views import (
    UnlockView, AdminRegistrationView,
    LoginView, LogoutView,
    UserListView, UserCreateView, UserEditView, UserDeleteView,
    GroupListView, GroupDetailView, GroupCreateView, GroupEditView,
    GroupDeleteView, GroupAddMemberView, GroupRemoveMemberView,
    AuditLogView,
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

# Group management URLs
groups_patterns = [
    path('', GroupListView.as_view(), name='list'),
    path('create/', GroupCreateView.as_view(), name='create'),
    path('<uuid:uuid>/', GroupDetailView.as_view(), name='detail'),
    path('<uuid:uuid>/edit/', GroupEditView.as_view(), name='edit'),
    path('<uuid:uuid>/delete/', GroupDeleteView.as_view(), name='delete'),
    path('<uuid:uuid>/add-member/', GroupAddMemberView.as_view(), name='add_member'),
    path('<uuid:uuid>/remove-member/<uuid:user_uuid>/', GroupRemoveMemberView.as_view(), name='remove_member'),
]

# Audit log URLs
audit_patterns = [
    path('', AuditLogView.as_view(), name='list'),
]
