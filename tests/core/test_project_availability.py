"""Tests for get_available_workflows_for_project / get_available_templates_for_project."""

import pytest

from core.models import (
    CIWorkflow,
    Project,
    ProjectApprovedWorkflow,
    ProjectCIConfig,
    ProjectTemplateConfig,
    Template,
    get_available_templates_for_project,
    get_available_workflows_for_project,
)


@pytest.fixture()
def project(db):
    return Project.objects.create(name="avail-project")


# ── Workflows ────────────────────────────────────────────────────────


class TestGetAvailableWorkflows:
    @pytest.fixture()
    def published(self, db):
        return CIWorkflow.objects.create(name="wf-pub", status="published")

    @pytest.fixture()
    def draft(self, db):
        return CIWorkflow.objects.create(name="wf-draft", status="draft")

    @pytest.fixture()
    def archived(self, db):
        return CIWorkflow.objects.create(name="wf-arch", status="archived")

    def test_no_ci_config_no_approvals_returns_empty(self, project):
        qs = get_available_workflows_for_project(project)
        assert list(qs) == []

    def test_explicit_approval_returns_published_only(self, project, published, draft):
        ProjectApprovedWorkflow.objects.create(project=project, workflow=published)
        ProjectApprovedWorkflow.objects.create(project=project, workflow=draft)

        qs = get_available_workflows_for_project(project)
        assert list(qs) == [published]

    def test_approve_all_published_returns_all_published(self, project, published, draft, archived):
        ProjectCIConfig.objects.create(project=project, approve_all_published=True)

        qs = get_available_workflows_for_project(project)
        assert list(qs) == [published]

    def test_approve_all_false_falls_back_to_explicit(self, project, published):
        ProjectCIConfig.objects.create(project=project, approve_all_published=False)

        # No approvals → empty
        assert list(get_available_workflows_for_project(project)) == []

        # Add approval → visible
        ProjectApprovedWorkflow.objects.create(project=project, workflow=published)
        assert list(get_available_workflows_for_project(project)) == [published]

    def test_approved_but_archived_excluded(self, project, archived):
        ProjectApprovedWorkflow.objects.create(project=project, workflow=archived)

        qs = get_available_workflows_for_project(project)
        assert list(qs) == []


# ── Templates ────────────────────────────────────────────────────────


class TestGetAvailableTemplates:
    @pytest.fixture()
    def synced(self, db):
        return Template.objects.create(name="tpl-synced", git_url="https://example.com/a", sync_status="synced")

    @pytest.fixture()
    def pending(self, db):
        return Template.objects.create(name="tpl-pending", git_url="https://example.com/b", sync_status="pending")

    def test_no_config_returns_all_synced(self, project, synced, pending):
        qs = get_available_templates_for_project(project)
        assert list(qs) == [synced]

    def test_allowed_list_filters_to_synced_subset(self, project, synced, pending):
        config = ProjectTemplateConfig.objects.create(project=project)
        config.allowed_templates.add(synced, pending)

        qs = get_available_templates_for_project(project)
        assert list(qs) == [synced]

    def test_empty_allowed_list_falls_back_to_all_synced(self, project, synced):
        ProjectTemplateConfig.objects.create(project=project)

        qs = get_available_templates_for_project(project)
        assert list(qs) == [synced]

    def test_allowed_template_not_synced_excluded(self, project, pending):
        config = ProjectTemplateConfig.objects.create(project=project)
        config.allowed_templates.add(pending)

        qs = get_available_templates_for_project(project)
        assert list(qs) == []
