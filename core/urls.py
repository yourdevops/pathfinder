from django.urls import path

from .views import (
    AddMemberModalView,
    ApiTokensView,
    AuditLogsSettingsView,
    AuditLogView,
    ConnectionConfigUpdateView,
    ConnectionCreateDispatchView,
    ConnectionDeleteView,
    ConnectionDetailView,
    ConnectionListView,
    ConnectionTestView,
    DashboardView,
    EnvironmentAttachConnectionView,
    EnvironmentCreateView,
    EnvironmentDeleteView,
    EnvironmentDetachConnectionView,
    EnvironmentDetailView,
    EnvironmentUpdateView,
    EnvVarDeleteView,
    EnvVarModalView,
    EnvVarSaveView,
    GeneralSettingsView,
    GroupAddMemberView,
    GroupCreateView,
    GroupDeleteView,
    GroupDetailView,
    GroupEditView,
    GroupListView,
    GroupRemoveMemberView,
    LoginView,
    LogoutView,
    NotificationsView,
    PluginListView,
    ProjectApproveWorkflowView,
    ProjectArchiveView,
    ProjectAttachConnectionView,
    ProjectCIConfigView,
    ProjectCreateModalView,
    ProjectCreateView,
    ProjectDetachConnectionView,
    ProjectDetailView,
    ProjectEnvVarDeleteView,
    ProjectEnvVarModalView,
    ProjectEnvVarSaveView,
    ProjectListView,
    ProjectRemoveApprovedWorkflowView,
    ProjectUpdateView,
    RemoveMemberView,
    UnlockView,
    UserCreateView,
    UserDeleteView,
    UserEditView,
    UserListView,
    UserManagementView,
    webhooks,
)
from .views.ci_workflows import (
    CompatibleStepsView,
    EngineRuntimesView,
    RuntimeVersionsView,
    StepConfigView,
    StepDetailView,
    StepsCatalogView,
    StepsRepoDeleteView,
    StepsRepoDetailView,
    StepsRepoListView,
    StepsRepoRegisterView,
    StepsRepoScanStatusView,
    StepsRepoScanView,
    StepsTableView,
    WorkflowComposerView,
    WorkflowCreateView,
    WorkflowDeleteView,
    WorkflowDetailView,
    WorkflowListView,
    WorkflowManifestView,
)
from .views.services import (
    ServiceAssignWorkflowView,
    ServiceCreateWizard,
    ServiceDeleteView,
    ServiceDetailView,
    ServiceListView,
    ServicePushManifestView,
    ServiceScaffoldStatusView,
)

# Setup URLs
setup_patterns = [
    path("unlock/", UnlockView.as_view(), name="unlock"),
]

# Auth URLs
auth_patterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]

# Dashboard URLs
dashboard_patterns = [
    path("", DashboardView.as_view(), name="home"),
]

# User management URLs
users_patterns = [
    path("", UserListView.as_view(), name="list"),
    path("create/", UserCreateView.as_view(), name="create"),
    path("<uuid:uuid>/edit/", UserEditView.as_view(), name="edit"),
    path("<uuid:uuid>/delete/", UserDeleteView.as_view(), name="delete"),
]

# Group management URLs
groups_patterns = [
    path("", GroupListView.as_view(), name="list"),
    path("create/", GroupCreateView.as_view(), name="create"),
    path("<dns:group_name>/", GroupDetailView.as_view(), name="detail"),
    path("<dns:group_name>/edit/", GroupEditView.as_view(), name="edit"),
    path("<dns:group_name>/delete/", GroupDeleteView.as_view(), name="delete"),
    path("<dns:group_name>/add-member/", GroupAddMemberView.as_view(), name="add_member"),
    path(
        "<dns:group_name>/remove-member/<uuid:user_uuid>/",
        GroupRemoveMemberView.as_view(),
        name="remove_member",
    ),
]

# Audit log URLs
audit_patterns = [
    path("", AuditLogView.as_view(), name="list"),
]

