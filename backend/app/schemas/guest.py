# ============================================================
# Lentis Gallery — Guest Schemas
# ------------------------------------------------------------
# Pydantic schemas for the Guest Registration & Session API.
#
# WHY SEPARATE FROM THE ORM MODEL?
#   * We NEVER return the raw SQLAlchemy Guest/GuestSession object.
#   * The raw token is returned ONCE at registration and then never
#     again. We do NOT expose token_hash, revoke details we don't
#     need, or any "internal" bookkeeping.
#   * Schemas are the contract between the API and the frontend.
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Guest name rules (backend validation, not just the frontend).
NAME_MIN = 1
NAME_MAX = 120


# ------------------------------------------------------------
# Registration request
# ------------------------------------------------------------

class GuestRegister(BaseModel):
    """
    Body for POST /api/events/{slug}/guests.
    A guest only needs to provide their name — no email, no password.
    """
    name: str = Field(
        ...,
        min_length=NAME_MIN,
        max_length=NAME_MAX,
        description="The guest's display name",
    )

    # Strip surrounding whitespace and collapse internal runs of
    # spaces so "  John   " becomes "John". This runs AFTER the
    # length checks, so we also guard against whitespace-only names.
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("Name cannot be empty or whitespace only.")
        return cleaned


# ------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------

class GuestOut(BaseModel):
    """Safe view of a guest (no sessions, no internal fields)."""
    id: str
    event_id: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuestSessionInfo(BaseModel):
    """
    Details about a guest's session. The RAW token (session_token)
    is returned ONLY here, at creation time. It is not stored by the
    backend (only its SHA-256 hash is kept).
    """
    session_id: str
    session_token: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuestRegisterResponse(BaseModel):
    """Response to a successful guest registration."""
    guest: GuestOut
    session: GuestSessionInfo


class GuestMeResponse(BaseModel):
    """Response to GET .../guests/me — the guest's own info."""
    guest: GuestOut
    session_status: str
