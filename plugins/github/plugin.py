# SPDX-License-Identifier: Apache-2.0
"""
GitHub integration plugin.

This module provides the GitHubPlugin class implementing GitHub App authentication
and repository operations via the PyGithub library.
"""

import os
import re
from typing import Any

from github import Auth, Github, GithubIntegration
from github.GithubException import GithubException

from plugins.base import BasePlugin, CICapableMixin

_GH_OUTPUT_REF_RE = re.compile(r"^\$\{\{\s*steps\.([a-z0-9][a-z0-9-]*)\.outputs\.([a-z0-9][a-z0-9_-]*)\s*\}\}$")

GH_API_VERSION = "2026-03-10"
GH_API_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": GH_API_VERSION}


class GitHubPlugin(CICapableMixin, BasePlugin):
    """
    GitHub integration plugin using GitHub App authentication.

    Supports repository management, branch creation, file commits,
    webhook configuration, and CI manifest generation via the GitHub API.
    """

    name = "github"
    display_name = "GitHub"
    category = "scm"
    capabilities = ["list_repos", "create_repo", "create_branch", "commit", "webhooks", "ci"]
    icon = "github"  # Maps to SVG icon in templates

    MANIFEST_ID_PATTERN = re.compile(r"^\.github/workflows/ci-[a-z0-9][a-z0-9-]*\.yml$")

    # --- CICapableMixin implementation ---

    @property
    def engine_name(self) -> str:
        return "github_actions"

    @property
    def engine_display_name(self) -> str:
        return "GitHub Actions"

    @property
    def engine_file_name(self) -> str:
        return "action.yml"

    def parse_step_file(self, file_content: dict) -> dict:
        """Parse GitHub Actions action.yml content and extract x-pathfinder metadata."""
        pathfinder = file_content.get("x-pathfinder", {})
        return {
            "name": file_content.get("name", ""),
            "description": file_content.get("description", ""),
            "inputs": file_content.get("inputs", {}),
            "outputs": file_content.get("outputs", {}),
            "phase": pathfinder.get("phase", ""),
            "runtime_constraints": pathfinder.get("runtimes", {}),
            "tags": pathfinder.get("tags", []),
            "produces": pathfinder.get("produces"),
            "raw_metadata": file_content,
        }

    def derive_step_slug(self, file_content: dict, directory_path: str) -> str:
        """Derive slug for a GitHub Actions step.

        Fallback chain:
          1. x-pathfinder.name
          2. action.yml top-level 'name' field
          3. Full relative directory path
        """
        from django.utils.text import slugify

        # Tier 1: x-pathfinder.name
        pathfinder_name = file_content.get("x-pathfinder", {}).get("name", "")
        if pathfinder_name:
            slug = slugify(pathfinder_name)
            if slug:
                return slug

        # Tier 2: GitHub Actions native 'name' field
        native_name = file_content.get("name", "")
        if native_name:
            slug = slugify(native_name)
            if slug:
                return slug

        # Tier 3: Full relative directory path (e.g., "setup/python" -> "setup-python")
        if directory_path:
            slug = slugify(directory_path.replace("/", "-").replace("\\", "-"))
            if slug:
                return slug

        return ""

    def format_step_id(self, step_slug: str) -> str:
        """Return GitHub Actions step ID (slug is already lowercase with hyphens)."""
        return step_slug

    def format_output_reference(self, step_slug: str, output_name: str) -> str:
        """Return GitHub Actions output reference expression."""
        return f"${{{{ steps.{step_slug}.outputs.{output_name} }}}}"

    def parse_output_reference(self, value: str) -> dict | None:
        """Parse a GitHub Actions output reference expression.

        Returns dict with step_slug and output_name if matched, None otherwise.
        """
        match = _GH_OUTPUT_REF_RE.match(value)
        if match:
            return {"step_slug": match.group(1), "output_name": match.group(2)}
        return None

    def generate_manifest(self, workflow, version: str | None = None) -> str:
        """Generate a GitHub Actions workflow YAML for a CIWorkflow instance.

        Args:
            workflow: CIWorkflow instance.
            version: Optional version string for the header. Defaults to "draft".

        Returns:
            Deterministic manifest string with header comment block.
        """
        import yaml

        from core.git_utils import parse_git_url

        manifest = {
            "name": f"ci-{workflow.name}",
            "on": {
                "push": {"branches": ["main"]},
            },
            "env": {
                "PTF_PROJECT": "${{ vars.PTF_PROJECT }}",
                "PTF_SERVICE": "${{ vars.PTF_SERVICE }}",
            },
            "jobs": {
                "build": {
                    "runs-on": "ubuntu-latest",
                    "steps": [],
                },
            },
        }

        steps_list = manifest["jobs"]["build"]["steps"]

        # Auto-inject: checkout
        steps_list.append(
            {
                "name": "Checkout",
                "uses": "actions/checkout@v4",
            }
        )

        # User-composed steps
        for ws in workflow.workflow_steps.select_related("step__repository").order_by("order"):
            step = ws.step
            repo = step.repository

            # Build uses reference: derive subdirectory from file_path
            # e.g. file_path="setup/python/action.yml" -> step_dir="setup/python"
            step_dir = os.path.dirname(step.file_path) if step.file_path else step.directory_name
            parsed = parse_git_url(repo.git_url)
            if parsed and parsed.get("owner") and parsed.get("repo"):
                uses_ref = f"{parsed['owner']}/{parsed['repo']}/{step_dir}"
                if step.commit_sha:
                    uses_ref += f"@{step.commit_sha}"
                else:
                    uses_ref += "@main"
            else:
                uses_ref = f"./{step_dir}"

            step_entry = {
                "name": step.name,
                "uses": uses_ref,
            }
            step_entry["id"] = self.format_step_id(step.slug)
            if ws.input_config:
                step_entry["with"] = ws.input_config

            steps_list.append(step_entry)

        yaml_body = yaml.dump(manifest, default_flow_style=False, sort_keys=False)

        version_str = version or "draft"
        header = (
            "# ==================================================\n"
            "# Managed by Pathfinder - DO NOT EDIT MANUALLY\n"
            f"# Workflow: {workflow.name}\n"
            f"# Version: {version_str}\n"
            "# ==================================================\n"
        )
        return header + yaml_body

    def manifest_id(self, workflow) -> str:
        """Return manifest identifier based on workflow name."""
        return f".github/workflows/ci-{workflow.name}.yml"

    def extract_manifest_id(self, run_data: dict) -> str | None:
        """Extract manifest identifier from CI run data.

        Returns None if the workflow is not Pathfinder-managed.
        """
        name = run_data.get("name", "")
        if name.startswith("ci-"):
            mid = f".github/workflows/{name}.yml"
            if self.MANIFEST_ID_PATTERN.match(mid):
                return mid
        return None

    def get_manifest_id_pattern(self) -> re.Pattern:
        """Return regex pattern for validating manifest IDs."""
        return self.MANIFEST_ID_PATTERN

    def map_run_status(self, status: str, conclusion: str | None) -> str:
        """Map GitHub Actions run status/conclusion to Build status."""
        if status in ("queued", "in_progress"):
            return "running"
        if status == "completed" and conclusion:
            conclusion_map = {
                "success": "success",
                "failure": "failed",
                "cancelled": "cancelled",
            }
            return conclusion_map.get(conclusion, "pending")
        return "pending"

    def fetch_manifest_content(self, config: dict, repo_name: str, manifest_id: str, commit_sha: str) -> str | None:
        """Fetch manifest file content from repo at a specific commit.

        Returns None if file not found.
        """
        try:
            g = self._get_github_client(config)
            repo = g.get_repo(repo_name)
            content_file = repo.get_contents(manifest_id, ref=commit_sha)
            if isinstance(content_file, list):
                return None  # directory, not file
            return content_file.decoded_content.decode("utf-8")
        except Exception:
            return None

    def find_open_pr(self, config: dict, repo_name: str, branch_name: str) -> dict | None:
        """Find an open PR for the given branch name."""
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        owner = repo.owner.login
        pulls = repo.get_pulls(state="open", head=f"{owner}:{branch_name}")
        for pr in pulls:
            return {"number": pr.number, "html_url": pr.html_url, "title": pr.title}
        return None

    def resolve_artifact_ref(self, config: dict, repo_name: str, run_id: int) -> str:
        """Resolve container image reference from GitHub Packages for a workflow run.

        Queries the GitHub Packages API to find a container image tagged with
        the short SHA of the workflow run's head commit.

        Returns image reference string or empty string if not found.
        """
        import requests

        try:
            g = self._get_github_client(config)
            # Get the run to find the commit SHA
            repo = g.get_repo(repo_name)
            run = repo.get_workflow_run(run_id)
            short_sha = run.head_sha[:7]

            # Query GHCR for container tagged with sha-{short_sha}
            token = g._Github__requester._Requester__auth.token
            base_url = config.get("base_url", "https://api.github.com")
            owner = repo_name.split("/")[0]
            package_name = repo_name.split("/")[1]

            # Try org packages first, then user packages
            for endpoint in [
                f"{base_url}/orgs/{owner}/packages/container/{package_name}/versions",
                f"{base_url}/users/{owner}/packages/container/{package_name}/versions",
            ]:
                headers = {**GH_API_HEADERS, "Authorization": f"Bearer {token}"}
                resp = requests.get(endpoint, headers=headers, timeout=15)
                if resp.status_code == 200:
                    for version in resp.json():
                        tags = version.get("metadata", {}).get("container", {}).get("tags", [])
                        if f"sha-{short_sha}" in tags:
                            return f"ghcr.io/{repo_name}:sha-{short_sha}"
                    # Found the package but no matching tag
                    break

            return ""
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to resolve artifact ref for run {run_id}: {e}")
            return ""

    def provision_ci_variables(self, config: dict, repo_name: str, variables: dict[str, str]) -> dict:
        """Provision GitHub Actions repository variables."""
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        results = {}
        for name, value in variables.items():
            try:
                repo.create_variable(name, value)
                results[name] = "created"
            except GithubException as e:
                if e.status == 409:
                    # Variable already exists -- update it
                    try:
                        var = repo.get_variable(name)
                        var.edit(value)
                        results[name] = "updated"
                    except Exception as update_err:
                        results[name] = f"error: {update_err}"
                else:
                    results[name] = f"error: {e.data.get('message', str(e)) if isinstance(e.data, dict) else str(e)}"
        return results

    def check_branch_protection(self, config: dict, repo_name: str, branch: str) -> dict:
        """Check branch protection rules on a GitHub repository branch."""
        try:
            g = self._get_github_client(config)
            repo = g.get_repo(repo_name)
            branch_obj = repo.get_branch(branch)

            if not branch_obj.protected:
                return {
                    "valid": False,
                    "rules": {},
                    "message": f"Branch '{branch}' has no protection rules configured",
                }

            protection = branch_obj.get_protection()

            rules = {
                "no_force_push": not protection.allow_force_pushes,
                "no_deletions": not protection.allow_deletions,
                "enforce_admins": protection.enforce_admins,
                "requires_pr": False,
                "required_reviews": False,
            }

            # Check that PRs are required (direct pushes disabled) and review count
            try:
                reviews = protection.required_pull_request_reviews
                if reviews is not None:
                    # If required_pull_request_reviews exists, PRs are required
                    rules["requires_pr"] = True
                    if reviews.required_approving_review_count >= 1:
                        rules["required_reviews"] = True
            except GithubException:
                pass  # No PR requirement configured -- both remain False

            valid = all(rules.values())

            failures = [k.replace("_", " ") for k, v in rules.items() if not v]
            if failures:
                message = "Missing protection rules: " + ", ".join(failures)
            else:
                message = "All branch protection rules are satisfied"

            return {"valid": valid, "rules": rules, "message": message}
        except Exception as e:
            return {
                "valid": False,
                "rules": {},
                "message": f"Failed to check branch protection: {e}",
            }

    # --- BasePlugin implementation ---

    def get_webhook_url(self, external_url: str) -> str:
        """Return the full external webhook URL for this plugin."""
        from django.urls import reverse

        webhook_path = reverse("github:webhook")
        return f"{external_url.rstrip('/')}{webhook_path}"

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

    def get_clone_credentials(self, config: dict[str, Any]) -> tuple[str, str] | None:
        """Return credentials for HTTPS git clone operations."""
        auth_type = config.get("auth_type", "token")
        if auth_type == "app":
            token = self._get_installation_token(config)
            return ("x-access-token", token)
        pat = config.get("personal_token")
        return (pat, "") if pat else None

    def _get_installation_token(self, config: dict[str, Any]) -> str:
        """Get a short-lived installation access token for GitHub App."""
        app_id = int(config["app_id"])
        private_key = config["private_key"]
        installation_id = int(config["installation_id"])
        base_url = config.get("base_url")

        auth = Auth.AppAuth(app_id, private_key)
        gi = GithubIntegration(auth=auth, base_url=base_url) if base_url else GithubIntegration(auth=auth)
        installation_auth = gi.get_access_token(installation_id)
        return installation_auth.token

    def _get_github_client_app(self, config: dict[str, Any]) -> Github:
        """
        Get authenticated GitHub client for GitHub App installation.

        Args:
            config: The decrypted configuration dictionary.

        Returns:
            Authenticated Github client instance.
        """
        token = self._get_installation_token(config)
        base_url = config.get("base_url")
        if base_url:
            return Github(auth=Auth.Token(token), base_url=base_url)
        return Github(auth=Auth.Token(token))

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
            rate = g.get_rate_limit()

            auth_type = config.get("auth_type", "app")
            if auth_type == "token":
                # PAT: GET /user works with user-scoped tokens
                user = g.get_user()
                identity = user.login
            else:
                # GitHub App: installation tokens can't call GET /user,
                # use GET /app via the App JWT instead
                app_id = int(config["app_id"])
                private_key = config["private_key"]
                base_url = config.get("base_url")
                auth = Auth.AppAuth(app_id, private_key)
                gi = GithubIntegration(auth=auth, base_url=base_url) if base_url else GithubIntegration(auth=auth)
                app = gi.get_app()
                identity = f"{app.name}[bot]"

            return {
                "status": "healthy",
                "message": f"Connected as {identity} ({rate.rate.remaining}/{rate.rate.limit} API calls/hour remaining)",
                "details": {
                    "authenticated_as": identity,
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

        # Check for existing webhook with the same URL (e.g. re-onboarded repo)
        for existing_hook in repo.get_hooks():
            if existing_hook.config.get("url") == webhook_url:
                existing_hook.edit(
                    name="web",
                    config=hook_config,
                    events=events,
                    active=True,
                )
                return {
                    "id": existing_hook.id,
                    "url": existing_hook.url,
                    "events": existing_hook.events,
                }

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

    def get_workflow_run(self, config: dict[str, Any], repo_name: str, run_id: int) -> dict[str, Any]:
        """
        Fetch workflow run details from GitHub API.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            run_id: The workflow run ID.

        Returns:
            Dictionary with workflow run details.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        run = repo.get_workflow_run(run_id)

        return {
            "id": run.id,
            "run_number": run.run_number,
            "head_sha": run.head_sha,
            "head_branch": run.head_branch,
            "status": run.status,  # queued, in_progress, completed
            "conclusion": run.conclusion,  # success, failure, cancelled, etc.
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "html_url": run.html_url,
            "name": run.name,
            "event": run.event,
            "actor": {
                "login": run.actor.login if run.actor else None,
                "avatar_url": run.actor.avatar_url if run.actor else None,
            },
        }

    def list_workflow_runs(self, config: dict[str, Any], repo_name: str, per_page: int = 10) -> list[dict[str, Any]]:
        """
        List recent workflow runs for a repository.

        Used for manual polling when webhooks are unavailable.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            per_page: Number of runs to fetch (default 10).

        Returns:
            List of workflow run dictionaries.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        runs = repo.get_workflow_runs()[:per_page]

        result = []
        for run in runs:
            result.append(
                {
                    "id": run.id,
                    "run_number": run.run_number,
                    "head_sha": run.head_sha,
                    "head_branch": run.head_branch,
                    "status": run.status,
                    "conclusion": run.conclusion,
                    "created_at": run.created_at,
                    "updated_at": run.updated_at,
                    "html_url": run.html_url,
                    "name": run.name,
                    "event": run.event,
                    "actor": {
                        "login": run.actor.login if run.actor else None,
                        "avatar_url": run.actor.avatar_url if run.actor else None,
                    },
                }
            )
        return result

    def get_commit(self, config: dict[str, Any], repo_name: str, commit_sha: str) -> dict[str, Any]:
        """
        Fetch commit details from GitHub API.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            commit_sha: The commit SHA.

        Returns:
            Dictionary with commit details.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        commit = repo.get_commit(commit_sha)

        return {
            "sha": commit.sha,
            "message": commit.commit.message,  # Full commit message
            "author_name": commit.commit.author.name if commit.commit.author else None,
            "author_email": commit.commit.author.email if commit.commit.author else None,
            "authored_date": commit.commit.author.date if commit.commit.author else None,
        }

    def get_workflow_run_jobs(self, config: dict[str, Any], repo_name: str, run_id: int) -> list[dict[str, Any]]:
        """
        Fetch jobs for a workflow run from GitHub API.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            run_id: The workflow run ID.

        Returns:
            List of job dictionaries with id, name, status, conclusion, steps.
        """
        g = self._get_github_client(config)
        repo = g.get_repo(repo_name)
        run = repo.get_workflow_run(run_id)
        jobs = run.jobs()

        result = []
        for job in jobs:
            steps = []
            for step in job.steps:
                steps.append(
                    {
                        "name": step.name,
                        "status": step.status,
                        "conclusion": step.conclusion,
                        "number": step.number,
                    }
                )
            result.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "status": job.status,
                    "conclusion": job.conclusion,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "steps": steps,
                }
            )
        return result

    def get_job_logs(self, config: dict[str, Any], repo_name: str, job_id: int) -> str | None:
        """
        Fetch job logs from GitHub Actions.

        PyGithub doesn't expose the logs endpoint directly, so we make a raw API request.

        Args:
            config: The decrypted configuration dictionary.
            repo_name: Full repository name (owner/repo).
            job_id: The job ID.

        Returns:
            Plain text log content, or None if unavailable.
        """
        import requests

        g = self._get_github_client(config)
        # Get token from the client's auth
        token = g._Github__requester._Requester__auth.token
        base_url = config.get("base_url", "https://api.github.com")
        url = f"{base_url}/repos/{repo_name}/actions/jobs/{job_id}/logs"
        headers = {**GH_API_HEADERS, "Authorization": f"Bearer {token}"}
        try:
            resp = requests.get(url, headers=headers, allow_redirects=True, timeout=30)
            if resp.status_code == 200:
                return resp.text
            # 410 Gone means logs expired
            return None
        except Exception:
            return None
