"""Forms package for core app."""
# Re-export all forms from base module (previously forms.py)
from core.forms.base import (
    UnlockForm,
    AdminRegistrationForm,
    LoginForm,
    UserCreateForm,
    UserEditForm,
    GroupCreateForm,
    GroupEditForm,
    GroupAddMemberForm,
    ProjectCreateForm,
    ProjectUpdateForm,
    EnvironmentForm,
    AddProjectMemberForm,
    AttachConnectionForm,
    ConnectionConfigUpdateForm,
    SiteConfigurationForm,
    SYSTEM_ROLE_CHOICES,
    PROJECT_ROLE_CHOICES,
)

# Service wizard forms
from core.forms.services import (
    BlueprintStepForm,
    RepositoryStepForm,
    ConfigurationStepForm,
    ReviewStepForm,
)

__all__ = [
    # Base forms
    'UnlockForm',
    'AdminRegistrationForm',
    'LoginForm',
    'UserCreateForm',
    'UserEditForm',
    'GroupCreateForm',
    'GroupEditForm',
    'GroupAddMemberForm',
    'ProjectCreateForm',
    'ProjectUpdateForm',
    'EnvironmentForm',
    'AddProjectMemberForm',
    'AttachConnectionForm',
    'ConnectionConfigUpdateForm',
    'SiteConfigurationForm',
    'SYSTEM_ROLE_CHOICES',
    'PROJECT_ROLE_CHOICES',
    # Service wizard forms
    'BlueprintStepForm',
    'RepositoryStepForm',
    'ConfigurationStepForm',
    'ReviewStepForm',
]