# CI Workflows URLs
ci_workflows_patterns = [
    path("", WorkflowListView.as_view(), name="workflow_list"),
    path("create/", WorkflowCreateView.as_view(), name="workflow_create"),
    path("composer/", WorkflowComposerView.as_view(), name="workflow_composer"),
    path("compatible-steps/", CompatibleStepsView.as_view(), name="compatible_steps"),
    path("step-config/<uuid:step_uuid>/", StepConfigView.as_view(), name="step_config"),
    path("runtime-versions/", RuntimeVersionsView.as_view(), name="runtime_versions"),
    path("engine-runtimes/", EngineRuntimesView.as_view(), name="engine_runtimes"),
    path("repos/", StepsRepoListView.as_view(), name="repo_list"),
    path("repos/register/", StepsRepoRegisterView.as_view(), name="repo_register"),
    path("repos/<dns:repo_name>/", StepsRepoDetailView.as_view(), name="repo_detail"),
    path("repos/<dns:repo_name>/scan/", StepsRepoScanView.as_view(), name="repo_scan"),
    path(
        "repos/<dns:repo_name>/scan-status/",
        StepsRepoScanStatusView.as_view(),
        name="repo_scan_status",
    ),
    path("repos/<dns:repo_name>/delete/", StepsRepoDeleteView.as_view(), name="repo_delete"),
    path("steps/", StepsCatalogView.as_view(), name="steps_catalog"),
    path("steps/table/", StepsTableView.as_view(), name="steps_table"),
    path("steps/<uuid:step_uuid>/", StepDetailView.as_view(), name="step_detail"),
    # Dynamic workflow paths (must be after all fixed paths to avoid URL conflicts)
    path("<dns:workflow_name>/", WorkflowDetailView.as_view(), name="workflow_detail"),
    path(
        "<dns:workflow_name>/manifest/",
        WorkflowManifestView.as_view(),
        name="workflow_manifest",
    ),
    path(
        "<dns:workflow_name>/edit/",
        WorkflowComposerView.as_view(),
        name="workflow_edit",
    ),
    path(
        "<dns:workflow_name>/delete/",
        WorkflowDeleteView.as_view(),
        name="workflow_delete",
    ),
]

# Services URLs (global service list and helper endpoints)
services_patterns = [
    path("", ServiceListView.as_view(), name="list"),
    path("create/", ServiceCreateWizard.as_view(), name="create"),
]

# Connection URLs (real implementation)
connections_patterns = [
    path("", ConnectionListView.as_view(), name="list"),
    path("plugins/", PluginListView.as_view(), name="plugins"),
    path("<dns:connection_name>/", ConnectionDetailView.as_view(), name="detail"),
    path("<dns:connection_name>/test/", ConnectionTestView.as_view(), name="test"),
    path(
        "<dns:connection_name>/update/",
        ConnectionConfigUpdateView.as_view(),
        name="update",
    ),
    path("<dns:connection_name>/delete/", ConnectionDeleteView.as_view(), name="delete"),
    path(
        "create/<str:plugin_name>/",
        ConnectionCreateDispatchView.as_view(),
        name="create",
    ),
]

