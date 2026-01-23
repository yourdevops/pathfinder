from .setup import UnlockView
from .auth import LoginView, LogoutView
from .users import UserListView, UserCreateView, UserEditView, UserDeleteView
from .groups import (
    GroupListView, GroupDetailView, GroupCreateView, GroupEditView,
    GroupDeleteView, GroupAddMemberView, GroupRemoveMemberView,
)
from .audit import AuditLogView
from .placeholders import BlueprintsListView
from .connections import (
    ConnectionListView,
    ConnectionDetailView,
    ConnectionTestView,
    ConnectionDeleteView,
    ConnectionCreateDispatchView,
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
    'UserListView', 'UserCreateView', 'UserEditView', 'UserDeleteView',
    'GroupListView', 'GroupDetailView', 'GroupCreateView', 'GroupEditView',
    'GroupDeleteView', 'GroupAddMemberView', 'GroupRemoveMemberView',
    'AuditLogView',
    'BlueprintsListView',
    'ConnectionListView', 'ConnectionDetailView', 'ConnectionTestView',
    'ConnectionDeleteView', 'ConnectionCreateDispatchView',
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
