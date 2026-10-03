"""Security helpers for passwords and API tokens."""

import base64
import binascii
import hashlib
import hmac
import secrets


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
API_KEY_BYTES = 32


def hash_password(password, *, salt=None, iterations=PBKDF2_ITERATIONS):
    """Hash a password using PBKDF2-HMAC-SHA256 and a per-password salt."""
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")

    salt_bytes = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations,
    )
    salt_b64 = base64.urlsafe_b64encode(salt_bytes).decode("ascii")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{PASSWORD_HASH_ALGORITHM}${iterations}${salt_b64}${digest_b64}"


def verify_password(password, stored_hash):
    """Return True when ``password`` matches ``stored_hash``."""
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False

    try:
        algorithm, iterations_raw, salt_b64, expected_b64 = stored_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_b64.encode("ascii"))
    except (binascii.Error, ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


def generate_api_key():
    """Create an unpredictable user API key."""
    return secrets.token_urlsafe(API_KEY_BYTES)


def generate_reset_token():
    """Create an unpredictable password reset token."""
    return secrets.token_urlsafe(API_KEY_BYTES)
