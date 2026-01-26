"""Git helper functions for SCM-agnostic operations.

Uses GitPython for repository operations, enabling support for any
Git-compatible SCM (GitHub, GitLab, Bitbucket, self-hosted).
"""
import logging
import re
import shutil
import tempfile
from typing import Optional
from urllib.parse import urlparse, urlunparse

import git
import semver
import yaml

logger = logging.getLogger(__name__)


def parse_git_url(url: str) -> Optional[dict]:
    """
    Parse any Git URL to extract host, owner, repo.

    Supports formats:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://gitlab.com/owner/repo
      - git@github.com:owner/repo.git
      - git@gitlab.com:owner/repo.git

    Returns dict with: host, owner, repo, or None if invalid.
    """
    if not url:
        return None

    # Handle SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r'^git@([^:]+):(.+)/(.+?)(?:\.git)?$', url)
    if ssh_match:
        host, owner, repo = ssh_match.groups()
        return {'host': host, 'owner': owner, 'repo': repo}

    # Handle HTTPS format
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return None

        if not parsed.netloc or not parsed.path:
            return None

        # Parse path: /owner/repo or /owner/repo.git
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            return None

        owner = path_parts[0]
        repo = path_parts[1]

        # Remove .git suffix if present
        if repo.endswith('.git'):
            repo = repo[:-4]

        return {
            'host': parsed.netloc,
            'owner': owner,
            'repo': repo
        }
    except Exception:
        return None


def build_authenticated_git_url(git_url: str, connection=None) -> str:
    """
    Build authenticated Git URL with embedded credentials.

    Args:
        git_url: Original repository URL
        connection: Optional IntegrationConnection with credentials

    Returns:
        URL with embedded credentials, or original URL if no connection
    """
    if connection is None:
        return git_url

    parsed_url = parse_git_url(git_url)
    if not parsed_url:
        return git_url

    host = parsed_url['host']
    owner = parsed_url['owner']
    repo = parsed_url['repo']

    config = connection.get_config()
    auth_type = config.get('auth_type', 'token')

    token = None

    if auth_type == 'token':
        # Personal Access Token
        token = config.get('personal_token')
    elif auth_type == 'app':
        # GitHub App - need to get installation token
        plugin = connection.get_plugin()
        if plugin:
            try:
                # Get GitHub client which handles installation token
                github_client = plugin._get_github_client_app(config)
                # The installation token is in the requester
                token = github_client.requester._Requester__authorizationHeader.split(' ')[-1]
            except Exception as e:
                logger.warning(f"Failed to get GitHub App installation token: {e}")
                # Fall back to public access
                return git_url
    else:
        # Unknown auth type, try to use any token-like field
        for key in ('personal_token', 'token', 'access_token'):
            if config.get(key):
                token = config.get(key)
                break

    if not token:
        return git_url

    # Build authenticated URL
    # Format: https://{token}@{host}/{owner}/{repo}.git
    # For GitHub App: https://x-access-token:{token}@{host}/{owner}/{repo}.git
    if auth_type == 'app':
        auth_url = f"https://x-access-token:{token}@{host}/{owner}/{repo}.git"
    else:
        auth_url = f"https://{token}@{host}/{owner}/{repo}.git"

    return auth_url


