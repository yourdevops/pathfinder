import secrets
from pathlib import Path

from django.conf import settings


def get_secrets_dir():
    """Return path to secrets directory."""
    return Path(settings.BASE_DIR) / "secrets"


def get_unlock_token_path():
    """Return path to unlock token file."""
    return get_secrets_dir() / "initialUnlockToken"


def is_setup_complete():
    """Check if initial setup has been completed.

    Setup is complete when:
    - Token doesn't exist AND at least one admin user exists

    Setup is incomplete when:
    - Token exists (in progress)
    - Token doesn't exist AND no admin users (fresh install)
    """
    token_path = get_unlock_token_path()

    if token_path.exists():
        # Token exists means setup is in progress
        return False

    # Token doesn't exist - check if any admin users exist
    # Import here to avoid circular imports
    from core.models import Group, GroupMembership

    admins_group = Group.objects.filter(name="admins", status="active").first()
    if admins_group:
        return GroupMembership.objects.filter(group=admins_group).exists()

    # No token and no admin group = fresh install
    return False


def generate_unlock_token():
    """Generate a secure unlock token on fresh install.

    Creates secrets directory if needed, generates cryptographically
    secure token, and writes to file.

    Returns the token string.
    """
    token_path = get_unlock_token_path()
    if not token_path.exists():
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token = secrets.token_urlsafe(32)
        token_path.write_text(token)
        # Set restrictive permissions (owner read only)
        token_path.chmod(0o400)
    return token_path.read_text().strip()


def verify_unlock_token(provided_token):
    """Verify the provided token matches the stored one.

    Uses constant-time comparison to prevent timing attacks.
    """
    token_path = get_unlock_token_path()
    if not token_path.exists():
        return False
    stored_token = token_path.read_text().strip()
    provided_token = provided_token.strip() if provided_token else ""
    return secrets.compare_digest(stored_token, provided_token)


def complete_setup():
    """Delete the unlock token after successful setup."""
    token_path = get_unlock_token_path()
    if token_path.exists():
        token_path.unlink()


def resolve_env_vars(project, service=None, environment=None):
    """Resolve environment variables using cascade logic.

    Layers variables top-down: system -> project -> service -> environment.
    Locked variables cannot be overridden by downstream levels.
    Description is inherited from upstream unless downstream provides its own.

    Returns sorted list of dicts:
        {key, value, lock, description, source, locked_by}
    """
    merged = {}

    # 1. System-injected variables (always locked)
    merged["PTF_PROJECT"] = {
        "key": "PTF_PROJECT",
        "value": project.name,
        "lock": True,
        "description": "Project name (system-injected)",
        "source": "system",
        "locked_by": "system",
    }

    if service:
        merged["PTF_SERVICE"] = {
            "key": "PTF_SERVICE",
            "value": service.name,
            "lock": True,
            "description": "Service name (system-injected)",
            "source": "system",
            "locked_by": "system",
        }

    if environment:
        merged["PTF_ENVIRONMENT"] = {
            "key": "PTF_ENVIRONMENT",
            "value": environment.name,
            "lock": True,
            "description": "Environment name (system-injected)",
            "source": "system",
            "locked_by": "system",
        }

    # 2. Project variables
    for var in project.env_vars or []:
        key = var["key"]
        if key in merged:
            continue  # System vars cannot be overridden
        value = var.get("value", "")
        lock = var.get("lock", False)
        # Empty value cannot be locked
        if not value:
            lock = False
        merged[key] = {
            "key": key,
            "value": value,
            "lock": lock,
            "description": var.get("description", ""),
            "source": "project",
            "locked_by": "project" if lock else None,
        }

    # 3. Service variables (if provided)
    if service:
        for var in service.env_vars or []:
            key = var["key"]
            if key in merged and merged[key]["lock"]:
                continue  # Cannot override locked upstream
            value = var.get("value", "")
            lock = var.get("lock", False)
            if not value:
                lock = False
            # Inherit description from upstream if downstream is empty
            upstream_desc = merged[key]["description"] if key in merged else ""
            desc = var.get("description", "") or upstream_desc
            merged[key] = {
                "key": key,
                "value": value,
                "lock": lock,
                "description": desc,
                "source": "service",
                "locked_by": "service" if lock else None,
            }

    # 4. Environment variables (if provided)
    if environment:
        for var in environment.env_vars or []:
            key = var["key"]
            if key in merged and merged[key]["lock"]:
                continue  # Cannot override locked upstream
            value = var.get("value", "")
            # Environment is terminal level, locked_by is None
            upstream_desc = merged[key]["description"] if key in merged else ""
            desc = var.get("description", "") or upstream_desc
            merged[key] = {
                "key": key,
                "value": value,
                "lock": False,  # Environment is terminal, no downstream to lock
                "description": desc,
                "source": "environment",
                "locked_by": None,
            }

    # Return sorted by key
    return sorted(merged.values(), key=lambda v: v["key"])


def check_deployment_gate(resolved_vars):
    """Check if all resolved variables have values (deployment readiness).

    Excludes system PTF_* variables from the check (they always have values).

    Returns:
        tuple: (is_ready: bool, empty_vars: list of vars with empty values)
    """
    empty_vars = [var for var in resolved_vars if var["source"] != "system" and not var["value"]]
    return (len(empty_vars) == 0, empty_vars)