# Project management URLs
projects_patterns = [
    path("", ProjectListView.as_view(), name="list"),
    path("create/", ProjectCreateModalView.as_view(), name="create_modal"),
    path("create/submit/", ProjectCreateView.as_view(), name="create"),
    path("<dns:project_name>/", ProjectDetailView.as_view(), name="detail"),
    path("<dns:project_name>/update/", ProjectUpdateView.as_view(), name="update"),
    path("<dns:project_name>/archive/", ProjectArchiveView.as_view(), name="archive"),
    path(
        "<dns:project_name>/environments/create/",
        EnvironmentCreateView.as_view(),
        name="environment_create",
    ),
    path(
        "<dns:project_name>/environments/<dns:env_name>/",
        EnvironmentDetailView.as_view(),
        name="environment_detail",
    ),
    path(
        "<dns:project_name>/environments/<dns:env_name>/update/",
        EnvironmentUpdateView.as_view(),
        name="environment_update",
    ),
    path(
        "<dns:project_name>/environments/<dns:env_name>/delete/",
        EnvironmentDeleteView.as_view(),
        name="environment_delete",
    ),
    path(
        "<dns:project_name>/environments/<dns:env_name>/env-vars/",
        EnvVarModalView.as_view(),
        name="env_var_modal",
    ),
    path(
        "<dns:project_name>/environments/<dns:env_name>/env-vars/save/",
        EnvVarSaveView.as_view(),
        name="env_var_save",
    ),
    path(
        "<dns:project_name>/environments/<dns:env_name>/env-vars/<str:key>/delete/",
        EnvVarDeleteView.as_view(),
        name="env_var_delete",
    ),
    path(
        "<dns:project_name>/members/add/",
        AddMemberModalView.as_view(),
        name="add_member_modal",
    ),
    path(
        "<dns:project_name>/members/<dns:group_name>/remove/",
        RemoveMemberView.as_view(),
        name="remove_member",
    ),
    # Project-level env vars
    path(
        "<dns:project_name>/env-vars/",
        ProjectEnvVarModalView.as_view(),
        name="project_env_var_modal",
    ),
    path(
        "<dns:project_name>/env-vars/<str:key>/edit/",
        ProjectEnvVarModalView.as_view(),
        name="project_env_var_edit",
    ),
    path(
        "<dns:project_name>/env-vars/save/",
        ProjectEnvVarSaveView.as_view(),
        name="project_env_var_save",
    ),
    path(
        "<dns:project_name>/env-vars/<str:key>/delete/",
        ProjectEnvVarDeleteView.as_view(),
        name="project_env_var_delete",
    ),
    # Project connections
    path(
        "<dns:project_name>/connections/attach/",
        ProjectAttachConnectionView.as_view(),
        name="project_attach_connection",
    ),
    path(
        "<dns:project_name>/connections/<int:connection_id>/detach/",
        ProjectDetachConnectionView.as_view(),
        name="project_detach_connection",
    ),
    # Environment connections
    path(
        "<dns:project_name>/environments/<dns:env_name>/connections/attach/",
        EnvironmentAttachConnectionView.as_view(),
        name="env_attach_connection",
    ),
    path(
        "<dns:project_name>/environments/<dns:env_name>/connections/<int:connection_id>/detach/",
        EnvironmentDetachConnectionView.as_view(),
        name="env_detach_connection",
    ),
    # CI Configuration
    path(
        "<dns:project_name>/settings/ci-config/",
        ProjectCIConfigView.as_view(),
        name="project_ci_config",
    ),
    path(
        "<dns:project_name>/settings/approve-workflow/",
        ProjectApproveWorkflowView.as_view(),
        name="project_approve_workflow",
    ),
    path(
        "<dns:project_name>/settings/remove-workflow/<int:workflow_id>/",
        ProjectRemoveApprovedWorkflowView.as_view(),
        name="project_remove_workflow",
    ),
    # Services (project-scoped)
    path(
        "<dns:project_name>/services/create/",
        ServiceCreateWizard.as_view(),
        name="service_create",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/",
        ServiceDetailView.as_view(),
        name="service_detail",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/delete/",
        ServiceDeleteView.as_view(),
        name="service_delete",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/scaffold-status/",
        ServiceScaffoldStatusView.as_view(),
        name="service_scaffold_status",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/ci/assign-workflow/",
        ServiceAssignWorkflowView.as_view(),
        name="service_assign_workflow",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/ci/push-manifest/",
        ServicePushManifestView.as_view(),
        name="service_push_manifest",
    ),
]

# Settings URLs
settings_patterns = [
    path("", GeneralSettingsView.as_view(), name="general"),
    path("user-management/", UserManagementView.as_view(), name="user_management"),
    path("audit-logs/", AuditLogsSettingsView.as_view(), name="audit_logs"),
    path("api-tokens/", ApiTokensView.as_view(), name="api_tokens"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
]

# Webhooks URLs
webhooks_patterns = [
    path("build/", webhooks.build_webhook, name="build_webhook"),
]
