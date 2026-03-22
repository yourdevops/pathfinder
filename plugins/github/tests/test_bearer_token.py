"""Tests for GitHub plugin authenticated API calls.

Verifies that get_job_logs and resolve_artifact_ref authenticate
using the token from config, not from PyGithub private internals.
"""

from unittest.mock import MagicMock, patch

import pytest

from plugins.github.plugin import GitHubPlugin


@pytest.fixture()
def plugin():
    return GitHubPlugin()


PAT_CONFIG = {"auth_type": "token", "personal_token": "ghp_test_token_123"}
APP_CONFIG = {"auth_type": "app", "app_id": "1", "private_key": "k", "installation_id": "2"}


class TestGetJobLogs:
    """get_job_logs must send Authorization header derived from config."""

    @patch("plugins.github.plugin.requests")
    def test_pat_auth_sends_correct_token(self, mock_requests, plugin):
        mock_requests.get.return_value = MagicMock(status_code=200, text="log output")

        # Mock _get_github_client so the token can NOT come from PyGithub internals
        with patch.object(plugin, "_get_github_client"):
            result = plugin.get_job_logs(PAT_CONFIG, "owner/repo", 42)

        assert result == "log output"
        headers = mock_requests.get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer ghp_test_token_123"

    @patch("plugins.github.plugin.requests")
    def test_app_auth_sends_installation_token(self, mock_requests, plugin):
        mock_requests.get.return_value = MagicMock(status_code=200, text="app logs")

        with (
            patch.object(plugin, "_get_github_client"),
            patch.object(plugin, "_get_installation_token", return_value="ghs_app_token"),
        ):
            result = plugin.get_job_logs(APP_CONFIG, "owner/repo", 42)

        assert result == "app logs"
        headers = mock_requests.get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer ghs_app_token"


class TestResolveArtifactRef:
    """resolve_artifact_ref must send Authorization header derived from config."""

    @patch("plugins.github.plugin.requests")
    def test_pat_auth_sends_correct_token(self, mock_requests, plugin):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = [{"metadata": {"container": {"tags": ["sha-abc1234", "latest"]}}}]
        mock_requests.get.return_value = mock_response

        mock_run = MagicMock(head_sha="abc1234full")
        mock_repo = MagicMock()
        mock_repo.get_workflow_run.return_value = mock_run
        with patch.object(plugin, "_get_github_client") as mock_client:
            mock_client.return_value.get_repo.return_value = mock_repo
            result = plugin.resolve_artifact_ref(PAT_CONFIG, "owner/repo", 99)

        assert result == "ghcr.io/owner/repo:sha-abc1234"
        headers = mock_requests.get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer ghp_test_token_123"
