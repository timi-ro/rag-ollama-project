import logging
import os

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet
    key = os.getenv("FERNET_KEY", "").encode()
    if not key:
        return None
    from cryptography.fernet import Fernet
    _fernet = Fernet(key)
    return _fernet


def encrypt_field(value: str) -> str:
    """Encrypt a sensitive string. Falls back to plaintext if FERNET_KEY is not set."""
    f = _get_fernet()
    if f is None:
        logger.warning("FERNET_KEY not set — storing sensitive field in plaintext")
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    """Decrypt a field encrypted by encrypt_field. Handles legacy plaintext gracefully."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        # Legacy plaintext value stored before encryption was enabled
        return value