# ============================================================
# Lentis Gallery — Guest & GuestSession Models
# ------------------------------------------------------------
# Phase 4 introduces GUESTS. A guest is someone who attends an
# event and uploads media. IMPORTANT: a guest is NOT a platform
# user — they have no password, no email, and no User account.
#
# WHY DON'T GUESTS NEED A USER ACCOUNT?
#   * Asking every wedding guest to create an account would be
#     terrible UX and totally unnecessary.
#   * Guests only need a lightweight, event-scoped identity so we
#     can (a) remember their name, and (b) later attribute uploaded
#     media to them.
#   * Creating a full User row for every guest would pollute the
#     secure auth system and bloat the users table with thousands
#     of meaningless rows.
#
# GUEST (the person) vs GUESTSESSION (the access right):
#   * A Guest row is "who they are" — name + which event.
#   * A GuestSession is "proof they may access the event" — a
#     secret token that expires. A guest can have many sessions
#     (e.g. on their phone and laptop); each is independent.
#   * Sessions borrow the SAME security model as refresh tokens:
#     we store the SHA-256 HASH of the token, never the raw token.
#
# EVENT ISOLATION:
#   Both Guest and GuestSession carry an event_id. The validation
#   code checks that a session's event_id matches the event in the
#   URL. A token minted for Event A can NEVER authenticate against
#   Event B because the event_id won't match.
#
# CASCADE DELETE:
#   guest_sessions.guest_id -> guests.id  ON DELETE CASCADE
#   guests.event_id -> events.id          ON DELETE CASCADE
#   If a guest is deleted, their sessions vanish too. If an event
#   is deleted, its guests and their sessions vanish. No orphans.
# ============================================================

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import utcnow


def generate_uuid() -> str:
    """Random UUID string primary key (not guessable like 1,2,3...)."""
    return str(uuid.uuid4())


class GuestSessionStatus(str, enum.Enum):
    """Lifecycle of a guest session."""
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class Guest(Base):
    """A person attending an event. Not a platform User."""

    __tablename__ = "guests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Which event this guest belongs to. FK -> events.id.
    # ON DELETE CASCADE: if the event is deleted, its guests go too.
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # The guest's display name (validated + sanitized at the API layer).
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # When they first registered.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # ORM relationship to the event this guest belongs to.
    event: Mapped["Event"] = relationship()  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Guest id={self.id} event_id={self.event_id} name={self.name!r}>"


class GuestSession(Base):
    """
    A single proof-of-access for a guest.

    SECURITY MODEL (mirrors refresh tokens):
      - The RAW token is handed to the client in the registration
        response and is NEVER stored.
      - We store only token_hash = SHA256(raw_token).
      - To validate, we hash the presented token and look for a
        matching, ACTIVE, unexpired row whose event_id matches.
    """

    __tablename__ = "guest_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Which guest this session belongs to. FK -> guests.id.
    guest_id: Mapped[str] = mapped_column(
        ForeignKey("guests.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Denormalized event id for FAST event-scoping checks.
    # FK to events.id; if the event is deleted, the session goes too.
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # SHA-256 hash of the raw token (NEVER the raw token).
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    # Lifecycle: ACTIVE / REVOKED / EXPIRED.
    status: Mapped[GuestSessionStatus] = mapped_column(
        Enum(GuestSessionStatus, name="guest_session_status"),
        nullable=False,
        default=GuestSessionStatus.ACTIVE,
    )

    # When this session becomes invalid (timezone-aware UTC).
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Audit metadata (not logged raw, just stored for accountability).
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<GuestSession id={self.id} event_id={self.event_id} status={self.status}>"
