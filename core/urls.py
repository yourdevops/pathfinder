from django.urls import path

from .views import (
    AddMemberModalView,
    ApiTokensView,
    AuditLogsSettingsView,
    AuditLogView,
    CIConfigSettingsView,
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
    ProjectListView,
    ProjectRemoveApprovedWorkflowView,
    ProjectUpdateCIConfigView,
    ProjectUpdateView,
    RemoveMemberView,
    UnlockView,
    UserCreateView,
    UserDeleteView,
    UserEditView,
    UserListView,
    UserManagementView,
)
from .views.ci_workflows import (
    DeleteVersionView,
    DiscardDraftView,
    ForkWorkflowView,
    PublishVersionView,
    RevokeVersionView,
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
    SuggestVersionView,
    SyncDetailView,
    VersionManifestView,
    WorkflowArchiveView,
    WorkflowComposerView,
    WorkflowCreateView,
    WorkflowDeleteView,
    WorkflowDetailView,
    WorkflowListView,
    WorkflowManifestView,
)
from .views.env_vars import (
    EnvVarBulkSaveView,
)
from .views.services import (
    BuildLogsView,
    ServiceAssignWorkflowView,
    ServiceAutoUpdateToggleView,
    ServiceCreateWizard,
    ServiceDeleteView,
    ServiceDetailView,
    ServiceFetchBuildsView,
    ServiceListView,
    ServicePinVersionView,
    ServiceProvisionVariablesView,
    ServicePushManifestView,
    ServiceRegisterWebhookView,
    ServiceRetryScaffoldView,
    ServiceScaffoldStatusView,
    ServiceUpdateInfoView,
)
from .views.templates import (
    TemplateDeregisterView,
    TemplateDetailView,
    TemplateListView,
    TemplateRegisterView,
    TemplateSyncStatusView,
    TemplateSyncView,
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
    path("step-config/<uuid:step_uuid>/", StepConfigView.as_view(), name="step_config"),
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
    path(
        "repos/<dns:repo_name>/sync/<int:sync_id>/",
        SyncDetailView.as_view(),
        name="sync_detail",
    ),
    path("steps/", StepsCatalogView.as_view(), name="steps_catalog"),
    path("steps/table/", StepsTableView.as_view(), name="steps_table"),
    path("steps/<uuid:step_uuid>/", StepDetailView.as_view(), name="step_detail"),
    # Dynamic workflow paths (must be after all fixed paths to avoid URL conflicts)
    path("<dns:workflow_name>/fork/", ForkWorkflowView.as_view(), name="workflow_fork"),
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
    path(
        "<dns:workflow_name>/archive/",
        WorkflowArchiveView.as_view(),
        name="workflow_archive",
    ),
    path(
        "<dns:workflow_name>/publish/",
        PublishVersionView.as_view(),
        name="workflow_publish",
    ),
    path(
        "<dns:workflow_name>/revoke/<int:version_id>/",
        RevokeVersionView.as_view(),
        name="workflow_revoke",
    ),
    path(
        "<dns:workflow_name>/discard-draft/",
        DiscardDraftView.as_view(),
        name="workflow_discard_draft",
    ),
    path(
        "<dns:workflow_name>/version/<int:version_id>/delete/",
        DeleteVersionView.as_view(),
        name="workflow_delete_version",
    ),
    path(
        "<dns:workflow_name>/version/<int:version_id>/manifest/",
        VersionManifestView.as_view(),
        name="version_manifest",
    ),
    path(
        "<dns:workflow_name>/suggest-version/",
        SuggestVersionView.as_view(),
        name="workflow_suggest_version",
    ),
]

# Services URLs (global service list and helper endpoints)
services_patterns = [
    path("", ServiceListView.as_view(), name="list"),
    path("create/", ServiceCreateWizard.as_view(), name="create"),
]

# Templates URLs
templates_patterns = [
    path("", TemplateListView.as_view(), name="list"),
    path("register/", TemplateRegisterView.as_view(), name="register"),
    path("<dns:template_name>/", TemplateDetailView.as_view(), name="detail"),
    path("<dns:template_name>/deregister/", TemplateDeregisterView.as_view(), name="deregister"),
    path("<dns:template_name>/sync/", TemplateSyncView.as_view(), name="sync"),
    path("<dns:template_name>/sync-status/", TemplateSyncStatusView.as_view(), name="sync_status"),
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
        "<dns:project_name>/members/add/",
        AddMemberModalView.as_view(),
        name="add_member_modal",
    ),
    path(
        "<dns:project_name>/members/<dns:group_name>/remove/",
        RemoveMemberView.as_view(),
        name="remove_member",
    ),
    # Env var bulk save — Project-level
    path(
        "<dns:project_name>/env-vars/bulk-save/",
        EnvVarBulkSaveView.as_view(),
        name="project_env_var_bulk_save",
    ),
    # Env var bulk save — Environment-level
    path(
        "<dns:project_name>/environments/<dns:env_name>/env-vars/bulk-save/",
        EnvVarBulkSaveView.as_view(),
        name="env_env_var_bulk_save",
    ),
    # Env var bulk save — Service-level
    path(
        "<dns:project_name>/services/<dns:service_name>/env-vars/bulk-save/",
        EnvVarBulkSaveView.as_view(),
        name="service_env_var_bulk_save",
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
        "<dns:project_name>/ci-config/",
        ProjectUpdateCIConfigView.as_view(),
        name="update_ci_config",
    ),
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
        "<dns:project_name>/services/<dns:service_name>/update-info/",
        ServiceUpdateInfoView.as_view(),
        name="service_update_info",
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
        "<dns:project_name>/services/<dns:service_name>/retry-scaffold/",
        ServiceRetryScaffoldView.as_view(),
        name="service_retry_scaffold",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/ci/assign-workflow/",
        ServiceAssignWorkflowView.as_view(),
        name="service_assign_workflow",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/ci/pin-version/",
        ServicePinVersionView.as_view(),
        name="service_pin_version",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/ci/push-manifest/",
        ServicePushManifestView.as_view(),
        name="service_push_manifest",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/ci/auto-update-toggle/",
        ServiceAutoUpdateToggleView.as_view(),
        name="service_auto_update_toggle",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/ci/provision-variables/",
        ServiceProvisionVariablesView.as_view(),
        name="service_provision_variables",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/register-webhook/",
        ServiceRegisterWebhookView.as_view(),
        name="service_register_webhook",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/fetch-builds/",
        ServiceFetchBuildsView.as_view(),
        name="service_fetch_builds",
    ),
    path(
        "<dns:project_name>/services/<dns:service_name>/builds/<uuid:build_uuid>/logs/",
        BuildLogsView.as_view(),
        name="service_build_logs",
    ),
]

# Settings URLs
settings_patterns = [
    path("", GeneralSettingsView.as_view(), name="general"),
    path("user-management/", UserManagementView.as_view(), name="user_management"),
    path("audit-logs/", AuditLogsSettingsView.as_view(), name="audit_logs"),
    path("api-tokens/", ApiTokensView.as_view(), name="api_tokens"),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path("ci-config/", CIConfigSettingsView.as_view(), name="settings_ci_config"),
]
