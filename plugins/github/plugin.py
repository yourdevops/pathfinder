"""
GitHub integration plugin.

This module provides the GitHubPlugin class implementing GitHub App authentication
and repository operations via the PyGithub library.
"""

from typing import Any

from github import Auth, Github, GithubIntegration
from github.GithubException import GithubException

from plugins.base import BasePlugin


class GitHubPlugin(BasePlugin):
    """
    GitHub integration plugin using GitHub App authentication.

    Supports repository management, branch creation, file commits,
    and webhook configuration via the GitHub API.
    """

    name = "github"
    display_name = "GitHub"
    category = "scm"
    capabilities = ["list_repos", "create_repo", "create_branch", "commit", "webhooks"]
    icon = "github"  # Maps to SVG icon in templates

    def get_config_schema(self) -> dict[str, Any]:
        """Return the configuration schema for GitHub connections."""
        return {
            "auth_type": {
                "type": "string",
                "required": True,
                "label": "Authentication Type",
            },
            "app_id": {"type": "string", "required": False, "label": "App ID"},
            "private_key": {
                "type": "string",
                "required": False,
                "sensitive": True,
                "editable": True,
                "label": "Private Key",
            },
            "installation_id": {
                "type": "string",
                "required": False,
                "label": "Installation ID",
            },
            "personal_token": {
                "type": "string",
                "required": False,
                "sensitive": True,
                "editable": True,
                "label": "Personal Access Token",
            },
            "webhook_secret": {
                "type": "string",
                "required": False,
                "sensitive": True,
                "label": "Webhook Secret",
            },
            "base_url": {
                "type": "string",
                "required": False,
                "label": "GitHub Enterprise URL",
            },
            "organization": {
                "type": "string",
                "required": False,
                "label": "Organization",
            },
        }

    def get_wizard_forms(self) -> list:
        """Return the form classes for connection setup."""
        from .forms import GitHubConnectionForm

        return [GitHubConnectionForm]

    def _get_github_client_pat(self, config: dict[str, Any]) -> Github:
        """
        Get GitHub client using Personal Access Token.

        Args:
            config: The decrypted configuration dictionary.

        Returns:
            Authenticated Github client instance.
        """
        token = config["personal_token"]
        base_url = config.get("base_url")
        if base_url:
            return Github(auth=Auth.Token(token), base_url=base_url)
        return Github(auth=Auth.Token(token))

    def _get_github_client_app(self, config: dict[str, Any]) -> Github:
        """
        Get authenticated GitHub client for GitHub App installation.

        Args:
            config: The decrypted configuration dictionary.

        Returns:
            Authenticated Github client instance.
        """
        app_id = int(config["app_id"])
        private_key = config["private_key"]
        installation_id = int(config["installation_id"])
        base_url = config.get("base_url")

        # Create App authentication
        auth = Auth.AppAuth(app_id, private_key)

        # Get GithubIntegration for installation token
        gi = GithubIntegration(auth=auth, base_url=base_url) if base_url else GithubIntegration(auth=auth)

        # Get installation access token
        installation_auth = gi.get_access_token(installation_id)

        # Create Github client with installation token
        if base_url:
            return Github(auth=Auth.Token(installation_auth.token), base_url=base_url)
        return Github(auth=Auth.Token(installation_auth.token))

    def _get_github_client(self, config: dict[str, Any]) -> Github:
        """
        Get authenticated GitHub client based on auth type.

        Routes to PAT or GitHub App authentication based on config.

        Args:
            config: The decrypted configuration dictionary.

        Returns:
            Authenticated Github client instance.
        """
        auth_type = config.get("auth_type", "app")
        if auth_type == "token":
            return self._get_github_client_pat(config)
        return self._get_github_client_app(config)

    def health_check(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Check GitHub connection health.

        Args:
            config: The decrypted configuration dictionary.

        Returns:
            Dictionary with status, message, and details.
        """
        try:
            g = self._get_github_client(config)
            # Get authenticated user and rate limit to verify connection
            user = g.get_user()
            rate = g.get_rate_limit()

            return {
                "status": "healthy",
                "message": f"Connected as {user.login} ({rate.rate.remaining}/{rate.rate.limit} API calls/hour remaining)",
                "details": {
                    "authenticated_user": user.login,
                    "rate_limit_remaining": rate.rate.remaining,
                    "rate_limit_limit": rate.rate.limit,
                    "rate_limit_reset": rate.rate.reset.isoformat() if rate.rate.reset else None,
                },
            }
        except GithubException as e:
            error_msg = e.data.get("message", str(e)) if isinstance(e.data, dict) else str(e)
            return {
                "status": "unhealthy",
                "message": f"GitHub API error: {error_msg}",
                "details": {"error_code": e.status},
            }
        except Exception as e:
            return {"status": "unhealthy", "message": str(e), "details": {}}

    def list_repositories(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """
        List all accessible repositories.

        Args:
            config: The decrypted configuration dictionary.

        Returns:
            List of dicts with: name, full_name, description, html_url,
            clone_url, private, default_branch, language, updated_at
        """
        g = self._get_github_client(config)
        org_name = config.get("organization")

        if org_name:
            org = g.get_organization(org_name)
            repos = org.get_repos()
        else:
            # For PAT, list user's repos; for App, use installation repos
            repos = g.get_user().get_repos()

        return [
            {
                "name": r.name,
                "full_name": r.full_name,
                "description": r.description or "",
                "html_url": r.html_url,
                "clone_url": r.clone_url,
                "private": r.private,
                "default_branch": r.default_branch,
                "language": r.language or "Unknown",
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in repos
        ]

    def create_repository(
        self,
        config: dict[str, Any],
        name: str,
        description: str = "",
        private: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new repository.

        Args:
            config: The decrypted configuration dictionary.
            name: Repository name.
            description: Optional repository description.
            private: Whether the repository should be private.

        Returns:
            Dictionary with repository details.
        """
        g = self._get_github_client(config)
        org_name = config.get("organization")

        if org_name:
            org = g.get_organization(org_name)
            repo = org.create_repo(name, description=description, private=private)
        else:
            user = g.get_user()
            repo = user.create_repo(name, description=description, private=private)

        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "clone_url": repo.clone_url,
            "html_url": repo.html_url,
        }

    def create_branch(
        self,
        config: dict[str, Any],
        repo_name: str,
        branch_name: str,
        source_branch: str = "main",
    ) -> dict[str, Any]:
        """
        Create a new branch from source.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            branch_name: Name for the new branch.
            source_branch: Source branch to create from.

        Returns:
            Dictionary with branch reference details.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)

        source = repo.get_branch(source_branch)
        sha = source.commit.sha
        ref = repo.create_git_ref(f"refs/heads/{branch_name}", sha)

        return {
            "ref": ref.ref,
            "sha": ref.object.sha,
        }

    def create_file(
        self,
        config: dict[str, Any],
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """
        Create or update a file in the repository.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            path: File path within the repository.
            content: File content.
            message: Commit message.
            branch: Target branch.

        Returns:
            Dictionary with file and commit details.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)

        result = repo.create_file(path, message, content, branch=branch)

        return {
            "path": result["content"].path,
            "sha": result["content"].sha,
            "commit_sha": result["commit"].sha,
        }

    def update_or_create_file(
        self,
        config: dict[str, Any],
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """
        Create or update a file in a GitHub repository.

        If the file already exists on the given branch, it is updated.
        Otherwise, a new file is created.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            path: File path within the repository.
            content: File content.
            message: Commit message.
            branch: Target branch.

        Returns:
            Dictionary with file path, SHA, and commit SHA.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        try:
            existing = repo.get_contents(path, ref=branch)
            result = repo.update_file(path, message, content, existing.sha, branch=branch)
        except Exception:
            result = repo.create_file(path, message, content, branch=branch)
        return {
            "path": result["content"].path,
            "sha": result["content"].sha,
            "commit_sha": result["commit"].sha,
        }

    def configure_webhook(
        self,
        config: dict[str, Any],
        repo_name: str,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Configure webhook on repository.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            webhook_url: URL to receive webhook events.
            events: List of events to subscribe to.

        Returns:
            Dictionary with webhook details.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        webhook_secret = config.get("webhook_secret", "")

        if events is None:
            events = ["push", "pull_request", "workflow_run"]

        hook_config = {
            "url": webhook_url,
            "content_type": "json",
        }
        if webhook_secret:
            hook_config["secret"] = webhook_secret

        hook = repo.create_hook("web", hook_config, events=events, active=True)

        return {
            "id": hook.id,
            "url": hook.url,
            "events": hook.events,
        }

    def create_pull_request(
        self,
        config: dict[str, Any],
        repo_url: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        """
        Create a pull request.

        Args:
            config: The decrypted configuration dictionary.
            repo_url: Repository URL (to extract owner/repo).
            title: Pull request title.
            body: Pull request description.
            head: Source branch name.
            base: Target branch name.

        Returns:
            Dictionary with PR details including html_url.
        """
        from core.git_utils import parse_git_url

        # Parse repo URL to get owner/repo
        parsed = parse_git_url(repo_url)
        if not parsed:
            raise ValueError(f"Invalid repository URL: {repo_url}")

        repo_name = f"{parsed['owner']}/{parsed['repo']}"

        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)

        pr = repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
        )

        return {
            "number": pr.number,
            "html_url": pr.html_url,
            "state": pr.state,
        }

    def get_urlpatterns(self) -> list:
        """Return URL patterns for this plugin's views."""
        from . import urls

        return urls.urlpatterns
