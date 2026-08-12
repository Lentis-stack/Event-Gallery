# ============================================================
# Lentis Gallery — Auth Service
# ------------------------------------------------------------
# Business logic for authentication. Endpoints call these functions;
# they do NOT contain the raw SQL or token logic directly.
#
# RESPONSIBILITIES:
#   - Find a user by normalized email.
#   - Verify passwords (Argon2id).
#   - Issue access + refresh tokens.
#   - Rotate/revoke refresh tokens.
#   - Create users (admin-only, controlled).
#   - Log auth events safely (never credentials).
# ============================================================

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import is_locked_out, record_failure, reset_failures
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    validate_password_strength,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _normalize_email(email: str) -> str:
    """Lowercase + strip whitespace so logins are case-insensitive."""
    return email.strip().lower()


def _build_access_payload(user: User) -> dict:
    """Return the safe fields + access token for a user."""
    # expires_in in seconds, for the frontend to know when to refresh.
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value,
        "access_token": create_access_token(user.id, user.role.value),
        "expires_in": expires_in,
    }


def _issue_refresh_token(db: Session, user: User, ip: str | None, user_agent: str | None) -> str:
    """
    Create a new refresh-token session row. Stores the HASH in the
    DB, returns the RAW token to the client (to place in a cookie).
    """
    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session_row = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=user_agent,
    )
    db.add(session_row)
    db.commit()  # persist so the token is valid immediately
    return raw_token


def _revoke_refresh_token(db: Session, token_hash: str) -> None:
    """Revoke a specific refresh token (by its hash)."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is not None and not row.revoked:
        row.revoked = True
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()


def _validate_refresh_token(db: Session, raw_token: str) -> RefreshToken:
    """
    Validate a raw refresh token: hash it, find the row, and ensure
    it is not revoked or expired. Returns the row on success.
    """
    token_hash = hash_refresh_token(raw_token)
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    if row.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked.")
    if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")
    return row


# ============================================================
# Core operations
# ============================================================

def authenticate_user(db: Session, email: str, password: str, ip: str | None, user_agent: str | None) -> dict:
    """
    Login: verify credentials, issue tokens. Returns login payload.
    Throws 401 for invalid credentials, 429 if locked out.
    """
    # 1. Rate limit check (before hitting the DB).
    if is_locked_out(ip):
        logger.warning("Login blocked for locked-out client ip=%s", ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )

    # 2. Find user by normalized email.
    normalized = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized))

    # 3. Verify. Use a SINGLE generic message for both "no user" and
    #    "wrong password" to prevent account enumeration.
    valid = user is not None and verify_password(password, user.password_hash)
    if not valid or (user is not None and not user.is_active):
        record_failure(ip)
        logger.info("Login failed email=%s ip=%s", normalized, ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Success — reset failures, update last_login_at.
    reset_failures(ip)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # 5. Issue tokens.
    raw_refresh = _issue_refresh_token(db, user, ip, user_agent)
    payload = _build_access_payload(user)
    payload["refresh_token"] = raw_refresh

    logger.info("Login success user_id=%s role=%s", user.id, user.role.value)
    return payload


def refresh_access(db: Session, raw_token: str, ip: str | None, user_agent: str | None) -> dict:
    """
    Refresh: validate the refresh token, rotate it (revoke old,
    issue new), and return a new access token + new refresh token.
    """
    row = _validate_refresh_token(db, raw_token)
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable.")

    # Rotation: revoke old session, create a fresh one.
    _revoke_refresh_token(db, hash_refresh_token(raw_token))
    raw_refresh = _issue_refresh_token(db, user, ip, user_agent)

    payload = _build_access_payload(user)
    payload["refresh_token"] = raw_refresh
    logger.info("Refresh success user_id=%s", user.id)
    return payload


def logout_refresh_token(db: Session, raw_token: str) -> None:
    """Logout: revoke the presented refresh token (if any)."""
    if raw_token:
        _revoke_refresh_token(db, hash_refresh_token(raw_token))
        logger.info("Logout: refresh token revoked.")


def create_user(db: Session, email: str, password: str, role: UserRole) -> User:
    """
    Create a new user (ADMIN or HOST). Password strength is checked
    here; the password is hashed with Argon2id before storing.
    """
    # Password policy.
    strength_error = validate_password_strength(password)
    if strength_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strength_error)

    normalized = _normalize_email(email)
    # Duplicate email check.
    existing = db.scalar(select(User).where(User.email == normalized))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User created user_id=%s role=%s", user.id, role.value)
    return user
