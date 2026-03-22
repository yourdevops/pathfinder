"""
Encryption utilities for sensitive configuration data.

This module provides Fernet-based encryption for storing sensitive
configuration fields like API keys, tokens, and passwords.

The encryption key is sourced from (in order of priority):
1. PTF_ENCRYPTION_KEY environment variable
2. secrets/encryption.key file (auto-generated if missing)

For production deployments, use the PTF_ENCRYPTION_KEY environment variable.
"""

import json
import logging
import os
import threading
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Cache the Fernet instance
_fernet_instance = None
_fernet_lock = threading.Lock()


def get_encryption_key() -> bytes:
    """
    Get the encryption key from environment or file.

    Priority:
    1. PTF_ENCRYPTION_KEY environment variable
    2. secrets/encryption.key file

    If no key exists, generates a new one and saves to file.

    Returns:
        The encryption key as bytes.
    """
    # Check environment variable first
    env_key = os.environ.get("PTF_ENCRYPTION_KEY")
    if env_key:
        logger.debug("Using encryption key from PTF_ENCRYPTION_KEY environment variable")
        return env_key.encode("utf-8")

    # Check secrets file
    secrets_dir = Path(__file__).resolve().parent.parent / "secrets"
    key_file = secrets_dir / "encryption.key"

    if key_file.exists():
        logger.debug("Using encryption key from %s", key_file)
        return key_file.read_bytes().strip()

    # Generate new key
    logger.info("Generating new encryption key")
    new_key = Fernet.generate_key()

    # Ensure secrets directory exists
    secrets_dir.mkdir(exist_ok=True)

    # Write key with restrictive permissions
    key_file.write_bytes(new_key)
    key_file.chmod(0o600)

    logger.info("New encryption key saved to %s", key_file)
    return new_key


def get_fernet() -> Fernet:
    """
    Get a Fernet instance for encryption/decryption.

    Uses cached instance for performance.

    Returns:
        Fernet instance initialized with the encryption key.
    """
    global _fernet_instance
    if _fernet_instance is None:
        with _fernet_lock:
            if _fernet_instance is None:
                _fernet_instance = Fernet(get_encryption_key())
    return _fernet_instance


def encrypt_config(config: dict) -> bytes:
    """
    Encrypt a configuration dictionary.

    Args:
        config: Dictionary of configuration key-value pairs.

    Returns:
        Encrypted bytes that can be stored in BinaryField.
    """
    fernet = get_fernet()
    json_bytes = json.dumps(config).encode("utf-8")
    return fernet.encrypt(json_bytes)


def decrypt_config(encrypted: bytes) -> dict:
    """
    Decrypt an encrypted configuration.

    Args:
        encrypted: Encrypted bytes from encrypt_config().

    Returns:
        The original configuration dictionary.

    Raises:
        cryptography.fernet.InvalidToken: If decryption fails
            (wrong key or corrupted data).
    """
    fernet = get_fernet()
    decrypted_bytes = fernet.decrypt(encrypted)
    return json.loads(decrypted_bytes.decode("utf-8"))
