from django.urls import path
from .views import (
    UnlockView,
    LoginView, LogoutView,
    UserListView, UserCreateView, UserEditView, UserDeleteView,
    GroupListView, GroupDetailView, GroupCreateView, GroupEditView,
    GroupDeleteView, GroupAddMemberView, GroupRemoveMemberView,
    AuditLogView,
    BlueprintsListView,
    ConnectionListView, ConnectionDetailView, ConnectionTestView,
    ConnectionDeleteView, ConnectionConfigUpdateView, ConnectionCreateDispatchView, PluginListView,
    ProjectListView, ProjectCreateModalView, ProjectCreateView,
    ProjectDetailView, ProjectUpdateView, ProjectArchiveView,
    EnvironmentCreateView, EnvironmentDetailView, EnvironmentUpdateView, EnvironmentDeleteView,
    AddMemberModalView, RemoveMemberView,
    ProjectEnvVarModalView, ProjectEnvVarSaveView, ProjectEnvVarDeleteView,
    EnvVarModalView, EnvVarSaveView, EnvVarDeleteView,
    ProjectAttachConnectionView, ProjectDetachConnectionView,
    EnvironmentAttachConnectionView, EnvironmentDetachConnectionView,
    GeneralSettingsView, UserManagementView, AuditLogsSettingsView,
    ApiTokensView, NotificationsView,
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

# Placeholder URLs (blueprints to be replaced in Phase 4)
blueprints_patterns = [
    path('', BlueprintsListView.as_view(), name='list'),
]

# Connection URLs (real implementation)
connections_patterns = [
    path('', ConnectionListView.as_view(), name='list'),
    path('plugins/', PluginListView.as_view(), name='plugins'),
    path('<uuid:uuid>/', ConnectionDetailView.as_view(), name='detail'),
    path('<uuid:uuid>/test/', ConnectionTestView.as_view(), name='test'),
    path('<uuid:uuid>/update/', ConnectionConfigUpdateView.as_view(), name='update'),
    path('<uuid:uuid>/delete/', ConnectionDeleteView.as_view(), name='delete'),
    path('create/<str:plugin_name>/', ConnectionCreateDispatchView.as_view(), name='create'),
]

# Project management URLs
projects_patterns = [
    path('', ProjectListView.as_view(), name='list'),
    path('create/', ProjectCreateModalView.as_view(), name='create_modal'),
    path('create/submit/', ProjectCreateView.as_view(), name='create'),
    path('<uuid:project_uuid>/', ProjectDetailView.as_view(), name='detail'),
    path('<uuid:project_uuid>/update/', ProjectUpdateView.as_view(), name='update'),
    path('<uuid:project_uuid>/archive/', ProjectArchiveView.as_view(), name='archive'),
    path('<uuid:project_uuid>/environments/create/', EnvironmentCreateView.as_view(), name='environment_create'),
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/', EnvironmentDetailView.as_view(), name='environment_detail'),
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/update/', EnvironmentUpdateView.as_view(), name='environment_update'),
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/delete/', EnvironmentDeleteView.as_view(), name='environment_delete'),
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/env-vars/', EnvVarModalView.as_view(), name='env_var_modal'),
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/env-vars/save/', EnvVarSaveView.as_view(), name='env_var_save'),
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/env-vars/<str:key>/delete/', EnvVarDeleteView.as_view(), name='env_var_delete'),
    path('<uuid:project_uuid>/members/add/', AddMemberModalView.as_view(), name='add_member_modal'),
    path('<uuid:project_uuid>/members/<uuid:group_uuid>/remove/', RemoveMemberView.as_view(), name='remove_member'),
    # Project-level env vars
    path('<uuid:project_uuid>/env-vars/', ProjectEnvVarModalView.as_view(), name='project_env_var_modal'),
    path('<uuid:project_uuid>/env-vars/save/', ProjectEnvVarSaveView.as_view(), name='project_env_var_save'),
    path('<uuid:project_uuid>/env-vars/<str:key>/delete/', ProjectEnvVarDeleteView.as_view(), name='project_env_var_delete'),
    # Project connections
    path('<uuid:project_uuid>/connections/attach/', ProjectAttachConnectionView.as_view(), name='project_attach_connection'),
    path('<uuid:project_uuid>/connections/<int:connection_id>/detach/', ProjectDetachConnectionView.as_view(), name='project_detach_connection'),
    # Environment connections
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/connections/attach/', EnvironmentAttachConnectionView.as_view(), name='env_attach_connection'),
    path('<uuid:project_uuid>/environments/<uuid:env_uuid>/connections/<int:connection_id>/detach/', EnvironmentDetachConnectionView.as_view(), name='env_detach_connection'),
]

# Settings URLs
settings_patterns = [
    path('', GeneralSettingsView.as_view(), name='general'),
    path('user-management/', UserManagementView.as_view(), name='user_management'),
    path('audit-logs/', AuditLogsSettingsView.as_view(), name='audit_logs'),
    path('api-tokens/', ApiTokensView.as_view(), name='api_tokens'),
    path('notifications/', NotificationsView.as_view(), name='notifications'),
]
