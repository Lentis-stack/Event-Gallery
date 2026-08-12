# ============================================================
# Lentis Gallery — Security Helpers
# ------------------------------------------------------------
# This module centralizes ALL security-critical primitives:
#   - Password hashing / verification (Argon2id)
#   - Access token creation / decoding (JWT via PyJWT)
#   - Refresh token generation / hashing
#
# WHY CENTRALIZE?
#   - One place to audit security.
#   - Easy to keep consistent.
#   - Prevents accidental use of weak hashing elsewhere.
#
# PASSWORD HASHING — WHY ARGON2id?
#   Hashes are one-way: given a hash, you cannot recover the
#   password. Argon2id is the current recommended algorithm — it
#   is deliberately SLOW and memory-hard, which makes brute-force
#   attacks expensive. It also includes a random "salt" per user,
#   so identical passwords produce different hashes.
#
# ACCESS TOKENS — WHAT IS A JWT?
#   A JWT (JSON Web Token) is a signed, self-contained token:
#     header.payload.signature
#   The payload contains claims (e.g. user id, role, expiry).
#   The signature proves the token was created by us (signed with
#   JWT_SECRET_KEY) and hasn't been tampered with. We validate the
#   signature and expiry when decoding.
#
# REFRESH TOKENS — WHY STORE A HASH?
#   We never store the raw refresh token in the DB. If the DB leak,
#   raw tokens are useless because we only stored their SHA-256
#   hash. When a client presents a refresh token, we hash it and
#   look up the matching row. This means a stolen DB does NOT give
#   an attacker working refresh tokens.
# ============================================================

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

# A single password hasher instance (safe to reuse).
_password_hasher = PasswordHasher()

# Seconds allowed for clock skew between servers (small tolerance).
LEEWAY_SECONDS = 10


# ============================================================
# Password hashing
# ============================================================

def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id and return the hash."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.
    Argon2's verify() runs in constant time, reducing timing attacks.
    Returns False (never raises) on any mismatch or malformed hash.
    """
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        # Same result for "wrong password" and "corrupt hash" so an
        # attacker cannot distinguish them.
        return False


def validate_password_strength(password: str) -> str | None:
    """
    Lightweight password policy check. Returns an error message if
    the password is too weak, otherwise None.
    We keep rules simple and clear (length + not-trivial).
    """
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password.lower() in ("password", "password123", "lentis", "lentis123"):
        return "That password is too common. Choose a stronger one."
    return None


# ============================================================
# Access tokens (JWT)
# ============================================================

def create_access_token(user_id: str, role: str) -> str:
    """
    Create a short-lived JWT access token for a user.
    Contains ONLY what authorization needs: sub (user id), role,
    token type, issued-at, expiry, and a unique id (jti).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": user_id,                          # subject = user id
        "role": role,                            # for authorization
        "type": "access",                        # token kind
        "iat": now,                              # issued at
        "exp": expire,                           # expires at
        "jti": secrets.token_urlsafe(16),        # unique token id
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and VALIDATE an access token.
    Raises jwt.PyJWTError if the token is invalid, expired, or
    tampered with. Callers translate this into a 401 response.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        leeway=LEEWAY_SECONDS,
    )


# ============================================================
# Refresh tokens
# ============================================================

def generate_refresh_token() -> str:
    """
    Generate a cryptographically random refresh token.
    We return the RAW token to the client (to store in a cookie),
    and store only its hash in the database.
    """
    return secrets.token_urlsafe(48)  # ~64 chars of high entropy


def hash_refresh_token(token: str) -> str:
    """Return a SHA-256 hash of a refresh token for DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ============================================================
# Guest session tokens (Phase 4)
# ============================================================
# Guest sessions use the SAME opaque-token pattern as refresh
# tokens: a cryptographically random raw token returned once to
# the client, with only its SHA-256 hash stored in the database.
#
# WHY OPAQUE RANDOM TOKENS (not JWTs) FOR GUESTS?
#   * A JWT carries claims we can forge/sign, but it also reveals
#     info and needs secret verification. An opaque random token
#     holds NO information at all — it is literally random bytes.
#     Its ONLY purpose is to be hashed, looked up, and matched.
#   * This is simplest and safest: no signing key involved, and a
#     DB leak exposes only meaningless hashes.
# ============================================================

def generate_guest_token() -> str:
    """
    Generate a cryptographically random guest session token.
    secrets.token_urlsafe(48) => ~64 chars of high entropy; it is
    impossible to guess (128 bits+).
    """
    return generate_refresh_token()


def hash_guest_token(token: str) -> str:
    """Return a SHA-256 hash of a guest session token for DB storage."""
    return hash_refresh_token(token)
