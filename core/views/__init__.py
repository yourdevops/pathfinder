from .setup import UnlockView
from .auth import LoginView, LogoutView
from .dashboard import DashboardView
from .users import UserListView, UserCreateView, UserEditView, UserDeleteView
from .groups import (
    GroupListView, GroupDetailView, GroupCreateView, GroupEditView,
    GroupDeleteView, GroupAddMemberView, GroupRemoveMemberView,
)
from .audit import AuditLogView
from .placeholders import ServicesPlaceholderView, ResourcesPlaceholderView
from .blueprints import (
    BlueprintListView, BlueprintsListView,
    BlueprintDetailView, BlueprintRegisterView,
    BlueprintPreviewView, BlueprintSyncView, BlueprintSyncStatusView,
)
from .connections import (
    ConnectionListView,
    ConnectionDetailView,
    ConnectionTestView,
    ConnectionDeleteView,
    ConnectionConfigUpdateView,
    ConnectionCreateDispatchView,
    PluginListView,
)
from .projects import (
    ProjectListView, ProjectCreateModalView, ProjectCreateView,
    ProjectDetailView, ProjectUpdateView, ProjectArchiveView,
    EnvironmentCreateView, EnvironmentDetailView, EnvironmentUpdateView, EnvironmentDeleteView,
    AddMemberModalView, RemoveMemberView,
    ProjectEnvVarModalView, ProjectEnvVarSaveView, ProjectEnvVarDeleteView,
    EnvVarModalView, EnvVarSaveView, EnvVarDeleteView,
    ProjectAttachConnectionView, ProjectDetachConnectionView,
    EnvironmentAttachConnectionView, EnvironmentDetachConnectionView,
)
from .settings import (
    GeneralSettingsView, UserManagementView, AuditLogsSettingsView,
    ApiTokensView, NotificationsView,
)

__all__ = [
    'UnlockView',
    'LoginView', 'LogoutView',
    'DashboardView',
    'UserListView', 'UserCreateView', 'UserEditView', 'UserDeleteView',
    'GroupListView', 'GroupDetailView', 'GroupCreateView', 'GroupEditView',
    'GroupDeleteView', 'GroupAddMemberView', 'GroupRemoveMemberView',
    'AuditLogView',
    'BlueprintListView', 'BlueprintsListView', 'BlueprintDetailView',
    'BlueprintRegisterView', 'BlueprintPreviewView', 'BlueprintSyncView', 'BlueprintSyncStatusView',
    'ServicesPlaceholderView', 'ResourcesPlaceholderView',
    'ConnectionListView', 'ConnectionDetailView', 'ConnectionTestView',
    'ConnectionDeleteView', 'ConnectionConfigUpdateView', 'ConnectionCreateDispatchView', 'PluginListView',
    'ProjectListView', 'ProjectCreateModalView', 'ProjectCreateView',
    'ProjectDetailView', 'ProjectUpdateView', 'ProjectArchiveView',
    'EnvironmentCreateView', 'EnvironmentDetailView', 'EnvironmentUpdateView', 'EnvironmentDeleteView',
    'AddMemberModalView', 'RemoveMemberView',
    'ProjectEnvVarModalView', 'ProjectEnvVarSaveView', 'ProjectEnvVarDeleteView',
    'EnvVarModalView', 'EnvVarSaveView', 'EnvVarDeleteView',
    'ProjectAttachConnectionView', 'ProjectDetachConnectionView',
    'EnvironmentAttachConnectionView', 'EnvironmentDetachConnectionView',
    'GeneralSettingsView', 'UserManagementView', 'AuditLogsSettingsView',
    'ApiTokensView', 'NotificationsView',
]
