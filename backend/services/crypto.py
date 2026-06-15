"""Encrypt/decrypt provider credentials using Fernet symmetric encryption."""
import base64
import hashlib
from cryptography.fernet import Fernet
from backend.config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from SECRET_KEY."""
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a password."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
