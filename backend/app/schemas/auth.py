# ============================================================
# Lentis Gallery — Auth Schemas
# ------------------------------------------------------------
# Pydantic schemas for the authentication API.
# These define exactly what the API accepts and returns, and are
# NEVER the raw SQLAlchemy models. This prevents leaking internal
# fields (password_hash) to the client.
# ============================================================

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


# ------------------------------------------------------------
# Login
# ------------------------------------------------------------

class LoginRequest(BaseModel):
    """Body for POST /api/auth/login."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, max_length=128, description="Password")


# ------------------------------------------------------------
# Tokens
# ------------------------------------------------------------

class AccessTokenResponse(BaseModel):
    """An access token + metadata returned to the client."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiry


class RefreshRequest(BaseModel):
    """Body for POST /api/auth/refresh (refresh token from cookie)."""
    # The refresh token is read from an HttpOnly cookie, so this
    # body may be empty. We keep a placeholder body model for
    # consistency; the cookie carries the actual token.
    pass


# ------------------------------------------------------------
# User
# ------------------------------------------------------------

class UserOut(BaseModel):
    """Safe user representation — NEVER includes password_hash."""
    id: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Response for login: safe user + access token."""
    user: UserOut
    access_token: AccessTokenResponse


class RefreshResponse(BaseModel):
    """Response for token refresh: new access token (+ rotated refresh cookie)."""
    access_token: AccessTokenResponse


# ------------------------------------------------------------
# Admin-only: user creation
# ------------------------------------------------------------

class UserCreate(BaseModel):
    """Body for admin-only user creation endpoint."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.HOST


class UserCreated(BaseModel):
    """Safe response confirming a user was created."""
    user: UserOut
    message: str = "User created."

