"""Git helper functions for SCM-agnostic operations.

Uses GitPython for repository operations, enabling support for any
Git-compatible SCM (GitHub, GitLab, Bitbucket, self-hosted).
"""
import logging
import os
import re
import shutil
import tempfile
from typing import Optional
from urllib.parse import urlparse, urlunparse

import git
import jinja2
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
    temp_dir = tempfile.mkdtemp(prefix='ssp_clone_')

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

    Looks for ssp-template.yaml first, then pathfinder-template.yaml.

    Args:
        repo_path: Path to cloned repository

    Returns:
        Parsed manifest dictionary

    Raises:
        FileNotFoundError: If no manifest file found
        yaml.YAMLError: If manifest is invalid YAML
    """
    import os

    manifest_names = ['ssp-template.yaml', 'pathfinder-template.yaml']

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


def get_template_variables(service) -> dict:
    """
    Get template variables for service template substitution.

    Args:
        service: Service model instance

    Returns:
        Dict of variables: service_name, project_name, service_handler
    """
    return {
        'service_name': service.name,
        'project_name': service.project.name,
        'service_handler': service.handler,
    }


def apply_template_to_directory(src_dir: str, dest_dir: str, variables: dict, exclude_files: list = None):
    """
    Copy template files and apply variable substitution.

    Args:
        src_dir: Source directory (cloned template)
        dest_dir: Destination directory (target repo)
        variables: Dict of template variables for substitution
        exclude_files: Files to skip (e.g., manifest files)
    """
    import os

    if exclude_files is None:
        exclude_files = ['ssp-template.yaml', 'pathfinder-template.yaml', '.git']

    # Copy all files except excluded
    for item in os.listdir(src_dir):
        if item in exclude_files:
            continue

        src_path = os.path.join(src_dir, item)
        dest_path = os.path.join(dest_dir, item)

        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dest_path)

    # Apply variable substitution to text files
    text_extensions = {'.yaml', '.yml', '.json', '.md', '.txt', '.py', '.js', '.ts',
                       '.html', '.css', '.sh', '.dockerfile', '.toml', '.ini', '.cfg',
                       '.env', '.env.example'}

    for root, dirs, files in os.walk(dest_dir):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')

        for filename in files:
            _, ext = os.path.splitext(filename.lower())
            if ext in text_extensions or filename.lower() in {'dockerfile', 'makefile', 'readme'}:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Use Jinja2 for substitution (handles {{ var }} syntax)
                    template = jinja2.Template(content, undefined=jinja2.StrictUndefined)
                    rendered = template.render(**variables)

                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(rendered)
                except (UnicodeDecodeError, jinja2.TemplateError) as e:
                    # Skip binary files or files with template errors
                    logger.warning(f"Skipping template substitution for {filepath}: {e}")


def scaffold_new_repository(
    service,
    connection,
    template_temp_dir: str,
    variables: dict
) -> dict:
    """
    Scaffold a new repository from a service template.

    1. Create empty repo via SCM plugin
    2. Clone the new repo
    3. Apply template with variable substitution (if template dir provided)
    4. Commit and push to main branch

    Args:
        service: Service model instance
        connection: IntegrationConnection for SCM
        template_temp_dir: Path to template directory (optional)
        variables: Template variables

    Returns:
        Dict with repo_url and status
    """
    plugin = connection.get_plugin()
    config = connection.get_config()

    # Determine repository name (project-service)
    repo_name = service.handler

    # Create repository via plugin
    logger.info(f"Creating repository: {repo_name}")
    create_result = plugin.create_repository(config, repo_name, private=True)
    repo_url = create_result.get('clone_url') or create_result.get('html_url')

    if not repo_url:
        raise ValueError("Failed to get repository URL from create_repository response")

    # Build authenticated URL for pushing
    auth_url = build_authenticated_git_url(repo_url, connection)

    # Create temp directory for the new repo
    repo_temp_dir = tempfile.mkdtemp(prefix='ssp_scaffold_')

    try:
        # Initialize git repo
        repo = git.Repo.init(repo_temp_dir)

        # Apply template if provided
        if template_temp_dir:
            apply_template_to_directory(template_temp_dir, repo_temp_dir, variables)

        # Git add all files
        repo.index.add('*')

        # Commit
        repo.index.commit(
            f"Initial commit for service {service.name}",
            author=git.Actor("Pathfinder", "pathfinder@localhost"),
            committer=git.Actor("Pathfinder", "pathfinder@localhost"),
        )

        # Add remote and push
        origin = repo.create_remote('origin', auth_url)

        # Rename branch to match target (usually 'main')
        if repo.active_branch.name != service.repo_branch:
            repo.active_branch.rename(service.repo_branch)

        origin.push(service.repo_branch)

        logger.info(f"Successfully scaffolded new repository: {repo_url}")

        return {
            'status': 'success',
            'repo_url': repo_url,
        }

    finally:
        # Cleanup
        shutil.rmtree(repo_temp_dir, ignore_errors=True)


def scaffold_existing_repository(
    service,
    connection,
    template_temp_dir: str,
    variables: dict
) -> dict:
    """
    Scaffold into existing repository with feature branch and PR.

    1. Clone existing repo
    2. Create feature/{service-name} branch
    3. Apply template with variable substitution (if template dir provided)
    4. Commit and push feature branch
    5. Create PR to base branch

    Args:
        service: Service model instance
        connection: IntegrationConnection for SCM
        template_temp_dir: Path to template directory (optional)
        variables: Template variables

    Returns:
        Dict with pr_url and status
    """
    plugin = connection.get_plugin()
    config = connection.get_config()

    # Build authenticated URL
    auth_url = build_authenticated_git_url(service.repo_url, connection)

    # Clone existing repo
    repo_temp_dir = tempfile.mkdtemp(prefix='ssp_scaffold_existing_')

    try:
        logger.info(f"Cloning existing repository: {service.repo_url}")
        repo = git.Repo.clone_from(auth_url, repo_temp_dir, branch=service.repo_branch)

        # Create feature branch
        feature_branch = f"feature/{service.name}"
        repo.create_head(feature_branch)
        repo.heads[feature_branch].checkout()

        # Apply template if provided
        if template_temp_dir:
            apply_template_to_directory(template_temp_dir, repo_temp_dir, variables)

        # Check if there are changes
        if not repo.is_dirty() and not repo.untracked_files:
            logger.warning("No changes to commit after applying template")
            return {
                'status': 'success',
                'message': 'No changes - template already applied',
            }

        # Git add and commit
        repo.index.add('*')
        repo.index.commit(
            f"Add service scaffold for {service.name}",
            author=git.Actor("Pathfinder", "pathfinder@localhost"),
            committer=git.Actor("Pathfinder", "pathfinder@localhost"),
        )

        # Push feature branch
        origin = repo.remote('origin')
        origin.push(feature_branch)

        # Create PR via plugin
        logger.info(f"Creating pull request for {feature_branch}")
        pr_result = plugin.create_pull_request(
            config,
            service.repo_url,
            title=f"Add {service.name} service scaffold",
            body=f"Scaffolded service: {service.name}",
            head=feature_branch,
            base=service.repo_branch,
        )

        pr_url = pr_result.get('html_url', '')

        logger.info(f"Successfully created PR: {pr_url}")

        return {
            'status': 'success',
            'pr_url': pr_url,
        }

    finally:
        # Cleanup
        shutil.rmtree(repo_temp_dir, ignore_errors=True)


def parse_runtimes_yml(repo_path: str) -> dict:
    """
    Parse runtimes.yml from a steps repository.

    Supports both formats:
      - {family: {versions: [...]}}
      - {family: [...]}

    Returns:
        Dict mapping family name to list of version strings.
        e.g., {"python": ["3.11", "3.12", "3.13"], "node": ["18", "20", "22"]}
    """
    runtimes_path = os.path.join(repo_path, 'runtimes.yml')
    if not os.path.exists(runtimes_path):
        return {}

    with open(runtimes_path, 'r') as f:
        data = yaml.safe_load(f) or {}

    result = {}
    for family, config in data.items():
        if isinstance(config, dict) and 'versions' in config:
            # Format: {family: {versions: [...]}}
            result[family] = [str(v) for v in config['versions']]
        elif isinstance(config, list):
            # Format: {family: [...]}
            result[family] = [str(v) for v in config]

    return result


def scan_ci_steps(repo_path: str) -> list:
    """
    Scan ci-steps/ directory for step definitions.

    Walks ci-steps/ looking for subdirectories containing action.yml
    (or action.yaml as fallback). Parses each file and extracts
    standard GitHub Actions fields plus x-pathfinder metadata.

    Returns:
        Sorted list of dicts with step metadata from action.yml files.
    """
    steps_dir = os.path.join(repo_path, 'ci-steps')
    if not os.path.isdir(steps_dir):
        return []

    steps = []
    for entry in sorted(os.listdir(steps_dir)):
        step_dir = os.path.join(steps_dir, entry)
        if not os.path.isdir(step_dir):
            continue

        # Look for action.yml, fallback to action.yaml
        action_file = os.path.join(step_dir, 'action.yml')
        if not os.path.exists(action_file):
            action_file = os.path.join(step_dir, 'action.yaml')
            if not os.path.exists(action_file):
                logger.warning(f"No action.yml found in ci-steps/{entry}, skipping")
                continue

        try:
            with open(action_file, 'r') as f:
                metadata = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse action.yml in ci-steps/{entry}: {e}")
            continue

        pathfinder = metadata.get('x-pathfinder', {})

        steps.append({
            'directory_name': entry,
            'name': metadata.get('name', entry),
            'description': metadata.get('description', ''),
            'inputs': metadata.get('inputs', {}),
            'phase': pathfinder.get('phase', ''),
            'runtime_constraints': pathfinder.get('runtimes', {}),
            'tags': pathfinder.get('tags', []),
            'produces': pathfinder.get('produces'),
            'raw_metadata': metadata,
        })

    return steps
