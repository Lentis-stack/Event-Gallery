# ============================================================
# Lentis Gallery — Authentication API Routes
# ------------------------------------------------------------
# Exposes the authentication endpoints the frontend (and any
# client) uses to log in, refresh, log out, and learn who they are.
#
# COOKIE vs LOCAL STORAGE DECISION:
#   We return the ACCESS token in the response body (the frontend
#   attaches it to API requests). The REFRESH token is placed in an
#   HttpOnly cookie. Why?
#     - HttpOnly cookies are NOT readable by JavaScript, so even if
#       an XSS attack runs JS, it cannot steal the refresh token.
#     - The refresh token is the long-lived credential, so it is the
#       most important one to protect.
#     - SameSite=Lax + Secure prevents it being sent on cross-site
#       requests (CSRF protection) and over plain HTTP in production.
#   The ACCESS token being in memory (JS) is acceptable because it is
#   short-lived (30 min). If stolen, the damage window is small.
#
# SECURITY NOTE on CORS:
#   Because we use cookies, the frontend must send credentials and
#   the allowed origin must be EXACT (never "*"). This is configured
#   via FRONTEND_URL in .env.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    UserCreate,
    UserCreated,
    UserOut,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Cookie name + attributes for the refresh token.
REFRESH_COOKIE = "lentis_refresh"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Set the refresh token as an HttpOnly, SameSite cookie."""
    # In production (HTTPS), Secure=True. In dev (http) we allow it off.
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,          # JS cannot read it
        samesite="lax",         # CSRF protection
        secure=settings.ENVIRONMENT == "production",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Expire the refresh cookie (logout)."""
    response.delete_cookie(REFRESH_COOKIE, path="/")


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    """Extract client IP + User-Agent for audit (never logged raw by us)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


# ============================================================
# POST /api/auth/login
# ============================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in with email + password",
    description="Authenticates a user and issues an access token (in the body) "
    "and a refresh token (in an HttpOnly cookie).",
)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip, ua = _client_meta(request)
    result = auth_service.authenticate_user(
        db, body.email, body.password, ip, ua
    )

    # Place the refresh token in an HttpOnly cookie.
    _set_refresh_cookie(response, result["refresh_token"])

    # Build the safe user object. The service returns user_id/email/
    # role; we look up created_at from the DB for the response.
    user_obj = db.get(User, result["user_id"])

    return {
        "user": {
            "id": result["user_id"],
            "email": result["email"],
            "role": result["role"],
            "is_active": True,
            "created_at": user_obj.created_at if user_obj else None,
        },
        "access_token": {
            "access_token": result["access_token"],
            "token_type": "bearer",
            "expires_in": result["expires_in"],
        },
    }


# ============================================================
# POST /api/auth/refresh
# ============================================================

@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh the access token",
    description="Uses the refresh token from the HttpOnly cookie to issue a new "
    "access token. The refresh token is rotated (old one revoked).",
)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided."
        )
    ip, ua = _client_meta(request)
    result = auth_service.refresh_access(db, raw_token, ip, ua)

    # Rotate the cookie to the new refresh token.
    _set_refresh_cookie(response, result["refresh_token"])

    return {
        "access_token": {
            "access_token": result["access_token"],
            "token_type": "bearer",
            "expires_in": result["expires_in"],
        }
    }


# ============================================================
# POST /api/auth/logout
# ============================================================

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    description="Revokes the refresh token and clears the cookie.",
)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if raw_token:
        auth_service.logout_refresh_token(db, raw_token)
    _clear_refresh_cookie(response)
    # The endpoint returns a raw Response, so we must explicitly set
    # the 204 status (FastAPI uses the Response's own status here).
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# ============================================================
# GET /api/auth/me
# ============================================================

@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
    description="Returns the authenticated user's info. Requires a valid access token.",
)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


# ============================================================
# POST /api/auth/users  (ADMIN ONLY)
# ============================================================
# Controlled creation of HOST/ADMIN users. Not public registration.

@router.post(
    "/users",
    response_model=UserCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (admin only)",
    description="Creates a new HOST or ADMIN account. Requires an ADMIN access token.",
)
def create_user_endpoint(
    body: UserCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = auth_service.create_user(db, body.email, body.password, body.role)
    return {
        "user": UserOut.model_validate(user),
        "message": "User created.",
    }
