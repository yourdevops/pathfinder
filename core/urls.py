from django.urls import path
from .views import (
    UnlockView,
    LoginView, LogoutView,
    UserListView, UserCreateView, UserEditView, UserDeleteView,
    GroupListView, GroupDetailView, GroupCreateView, GroupEditView,
    GroupDeleteView, GroupAddMemberView, GroupRemoveMemberView,
    AuditLogView,
    BlueprintsListView, ConnectionsListView,
    ProjectListView, ProjectCreateModalView, ProjectCreateView,
)

# Setup URLs
setup_patterns = [
    path('unlock/', UnlockView.as_view(), name='unlock'),
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

# Placeholder URLs (to be replaced in Phase 3-4)
blueprints_patterns = [
    path('', BlueprintsListView.as_view(), name='list'),
]

connections_patterns = [
    path('', ConnectionsListView.as_view(), name='list'),
]

# Project management URLs
projects_patterns = [
    path('', ProjectListView.as_view(), name='list'),
    path('create/', ProjectCreateModalView.as_view(), name='create_modal'),
    path('create/submit/', ProjectCreateView.as_view(), name='create'),
]
