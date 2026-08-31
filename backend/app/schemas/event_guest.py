# ============================================================
# Lentis Gallery — Event Invited Guest Schemas
# ------------------------------------------------------------
# Pydantic schemas for the private event guest management API.
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.event_guest import InvitedGuestStatus


class InvitedGuestCreate(BaseModel):
    """Body for adding an invited guest to a private event."""
    name: str = Field(..., min_length=1, max_length=120, description="Guest display name")
    password: str = Field(..., min_length=8, max_length=128, description="Guest password")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("Name cannot be empty or whitespace only.")
        return cleaned


class InvitedGuestUpdate(BaseModel):
    """Body for updating an invited guest (password reset)."""
    password: str = Field(..., min_length=8, max_length=128, description="New password")


class InvitedGuestOut(BaseModel):
    """Safe view of an invited guest (never exposes password_hash)."""
    id: str
    event_id: str
    name: str
    status: InvitedGuestStatus
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class InvitedGuestListResponse(BaseModel):
    """Response for listing invited guests."""
    guests: list[InvitedGuestOut]
    total: int
    joined: int
    not_joined: int


class PrivateGuestLoginRequest(BaseModel):
    """Body for private guest login."""
    name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("Name cannot be empty or whitespace only.")
        return cleaned


class PrivateGuestLoginResponse(BaseModel):
    """Response to a successful private guest login."""
    guest: InvitedGuestOut
    session_token: str
    expires_at: datetime
