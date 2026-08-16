"""
auth_utils.py — Password hashing and verification using the Python standard library.

No third-party dependencies required.

Algorithm: PBKDF2-HMAC-SHA256 with 260,000 iterations (NIST SP 800-132 compliant for 2024).
Salt: 128-bit cryptographically random, generated via secrets.token_hex(16).
Comparison: hmac.compare_digest (constant-time, resistant to timing attacks).

Stored format:
    pbkdf2_sha256$<iterations>$<hex_salt>$<base64_derived_key>

Example:
    pbkdf2_sha256$260000$9f3a1b2c4d5e6f7a8b9c0d1e2f3a4b5c$<base64...>
"""

import base64
import hashlib
import hmac
import secrets

# Number of PBKDF2 iterations — NIST SP 800-132 recommendation for SHA-256 in 2024.
_ITERATIONS = 260_000
_ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """
    Hash a plaintext password and return a self-describing stored string.

    The returned string contains all information needed to verify the password
    later, including algorithm identifier, iteration count, salt, and derived key.
    It does NOT contain the original plaintext password.
    """
    salt = secrets.token_hex(16)          # 128-bit random salt, hex-encoded
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    )
    b64_dk = base64.b64encode(dk).decode("ascii")
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${b64_dk}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored hash string.

    Returns True if the password matches, False otherwise.
    Uses hmac.compare_digest for constant-time comparison (timing-attack resistant).
    Returns False (not raises) on malformed stored_hash to avoid leaking info.
    """
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False
        algorithm, iterations_str, salt, stored_b64 = parts
        if algorithm != _ALGORITHM:
            return False
        iterations = int(iterations_str)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        candidate_b64 = base64.b64encode(dk).decode("ascii")
        return hmac.compare_digest(candidate_b64, stored_b64)
    except Exception:
        return False


def hash_reset_token(raw_token: str) -> str:
    """
    Return the SHA-256 hex digest of a raw reset token.

    The raw token (from secrets.token_urlsafe(32)) has 256 bits of
    cryptographic entropy, so no salt is required — preimage resistance
    of SHA-256 is sufficient to protect the stored hash.

    Only the hash is persisted; the raw token is sent to the user (via
    console in dev mode, or email in production) and never stored.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