def clone_repo_shallow(git_url: str, branch: str = 'main', auth_url: str = None, depth: int = 1):
    """
    Clone a repository with shallow depth.

    Args:
        git_url: Repository URL (for logging)
        branch: Branch to clone
        auth_url: Optional authenticated URL to use instead of git_url
        depth: Clone depth (default 1 for shallow)

    Returns:
        Tuple of (git.Repo object, temp_dir path)

    Raises:
        git.GitCommandError: If clone fails
    """
    temp_dir = tempfile.mkdtemp(prefix='ssp_blueprint_')

    try:
        url_to_clone = auth_url or git_url
        logger.info(f"Cloning repository (branch={branch}, depth={depth})")

        repo = git.Repo.clone_from(
            url_to_clone,
            temp_dir,
            depth=depth,
            branch=branch,
            single_branch=True
        )

        return repo, temp_dir

    except Exception as e:
        # Clean up on failure
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def read_manifest_from_repo(repo_path: str) -> dict:
    """
    Read and parse manifest file from repository.

    Looks for ssp-template.yaml first, then devssp-template.yaml.

    Args:
        repo_path: Path to cloned repository

    Returns:
        Parsed manifest dictionary

    Raises:
        FileNotFoundError: If no manifest file found
        yaml.YAMLError: If manifest is invalid YAML
    """
    import os

    manifest_names = ['ssp-template.yaml', 'devssp-template.yaml']

    for name in manifest_names:
        manifest_path = os.path.join(repo_path, name)
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(
        f"Manifest file not found. Expected one of: {', '.join(manifest_names)}"
    )


def list_tags_from_repo(repo: git.Repo) -> list:
    """
    List all tags from repository.

    Args:
        repo: GitPython Repo object

    Returns:
        List of dicts: [{'name': tag_name, 'commit_sha': sha}, ...]
    """
    tags = []

    for tag in repo.tags:
        try:
            # Handle both lightweight and annotated tags
            commit = tag.commit
            tags.append({
                'name': tag.name,
                'commit_sha': commit.hexsha
            })
        except Exception as e:
            logger.warning(f"Failed to get commit for tag {tag.name}: {e}")

    # Sort by tag name
    tags.sort(key=lambda t: t['name'])

    return tags


def cleanup_repo(repo: git.Repo, temp_dir: str):
    """
    Clean up cloned repository.

    Args:
        repo: GitPython Repo object
        temp_dir: Path to temporary directory
    """
    try:
        repo.close()
    except Exception as e:
        logger.warning(f"Failed to close repo: {e}")

    shutil.rmtree(temp_dir, ignore_errors=True)


def compute_version_sort_key(major: int, minor: int, patch: int, prerelease: str) -> str:
    """
    Compute sortable string key for version ordering.

    Format: {major:05d}.{minor:05d}.{patch:05d}.{prerelease or 'zzzz'}

    This ensures:
    - 1.0.0 > 1.0.0-rc.1 > 1.0.0-beta.1
    - Pre-release versions sort before release (because 'beta' < 'zzzz')

    Args:
        major: Major version number
        minor: Minor version number
        patch: Patch version number
        prerelease: Pre-release identifier or empty string

    Returns:
        Sortable version string
    """
    # Use 'zzzz' for releases so they sort after pre-releases
    pre = prerelease if prerelease else 'zzzz'
    return f'{major:05d}.{minor:05d}.{patch:05d}.{pre}'


def parse_version_tag(tag_name: str) -> dict:
    """
    Parse a version tag into components.

    Supports:
    - v1.2.3, V1.2.3, 1.2.3
    - 1.0.0-alpha, 1.0.0-beta.1, 1.0.0-rc.1

    Args:
        tag_name: Git tag name (e.g., 'v1.2.3')

    Returns:
        Dict with: major, minor, patch, prerelease, is_prerelease, sort_key
    """
    # Strip leading 'v' or 'V'
    version_str = tag_name
    if version_str.lower().startswith('v'):
        version_str = version_str[1:]

    try:
        version = semver.Version.parse(version_str)

        prerelease = version.prerelease or ''
        is_prerelease = bool(version.prerelease)

        return {
            'major': version.major,
            'minor': version.minor,
            'patch': version.patch,
            'prerelease': prerelease,
            'is_prerelease': is_prerelease,
            'sort_key': compute_version_sort_key(
                version.major, version.minor, version.patch, prerelease
            )
        }
    except ValueError:
        # Non-semver tag - treat as pre-release with version 0.0.0
        return {
            'major': 0,
            'minor': 0,
            'patch': 0,
            'prerelease': tag_name,
            'is_prerelease': True,
            'sort_key': compute_version_sort_key(0, 0, 0, tag_name)
        }
