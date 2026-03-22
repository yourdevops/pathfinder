from core.models.auth import ApiToken, Group, GroupMembership, User
from core.models.ci import (
    Build,
    CIStep,
    CIWorkflow,
    CIWorkflowStep,
    CIWorkflowVersion,
    ProjectApprovedWorkflow,
    ProjectCIConfig,
    RuntimeFamily,
    compute_manifest_hash,
)
from core.models.config import SiteConfiguration
from core.models.connections import (
    EnvironmentConnection,
    IntegrationConnection,
    ProjectConnection,
)
from core.models.projects import Environment, Project, ProjectMembership
from core.models.services import Service
from core.models.steps import StepsRepository, StepsRepoSyncLog, StepSyncEntry
from core.models.templates import ProjectTemplateConfig, Template, TemplateVersion

__all__ = [
    "ApiToken",
    "Build",
    "CIStep",
    "CIWorkflow",
    "CIWorkflowStep",
    "CIWorkflowVersion",
    "Environment",
    "EnvironmentConnection",
    "Group",
    "GroupMembership",
    "IntegrationConnection",
    "Project",
    "ProjectApprovedWorkflow",
    "ProjectCIConfig",
    "ProjectConnection",
    "ProjectMembership",
    "ProjectTemplateConfig",
    "RuntimeFamily",
    "Service",
    "SiteConfiguration",
    "StepSyncEntry",
    "StepsRepoSyncLog",
    "StepsRepository",
    "Template",
    "TemplateVersion",
    "User",
    "compute_manifest_hash",
    "get_available_templates_for_project",
    "get_available_workflows_for_project",
]


def get_available_workflows_for_project(project):
    """Return queryset of CI workflows available for a project."""
    try:
        ci_config = project.ci_config
    except ProjectCIConfig.DoesNotExist:
        ci_config = None
    if ci_config and ci_config.approve_all_published:
        return CIWorkflow.objects.filter(status="published")
    approved_ids = project.approved_workflows.values_list("workflow_id", flat=True)
    return CIWorkflow.objects.filter(id__in=approved_ids, status="published")


def get_available_templates_for_project(project):
    """Return queryset of templates available for a project."""
    try:
        tpl_config = project.template_config
    except ProjectTemplateConfig.DoesNotExist:
        tpl_config = None
    if tpl_config and tpl_config.allowed_templates.exists():
        return tpl_config.allowed_templates.filter(sync_status="synced")
    return Template.objects.filter(sync_status="synced")


# Register models with auditlog
from auditlog.registry import auditlog  # noqa: E402

auditlog.register(User, exclude_fields=["password", "last_login"])
auditlog.register(Group)
auditlog.register(GroupMembership)
auditlog.register(Project)
auditlog.register(Environment)
auditlog.register(ProjectMembership)
auditlog.register(ApiToken)
auditlog.register(SiteConfiguration)
auditlog.register(IntegrationConnection, exclude_fields=["config_encrypted"])
auditlog.register(ProjectConnection)
auditlog.register(EnvironmentConnection)
auditlog.register(Service)
auditlog.register(StepsRepository)
auditlog.register(StepsRepoSyncLog)
auditlog.register(StepSyncEntry)
auditlog.register(CIStep)
auditlog.register(CIWorkflow)
auditlog.register(CIWorkflowStep)
auditlog.register(ProjectApprovedWorkflow)
auditlog.register(ProjectCIConfig)
auditlog.register(CIWorkflowVersion)
auditlog.register(Build)
auditlog.register(Template)
auditlog.register(TemplateVersion)
