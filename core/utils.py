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
