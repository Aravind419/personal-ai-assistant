import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_encryption_key() -> bytes:
    """
    Derives a 32-byte URL-safe base64-encoded key for Fernet
    from the application's SECRET_KEY.
    """
    raw_key = settings.SECRET_KEY.encode("utf-8")
    digest = hashlib.sha256(raw_key).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plain_text: str | None) -> str | None:
    """
    Encrypts a secret string using Fernet symmetric encryption.
    Returns the encrypted token as a string, or None if input is empty.
    """
    if not plain_text or not plain_text.strip():
        return None
    fernet = Fernet(_get_encryption_key())
    encrypted_bytes = fernet.encrypt(plain_text.strip().encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_secret(cipher_text: str | None) -> str | None:
    """
    Decrypts an encrypted token. Returns the plaintext secret,
    or None if input is empty or invalid.
    """
    if not cipher_text or not cipher_text.strip():
        return None
    try:
        fernet = Fernet(_get_encryption_key())
        decrypted_bytes = fernet.decrypt(cipher_text.strip().encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return None


def mask_secret(secret: str | None, prefix_len: int = 5, suffix_len: int = 4) -> str | None:
    """
    Returns a masked version of a secret suitable for safe UI display (e.g., 'sk-or-••••••••abcd').
    """
    if not secret:
        return None
    s = secret.strip()
    if len(s) <= (prefix_len + suffix_len):
        return "••••••••"
    return f"{s[:prefix_len]}••••••••{s[-suffix_len:]}"
