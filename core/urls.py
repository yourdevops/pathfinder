from django.urls import path
from .views import (
    UnlockView,
    LoginView, LogoutView,
    DashboardView,
    UserListView, UserCreateView, UserEditView, UserDeleteView,
    GroupListView, GroupDetailView, GroupCreateView, GroupEditView,
    GroupDeleteView, GroupAddMemberView, GroupRemoveMemberView,
    AuditLogView,
    BlueprintsListView, BlueprintDetailView, BlueprintRegisterView,
    BlueprintPreviewView, BlueprintSyncView, BlueprintSyncStatusView,
    ResourcesPlaceholderView,
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
from .views.services import (
    ServiceListView, ServiceCreateWizard, ServiceDetailView, ServiceDeleteView,
    ServiceScaffoldStatusView, BlueprintVersionsView,
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

# Dashboard URLs
dashboard_patterns = [
    path('', DashboardView.as_view(), name='home'),
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
    path('<dns:group_name>/', GroupDetailView.as_view(), name='detail'),
    path('<dns:group_name>/edit/', GroupEditView.as_view(), name='edit'),
    path('<dns:group_name>/delete/', GroupDeleteView.as_view(), name='delete'),
    path('<dns:group_name>/add-member/', GroupAddMemberView.as_view(), name='add_member'),
    path('<dns:group_name>/remove-member/<uuid:user_uuid>/', GroupRemoveMemberView.as_view(), name='remove_member'),
]

# Audit log URLs
audit_patterns = [
    path('', AuditLogView.as_view(), name='list'),
]

# Blueprint URLs
blueprints_patterns = [
    path('', BlueprintsListView.as_view(), name='list'),
    path('register/', BlueprintRegisterView.as_view(), name='register'),
    path('preview/', BlueprintPreviewView.as_view(), name='preview'),
    path('<dns:blueprint_name>/', BlueprintDetailView.as_view(), name='detail'),
    path('<dns:blueprint_name>/sync/', BlueprintSyncView.as_view(), name='sync'),
    path('<dns:blueprint_name>/sync-status/', BlueprintSyncStatusView.as_view(), name='sync_status'),
]

# Services URLs (global service list and helper endpoints)
services_patterns = [
    path('', ServiceListView.as_view(), name='list'),
    path('blueprint-versions/<int:blueprint_id>/', BlueprintVersionsView.as_view(), name='blueprint_versions'),
]

# Resources placeholder URLs (to be replaced in future version)
resources_patterns = [
    path('', ResourcesPlaceholderView.as_view(), name='list'),
]

# Connection URLs (real implementation)
connections_patterns = [
    path('', ConnectionListView.as_view(), name='list'),
    path('plugins/', PluginListView.as_view(), name='plugins'),
    path('<dns:connection_name>/', ConnectionDetailView.as_view(), name='detail'),
    path('<dns:connection_name>/test/', ConnectionTestView.as_view(), name='test'),
    path('<dns:connection_name>/update/', ConnectionConfigUpdateView.as_view(), name='update'),
    path('<dns:connection_name>/delete/', ConnectionDeleteView.as_view(), name='delete'),
    path('create/<str:plugin_name>/', ConnectionCreateDispatchView.as_view(), name='create'),
]

# Project management URLs
projects_patterns = [
    path('', ProjectListView.as_view(), name='list'),
    path('create/', ProjectCreateModalView.as_view(), name='create_modal'),
    path('create/submit/', ProjectCreateView.as_view(), name='create'),
    path('<dns:project_name>/', ProjectDetailView.as_view(), name='detail'),
    path('<dns:project_name>/update/', ProjectUpdateView.as_view(), name='update'),
    path('<dns:project_name>/archive/', ProjectArchiveView.as_view(), name='archive'),
    path('<dns:project_name>/environments/create/', EnvironmentCreateView.as_view(), name='environment_create'),
    path('<dns:project_name>/environments/<dns:env_name>/', EnvironmentDetailView.as_view(), name='environment_detail'),
    path('<dns:project_name>/environments/<dns:env_name>/update/', EnvironmentUpdateView.as_view(), name='environment_update'),
    path('<dns:project_name>/environments/<dns:env_name>/delete/', EnvironmentDeleteView.as_view(), name='environment_delete'),
    path('<dns:project_name>/environments/<dns:env_name>/env-vars/', EnvVarModalView.as_view(), name='env_var_modal'),
    path('<dns:project_name>/environments/<dns:env_name>/env-vars/save/', EnvVarSaveView.as_view(), name='env_var_save'),
    path('<dns:project_name>/environments/<dns:env_name>/env-vars/<str:key>/delete/', EnvVarDeleteView.as_view(), name='env_var_delete'),
    path('<dns:project_name>/members/add/', AddMemberModalView.as_view(), name='add_member_modal'),
    path('<dns:project_name>/members/<dns:group_name>/remove/', RemoveMemberView.as_view(), name='remove_member'),
    # Project-level env vars
    path('<dns:project_name>/env-vars/', ProjectEnvVarModalView.as_view(), name='project_env_var_modal'),
    path('<dns:project_name>/env-vars/<str:key>/edit/', ProjectEnvVarModalView.as_view(), name='project_env_var_edit'),
    path('<dns:project_name>/env-vars/save/', ProjectEnvVarSaveView.as_view(), name='project_env_var_save'),
    path('<dns:project_name>/env-vars/<str:key>/delete/', ProjectEnvVarDeleteView.as_view(), name='project_env_var_delete'),
    # Project connections
    path('<dns:project_name>/connections/attach/', ProjectAttachConnectionView.as_view(), name='project_attach_connection'),
    path('<dns:project_name>/connections/<int:connection_id>/detach/', ProjectDetachConnectionView.as_view(), name='project_detach_connection'),
    # Environment connections
    path('<dns:project_name>/environments/<dns:env_name>/connections/attach/', EnvironmentAttachConnectionView.as_view(), name='env_attach_connection'),
    path('<dns:project_name>/environments/<dns:env_name>/connections/<int:connection_id>/detach/', EnvironmentDetachConnectionView.as_view(), name='env_detach_connection'),
    # Services (project-scoped)
    path('<dns:project_name>/services/create/', ServiceCreateWizard.as_view(), name='service_create'),
    path('<dns:project_name>/services/<dns:service_name>/', ServiceDetailView.as_view(), name='service_detail'),
    path('<dns:project_name>/services/<dns:service_name>/delete/', ServiceDeleteView.as_view(), name='service_delete'),
    path('<dns:project_name>/services/<dns:service_name>/scaffold-status/', ServiceScaffoldStatusView.as_view(), name='service_scaffold_status'),
]

# Settings URLs
settings_patterns = [
    path('', GeneralSettingsView.as_view(), name='general'),
    path('user-management/', UserManagementView.as_view(), name='user_management'),
    path('audit-logs/', AuditLogsSettingsView.as_view(), name='audit_logs'),
    path('api-tokens/', ApiTokensView.as_view(), name='api_tokens'),
    path('notifications/', NotificationsView.as_view(), name='notifications'),
]
