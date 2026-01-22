from .setup import UnlockView, AdminRegistrationView
from .auth import LoginView, LogoutView
from .users import UserListView, UserCreateView, UserEditView, UserDeleteView
from .groups import (
    GroupListView, GroupDetailView, GroupCreateView, GroupEditView,
    GroupDeleteView, GroupAddMemberView, GroupRemoveMemberView,
)

__all__ = [
    'UnlockView', 'AdminRegistrationView',
    'LoginView', 'LogoutView',
    'UserListView', 'UserCreateView', 'UserEditView', 'UserDeleteView',
    'GroupListView', 'GroupDetailView', 'GroupCreateView', 'GroupEditView',
    'GroupDeleteView', 'GroupAddMemberView', 'GroupRemoveMemberView',
]
