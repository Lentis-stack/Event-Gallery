# ============================================================
# Lentis Gallery — Event Invited Guest Model
# ------------------------------------------------------------
# Phase 13.18. For PRIVATE events, the Admin invites guests
# by name + password. Invited guests authenticate before
# accessing the camera/upload flow.
#
# WHY A SEPARATE MODEL FROM Guest?
#   * Guest (existing) = anyone who registers at a public event.
#     No password, no admin invitation, lightweight.
#   * EventInvitedGuest = admin-managed, password-protected,
#     event-specific identity for private events.
#   * They serve different purposes and have different auth models.
#
# SECURITY:
#   * Only password_hash is stored, never the plaintext password.
#   * Each invited guest belongs to exactly one event.
#   * Status controls access: INVITED, ACTIVE, REMOVED.
# ============================================================

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import utcnow


def generate_uuid() -> str:
    """Random UUID string primary key."""
    return str(uuid.uuid4())


class InvitedGuestStatus(str, enum.Enum):
    """Lifecycle of an invited guest."""
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class EventInvitedGuest(Base):
    """An invited guest for a private event."""
    __tablename__ = "event_invited_guests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Which event this guest is invited to.
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Guest's display name (used for login + display).
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Argon2id password hash. NEVER store plaintext.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Access status.
    status: Mapped[InvitedGuestStatus] = mapped_column(
        Enum(InvitedGuestStatus, name="invited_guest_status"),
        nullable=False,
        default=InvitedGuestStatus.INVITED,
        server_default="INVITED",
    )

    # Timestamps.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ORM relationship to the event.
    event: Mapped["Event"] = relationship()  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<EventInvitedGuest id={self.id} event_id={self.event_id} name={self.name!r}>"
