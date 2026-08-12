# ============================================================
# Lentis Gallery — FastAPI Dependencies
# ------------------------------------------------------------
# Reusable FastAPI dependencies for authentication + authorization.
#
# WHY HAVE THESE?
#   - Instead of copy/pasting token validation into every route,
#     we define it once here.
#   - Any route that needs a logged-in user declares
#     `user = Depends(get_current_user)`.
#   - Any route that needs an admin declares
#     `user = Depends(require_admin)`.
#   - The backend INDEPENDENTLY enforces roles. Hiding a button in
#     the frontend is NOT security — the API itself rejects
#     unauthorized users.
# ============================================================

import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# HTTPBearer extracts the "Authorization: Bearer <token>" header.
# auto_error=False lets us return our own error message.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate the request by validating the access token and
    loading the user. Used by any protected route.
    """
    # Must present an Authorization: Bearer <token> header.
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Validate the token signature + expiry.
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # It must be an access token (not a refresh token).
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    # Load the user from the DB.
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Inactive users are blocked even if they have a valid token.
    if not user.is_active:
        logger.warning("Blocked inactive user %s", user.email)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Authorization dependency: require the ADMIN role.
    Rejects HOST users even if they are authenticated.
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


def require_host(user: User = Depends(get_current_user)) -> User:
    """
    Authorization dependency: require the HOST role.
    (A host may also be an admin; admins are allowed through.)
    """
    if user.role not in (UserRole.HOST, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Host access required.",
        )
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    OPTIONAL authentication dependency (Phase 6). Returns the
    authenticated user if a valid Bearer token is supplied, otherwise
    None. Used by the media processing-status endpoint so it can accept
    EITHER a host/admin Bearer token OR a guest X-Guest-Token header.
    """
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        # Invalid/expired token -> treat as "no user" (the caller will
        # fall through to guest-token auth or fail with 401/404).
        return None
