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
    # Base forms
    "UnlockForm",
    "AdminRegistrationForm",
    "LoginForm",
    "UserCreateForm",
    "UserEditForm",
    "GroupCreateForm",
    "GroupEditForm",
    "GroupAddMemberForm",
    "ProjectCreateForm",
    "ProjectUpdateForm",
    "EnvironmentForm",
    "AddProjectMemberForm",
    "AttachConnectionForm",
    "ConnectionConfigUpdateForm",
    "SiteConfigurationForm",
    "SYSTEM_ROLE_CHOICES",
    "PROJECT_ROLE_CHOICES",
    # Service wizard forms
    "ProjectStepForm",
    "RepositoryStepForm",
    "ConfigurationStepForm",
    "ReviewStepForm",
]
