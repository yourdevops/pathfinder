"""Tests for critical business logic in core.tasks modules."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from core.models import (
    Build,
    CIWorkflow,
    CIWorkflowVersion,
    IntegrationConnection,
    Project,
    Service,
    compute_manifest_hash,
)
from core.tasks.builds import activate_service_on_first_success, verify_build
from core.tasks.scanning import _classify_change
from core.tasks.versions import auto_update_services, is_patch_bump

# ---------------------------------------------------------------------------
# _classify_change
# ---------------------------------------------------------------------------


class ClassifyChangeTest(TestCase):
    """Test _classify_change correctly categorises step field diffs."""

    def _make_step(self, **overrides):
        defaults = {
            "inputs_schema": {"src": {"required": True}},
            "outputs_schema": {"image": {"description": "built image"}},
            "runtime_constraints": {"python": "3.12"},
            "produces": ["docker-image"],
            "phase": "build",
            "tags": ["docker", "python"],
            "description": "Build a container image",
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_no_change_returns_none(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": step.inputs_schema,
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": step.runtime_constraints,
            "produces": step.produces,
            "phase": step.phase,
            "tags": step.tags,
            "description": step.description,
        }
        self.assertIsNone(_classify_change(step, new_fields))

    def test_description_only_is_metadata(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": step.inputs_schema,
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": step.runtime_constraints,
            "produces": step.produces,
            "phase": step.phase,
            "tags": step.tags,
            "description": "Updated description",
        }
        self.assertEqual(_classify_change(step, new_fields), "metadata")

    def test_tags_only_is_metadata(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": step.inputs_schema,
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": step.runtime_constraints,
            "produces": step.produces,
            "phase": step.phase,
            "tags": ["docker", "python", "new-tag"],
            "description": step.description,
        }
        self.assertEqual(_classify_change(step, new_fields), "metadata")

    def test_inputs_change_is_interface(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": {"src": {"required": True}, "extra": {"required": False}},
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": step.runtime_constraints,
            "produces": step.produces,
            "phase": step.phase,
            "tags": step.tags,
            "description": step.description,
        }
        self.assertEqual(_classify_change(step, new_fields), "interface")

    def test_outputs_change_is_interface(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": step.inputs_schema,
            "outputs_schema": {"image": {"description": "changed"}},
            "runtime_constraints": step.runtime_constraints,
            "produces": step.produces,
            "phase": step.phase,
            "tags": step.tags,
            "description": step.description,
        }
        self.assertEqual(_classify_change(step, new_fields), "interface")

    def test_phase_change_is_interface(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": step.inputs_schema,
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": step.runtime_constraints,
            "produces": step.produces,
            "phase": "test",
            "tags": step.tags,
            "description": step.description,
        }
        self.assertEqual(_classify_change(step, new_fields), "interface")

    def test_runtime_constraints_change_is_interface(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": step.inputs_schema,
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": {"python": "3.13"},
            "produces": step.produces,
            "phase": step.phase,
            "tags": step.tags,
            "description": step.description,
        }
        self.assertEqual(_classify_change(step, new_fields), "interface")

    def test_produces_change_is_interface(self):
        step = self._make_step()
        new_fields = {
            "inputs_schema": step.inputs_schema,
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": step.runtime_constraints,
            "produces": ["docker-image", "sbom"],
            "phase": step.phase,
            "tags": step.tags,
            "description": step.description,
        }
        self.assertEqual(_classify_change(step, new_fields), "interface")

    def test_interface_trumps_metadata(self):
        """When both interface and metadata fields change, interface wins."""
        step = self._make_step()
        new_fields = {
            "inputs_schema": {"completely": "different"},
            "outputs_schema": step.outputs_schema,
            "runtime_constraints": step.runtime_constraints,
            "produces": step.produces,
            "phase": step.phase,
            "tags": ["changed-tag"],
            "description": "Also changed",
        }
        self.assertEqual(_classify_change(step, new_fields), "interface")


# ---------------------------------------------------------------------------
# is_patch_bump
# ---------------------------------------------------------------------------


class IsPatchBumpTest(TestCase):
    """Test is_patch_bump correctly identifies patch-level version bumps."""

    def test_patch_bump(self):
        self.assertTrue(is_patch_bump("1.2.3", "1.2.4"))

    def test_patch_bump_large_numbers(self):
        self.assertTrue(is_patch_bump("1.2.99", "1.2.100"))

    def test_minor_bump_is_not_patch(self):
        self.assertFalse(is_patch_bump("1.2.3", "1.3.0"))

    def test_major_bump_is_not_patch(self):
        self.assertFalse(is_patch_bump("1.2.3", "2.0.0"))

    def test_same_version_is_not_patch(self):
        self.assertFalse(is_patch_bump("1.2.3", "1.2.3"))

    def test_downgrade_is_not_patch(self):
        self.assertFalse(is_patch_bump("1.2.5", "1.2.3"))

    def test_invalid_current_version(self):
        self.assertFalse(is_patch_bump("not-semver", "1.2.4"))

    def test_invalid_new_version(self):
        self.assertFalse(is_patch_bump("1.2.3", "garbage"))

    def test_both_invalid(self):
        self.assertFalse(is_patch_bump("x", "y"))

    def test_prerelease_patch_bump(self):
        """Pre-release on new version: still same major.minor, but semver ordering applies."""
        # 1.2.4-rc.1 < 1.2.4, and 1.2.4-rc.1 > 1.2.3, so it IS a patch bump
        self.assertTrue(is_patch_bump("1.2.3", "1.2.4-rc.1"))

    def test_zero_major(self):
        self.assertTrue(is_patch_bump("0.1.0", "0.1.1"))


# ---------------------------------------------------------------------------
# activate_service_on_first_success
# ---------------------------------------------------------------------------


class ActivateServiceOnFirstSuccessTest(TestCase):
    """Test the draft → active state transition on first successful build."""

    def setUp(self):
        self.project = Project.objects.create(name="test-proj")
        self.service = Service.objects.create(
            project=self.project,
            name="test-svc",
            status="draft",
        )

    def _make_build(self, status="success", **kwargs):
        return Build.objects.create(
            service=self.service,
            ci_run_id=kwargs.pop("ci_run_id", 1000 + Build.objects.count()),
            status=status,
            **kwargs,
        )

    def test_activates_on_first_success(self):
        build = self._make_build(status="success")
        activate_service_on_first_success(build)

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, "active")
        self.assertEqual(self.service.current_build_id, build.id)

    def test_noop_when_already_active(self):
        self.service.status = "active"
        self.service.save(update_fields=["status"])

        build = self._make_build(status="success")
        activate_service_on_first_success(build)

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, "active")
        # current_build_id should NOT be updated
        self.assertIsNone(self.service.current_build_id)

    def test_noop_for_failed_build(self):
        """Non-success builds never trigger activation, even with no prior successes."""
        build = self._make_build(status="failed")
        activate_service_on_first_success(build)

        self.service.refresh_from_db()
        self.assertEqual(self.service.status, "draft")


# ---------------------------------------------------------------------------
# verify_build
# ---------------------------------------------------------------------------


class VerifyBuildTest(TestCase):
    """Test build manifest verification against authorized workflow versions."""

    def setUp(self):
        self.project = Project.objects.create(name="verify-proj")
        self.workflow = CIWorkflow.objects.create(name="ci-python", engine="github_actions")
        self.connection = IntegrationConnection.objects.create(
            name="gh-conn",
            plugin_name="github",
        )
        self.service = Service.objects.create(
            project=self.project,
            name="verify-svc",
            ci_workflow=self.workflow,
        )

    def _make_build(self, **kwargs):
        defaults = {
            "service": self.service,
            "ci_run_id": 2000 + Build.objects.count(),
            "status": "success",
            "commit_sha": "abc123",
            "branch": "main",
        }
        defaults.update(kwargs)
        return Build.objects.create(**defaults)

    def test_skips_already_verified(self):
        build = self._make_build(verification_status="verified")
        result = verify_build.call(build.id, self.connection.id, "owner/repo")
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "already verified")

    def test_skips_non_terminal_build(self):
        build = self._make_build(status="running")
        result = verify_build.call(build.id, self.connection.id, "owner/repo")
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "not terminal")

    def test_unauthorized_when_no_workflow(self):
        self.service.ci_workflow = None
        self.service.save(update_fields=["ci_workflow"])

        build = self._make_build()
        result = verify_build.call(build.id, self.connection.id, "owner/repo")

        build.refresh_from_db()
        self.assertEqual(result["status"], "unauthorized")
        self.assertEqual(build.verification_status, "unauthorized")

    def test_unauthorized_when_manifest_not_found(self):
        manifest_content = "name: ci-python\non: push\njobs: {}"
        CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.0",
            status=CIWorkflowVersion.Status.AUTHORIZED,
            manifest_hash=compute_manifest_hash(manifest_content),
            manifest_content=manifest_content,
        )
        build = self._make_build()

        with patch("plugins.base.get_ci_plugin_for_engine") as mock_get_plugin:
            mock_plugin = mock_get_plugin.return_value
            mock_plugin.manifest_id.return_value = ".github/workflows/ci-python.yml"
            mock_plugin.fetch_manifest_content.return_value = None  # not found

            result = verify_build.call(build.id, self.connection.id, "owner/repo")

        build.refresh_from_db()
        self.assertEqual(result["status"], "unauthorized")
        self.assertEqual(build.verification_status, "unauthorized")

    def test_verified_when_hash_matches_authorized_version(self):
        manifest_content = "name: ci-python\non: push\njobs: {}"
        version = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.0",
            status=CIWorkflowVersion.Status.AUTHORIZED,
            manifest_hash=compute_manifest_hash(manifest_content),
            manifest_content=manifest_content,
        )
        build = self._make_build()

        with patch("plugins.base.get_ci_plugin_for_engine") as mock_get_plugin:
            mock_plugin = mock_get_plugin.return_value
            mock_plugin.manifest_id.return_value = ".github/workflows/ci-python.yml"
            mock_plugin.fetch_manifest_content.return_value = manifest_content

            result = verify_build.call(build.id, self.connection.id, "owner/repo")

        build.refresh_from_db()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(build.verification_status, "verified")
        self.assertEqual(build.workflow_version_id, version.id)

    def test_draft_when_hash_matches_draft_version(self):
        manifest_content = "name: ci-python\non: push\njobs: {}"
        CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.1.0",
            status=CIWorkflowVersion.Status.DRAFT,
            manifest_hash=compute_manifest_hash(manifest_content),
            manifest_content=manifest_content,
        )
        build = self._make_build()

        with patch("plugins.base.get_ci_plugin_for_engine") as mock_get_plugin:
            mock_plugin = mock_get_plugin.return_value
            mock_plugin.manifest_id.return_value = ".github/workflows/ci-python.yml"
            mock_plugin.fetch_manifest_content.return_value = manifest_content

            result = verify_build.call(build.id, self.connection.id, "owner/repo")

        build.refresh_from_db()
        self.assertEqual(result["status"], "draft")
        self.assertEqual(build.verification_status, "draft")

    def test_revoked_when_hash_matches_revoked_version(self):
        manifest_content = "name: ci-python\non: push\njobs: {}"
        CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="0.9.0",
            status=CIWorkflowVersion.Status.REVOKED,
            manifest_hash=compute_manifest_hash(manifest_content),
            manifest_content=manifest_content,
        )
        build = self._make_build()

        with patch("plugins.base.get_ci_plugin_for_engine") as mock_get_plugin:
            mock_plugin = mock_get_plugin.return_value
            mock_plugin.manifest_id.return_value = ".github/workflows/ci-python.yml"
            mock_plugin.fetch_manifest_content.return_value = manifest_content

            result = verify_build.call(build.id, self.connection.id, "owner/repo")

        build.refresh_from_db()
        self.assertEqual(result["status"], "revoked")
        self.assertEqual(build.verification_status, "revoked")

    def test_unauthorized_when_hash_matches_no_version(self):
        build = self._make_build()

        with patch("plugins.base.get_ci_plugin_for_engine") as mock_get_plugin:
            mock_plugin = mock_get_plugin.return_value
            mock_plugin.manifest_id.return_value = ".github/workflows/ci-python.yml"
            mock_plugin.fetch_manifest_content.return_value = "tampered manifest content"

            result = verify_build.call(build.id, self.connection.id, "owner/repo")

        build.refresh_from_db()
        self.assertEqual(result["status"], "unauthorized")
        self.assertEqual(build.verification_status, "unauthorized")

    def test_pending_pr_transitions_to_synced(self):
        """When verified version matches pinned version on default branch, sync status updates."""
        manifest_content = "name: ci-python\non: push\njobs: {}"
        version = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.0",
            status=CIWorkflowVersion.Status.AUTHORIZED,
            manifest_hash=compute_manifest_hash(manifest_content),
            manifest_content=manifest_content,
        )
        self.service.ci_workflow_version = version
        self.service.ci_manifest_status = "pending_pr"
        self.service.save(update_fields=["ci_workflow_version", "ci_manifest_status"])

        build = self._make_build(branch="main")

        with patch("plugins.base.get_ci_plugin_for_engine") as mock_get_plugin:
            mock_plugin = mock_get_plugin.return_value
            mock_plugin.manifest_id.return_value = ".github/workflows/ci-python.yml"
            mock_plugin.fetch_manifest_content.return_value = manifest_content

            result = verify_build.call(build.id, self.connection.id, "owner/repo")

        self.service.refresh_from_db()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(self.service.ci_manifest_status, "synced")

    def test_pending_pr_not_synced_on_feature_branch(self):
        """pending_pr should NOT transition when build is on a non-default branch."""
        manifest_content = "name: ci-python\non: push\njobs: {}"
        version = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.0",
            status=CIWorkflowVersion.Status.AUTHORIZED,
            manifest_hash=compute_manifest_hash(manifest_content),
            manifest_content=manifest_content,
        )
        self.service.ci_workflow_version = version
        self.service.ci_manifest_status = "pending_pr"
        self.service.save(update_fields=["ci_workflow_version", "ci_manifest_status"])

        build = self._make_build(branch="feature/something")

        with patch("plugins.base.get_ci_plugin_for_engine") as mock_get_plugin:
            mock_plugin = mock_get_plugin.return_value
            mock_plugin.manifest_id.return_value = ".github/workflows/ci-python.yml"
            mock_plugin.fetch_manifest_content.return_value = manifest_content

            result = verify_build.call(build.id, self.connection.id, "owner/repo")

        self.service.refresh_from_db()
        self.assertEqual(result["status"], "verified")
        # Still pending_pr — not synced because branch doesn't match
        self.assertEqual(self.service.ci_manifest_status, "pending_pr")


# ---------------------------------------------------------------------------
# auto_update_services
# ---------------------------------------------------------------------------


class AutoUpdateServicesTest(TestCase):
    """Test patch auto-update filtering, version pinning, and manifest push enqueue."""

    def setUp(self):
        self.project = Project.objects.create(name="auto-proj")
        self.workflow = CIWorkflow.objects.create(name="ci-auto", engine="github_actions")
        self.v1_0_0 = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.0",
            status=CIWorkflowVersion.Status.AUTHORIZED,
        )
        self.v1_0_1 = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.1",
            status=CIWorkflowVersion.Status.AUTHORIZED,
        )

    def _make_service(self, name, pinned_version=None, auto_update=True, **kwargs):
        return Service.objects.create(
            project=self.project,
            name=name,
            ci_workflow=self.workflow,
            ci_workflow_version=pinned_version,
            auto_update_patch=auto_update,
            **kwargs,
        )

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_updates_eligible_service(self, mock_push):
        svc = self._make_service("eligible", pinned_version=self.v1_0_0)

        result = auto_update_services.call(self.workflow.id, self.v1_0_1.id)

        svc.refresh_from_db()
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(svc.ci_workflow_version_id, self.v1_0_1.id)
        self.assertEqual(svc.ci_manifest_status, "pending_pr")
        mock_push.enqueue.assert_called_once_with(service_id=svc.id)

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_skips_service_with_auto_update_disabled(self, mock_push):
        svc = self._make_service("no-auto", pinned_version=self.v1_0_0, auto_update=False)

        result = auto_update_services.call(self.workflow.id, self.v1_0_1.id)

        svc.refresh_from_db()
        self.assertEqual(result["updated"], 0)
        # Service not in queryset at all (auto_update_patch=False)
        self.assertEqual(svc.ci_workflow_version_id, self.v1_0_0.id)
        mock_push.enqueue.assert_not_called()

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_skips_service_without_pinned_version(self, mock_push):
        svc = self._make_service("no-pin", pinned_version=None)

        auto_update_services.call(self.workflow.id, self.v1_0_1.id)

        svc.refresh_from_db()
        self.assertIsNone(svc.ci_workflow_version)
        mock_push.enqueue.assert_not_called()

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_skips_minor_bump(self, mock_push):
        """1.0.0 → 1.1.0 is a minor bump, not a patch — should be skipped."""
        v1_1_0 = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.1.0",
            status=CIWorkflowVersion.Status.AUTHORIZED,
        )
        svc = self._make_service("minor-bump", pinned_version=self.v1_0_0)

        result = auto_update_services.call(self.workflow.id, v1_1_0.id)

        svc.refresh_from_db()
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(svc.ci_workflow_version_id, self.v1_0_0.id)
        mock_push.enqueue.assert_not_called()

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_skips_draft_version(self, mock_push):
        """Draft versions should not trigger auto-update even if patch bump."""
        v1_0_2_draft = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.2",
            status=CIWorkflowVersion.Status.DRAFT,
        )
        svc = self._make_service("draft-ver", pinned_version=self.v1_0_1)

        result = auto_update_services.call(self.workflow.id, v1_0_2_draft.id)

        svc.refresh_from_db()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "not authorized")
        self.assertEqual(svc.ci_workflow_version_id, self.v1_0_1.id)
        mock_push.enqueue.assert_not_called()

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_skips_revoked_version(self, mock_push):
        v1_0_2_revoked = CIWorkflowVersion.objects.create(
            workflow=self.workflow,
            version="1.0.2",
            status=CIWorkflowVersion.Status.REVOKED,
        )
        svc = self._make_service("revoked-ver", pinned_version=self.v1_0_1)

        result = auto_update_services.call(self.workflow.id, v1_0_2_revoked.id)

        svc.refresh_from_db()
        self.assertTrue(result["skipped"])
        self.assertEqual(svc.ci_workflow_version_id, self.v1_0_1.id)
        mock_push.enqueue.assert_not_called()

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_mixed_eligible_and_ineligible(self, mock_push):
        """Multiple services: some eligible, some not."""
        svc_patch = self._make_service("svc-patch", pinned_version=self.v1_0_0)
        self._make_service("svc-no-auto", pinned_version=self.v1_0_0, auto_update=False)
        svc_already_on_latest = self._make_service("svc-latest", pinned_version=self.v1_0_1)

        result = auto_update_services.call(self.workflow.id, self.v1_0_1.id)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["skipped"], 1)  # svc_already_on_latest: same version, not a bump

        svc_patch.refresh_from_db()
        self.assertEqual(svc_patch.ci_workflow_version_id, self.v1_0_1.id)

        svc_already_on_latest.refresh_from_db()
        self.assertEqual(svc_already_on_latest.ci_workflow_version_id, self.v1_0_1.id)  # unchanged

    @patch("core.tasks.ci_setup.push_ci_manifest")
    def test_does_not_touch_other_workflows(self, mock_push):
        """Services on a different workflow should not be affected."""
        other_wf = CIWorkflow.objects.create(name="ci-other", engine="github_actions")
        other_v = CIWorkflowVersion.objects.create(
            workflow=other_wf,
            version="1.0.0",
            status=CIWorkflowVersion.Status.AUTHORIZED,
        )
        svc = Service.objects.create(
            project=self.project,
            name="other-wf-svc",
            ci_workflow=other_wf,
            ci_workflow_version=other_v,
            auto_update_patch=True,
        )

        result = auto_update_services.call(self.workflow.id, self.v1_0_1.id)

        svc.refresh_from_db()
        self.assertEqual(result["updated"], 0)
        self.assertEqual(svc.ci_workflow_version_id, other_v.id)
        mock_push.enqueue.assert_not_called()

    def test_nonexistent_workflow(self):
        result = auto_update_services.call(99999, self.v1_0_1.id)
        self.assertIn("error", result)

    def test_nonexistent_version(self):
        result = auto_update_services.call(self.workflow.id, 99999)
        self.assertIn("error", result)
