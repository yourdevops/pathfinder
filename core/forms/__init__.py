"""Forms package for core app."""

# Re-export all forms from base module (previously forms.py)
from core.forms.base import (
    PROJECT_ROLE_CHOICES,
    SYSTEM_ROLE_CHOICES,
    AddProjectMemberForm,
    AdminRegistrationForm,
    AttachConnectionForm,
    ConnectionConfigUpdateForm,
    EnvironmentForm,
    GroupAddMemberForm,
    GroupCreateForm,
    GroupEditForm,
    LoginForm,
    ProjectCreateForm,
    ProjectUpdateForm,
    RetentionSettingsForm,
    SiteConfigurationForm,
    UnlockForm,
    UserCreateForm,
    UserEditForm,
)

# Service wizard forms
from core.forms.services import (
    ConfigurationStepForm,
    ProjectStepForm,
    RepositoryStepForm,
    ReviewStepForm,
)

__all__ = [
    "PROJECT_ROLE_CHOICES",
    "SYSTEM_ROLE_CHOICES",
    "AddProjectMemberForm",
    "AdminRegistrationForm",
    "AttachConnectionForm",
    "ConfigurationStepForm",
    "ConnectionConfigUpdateForm",
    "EnvironmentForm",
    "GroupAddMemberForm",
    "GroupCreateForm",
    "GroupEditForm",
    "LoginForm",
    "ProjectCreateForm",
    "ProjectStepForm",
    "ProjectUpdateForm",
    "RepositoryStepForm",
    "RetentionSettingsForm",
    "ReviewStepForm",
    "SiteConfigurationForm",
    "UnlockForm",
    "UserCreateForm",
    "UserEditForm",
]
