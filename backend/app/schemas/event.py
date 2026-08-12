# ============================================================
# Lentis Gallery — Event Schemas
# ------------------------------------------------------------
# Pydantic schemas for the Event Management API.
#
# WHY SEPARATE SCHEMAS FROM THE DATABASE MODEL?
#   - We NEVER return the raw SQLAlchemy Event object directly.
#   - Different audiences need different fields:
#       * Admin sees host info, timestamps, status.
#       * Host sees their own event's editable fields.
#       * Public sees ONLY safe, non-sensitive fields.
#   - Keeping schemas separate means we control exactly what
#     leaves the API. We can never accidentally leak internal
#     columns we didn't intend to expose.
# ============================================================

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.event import EventStatus, ThemeChoice


# Conservative field length limits (backend validation, not just
# frontend). These are the SAME limits the frontend will expect.
NAME_MAX = 255
SLUG_MAX = 255
SUBTITLE_MAX = 500


# ------------------------------------------------------------
# Create / Update payloads
# ------------------------------------------------------------

class EventCreate(BaseModel):
    """Body for admin creating an event."""
    name: str = Field(..., min_length=3, max_length=NAME_MAX, description="Event name")
    subtitle: str | None = Field(None, max_length=SUBTITLE_MAX, description="Short one-liner")
    host_id: str = Field(..., description="UUID of the HOST user who will own this event")
    event_date: date = Field(..., description="The event's calendar date (YYYY-MM-DD)")
    theme: ThemeChoice = Field(ThemeChoice.GOLD, description="Brand theme accent")
    # slug is OPTIONAL on create: if omitted, the backend generates
    # one from the name (slugify). If provided, it is validated.
    slug: str | None = Field(
        None, max_length=SLUG_MAX, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Optional URL slug (auto-generated from name if omitted)",
    )


class EventUpdate(BaseModel):
    """Body for updating an event (all fields optional = PATCH)."""
    name: str | None = Field(None, min_length=3, max_length=NAME_MAX)
    subtitle: str | None = Field(None, max_length=SUBTITLE_MAX)
    event_date: date | None = None
    theme: ThemeChoice | None = None
    # Admin-only editable fields (not allowed for hosts):
    host_id: str | None = None
    status: EventStatus | None = None


# ------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------

class HostBrief(BaseModel):
    """Minimal, safe view of a host user (never password_hash)."""
    id: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


# Full event used by Admin (and Host for their own events). This
# includes the host's email for the admin console to display.
class EventOut(BaseModel):
    id: str
    name: str
    slug: str
    subtitle: str | None
    host_id: str
    event_date: date
    status: EventStatus
    theme: ThemeChoice
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    # Nested safe host info (email only).
    host: HostBrief | None = None

    model_config = ConfigDict(from_attributes=True)


# The public-facing event object. Contains ONLY fields a guest's
# browser needs. No host id, no internal timestamps beyond what is
# needed, no auth info.
class PublicEventOut(BaseModel):
    name: str
    slug: str
    subtitle: str | None
    theme: ThemeChoice
    event_date: date
    status: EventStatus

    model_config = ConfigDict(from_attributes=True)
