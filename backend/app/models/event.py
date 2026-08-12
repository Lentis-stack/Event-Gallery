# ============================================================
# Lentis Gallery — Event Model
# ------------------------------------------------------------
# This is the SQLAlchemy ORM class for the "events" table.
#
# WHAT THIS MODEL REPRESENTS:
#   A real event (wedding, festival, gala, ...) that Lentis hosts.
#   One event belongs to exactly ONE host (a User with HOST role).
#   A host may own MANY events over time.
#
# RELATIONSHIP DIAGRAM:
#       users (parent)
#          |
#          | 1  (a host user)
#          |
#       events (child)
#          |
#          | N  (later: media records belong to an event)
#          |
#       media  (Phase 5+ — metadata only, bytes in object storage)
#
# WHY A FOREIGN KEY?
#   A foreign key (host_id -> users.id) is the database's promise
#   that every event's host actually exists in the users table.
#   PostgreSQL enforces this so we cannot create an orphan event
#   that points at a non-existent user.
#
# SECURITY / DESIGN NOTES:
#   - slug is UNIQUE — the database itself prevents two events
#     from sharing the same public URL slug.
#   - status uses a Python Enum (LIVE/ENDED/ARCHIVED), not magic
#     strings, so invalid values are rejected.
#   - archived_at records when an event was archived WITHOUT
#     physically deleting the row (soft archive).
#   - Timestamps are timezone-aware UTC.
# ============================================================

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import utcnow


class EventStatus(str, enum.Enum):
    """Lifecycle status of an event. No DRAFT in Phase 3."""
    LIVE = "LIVE"
    ENDED = "ENDED"
    ARCHIVED = "ARCHIVED"


class ThemeChoice(str, enum.Enum):
    """Brand colour theme options for an event."""
    GOLD = "gold"
    BLUE = "blue"
    ROSE = "rose"
    EMERALD = "emerald"


def generate_uuid() -> str:
    """Random UUID string primary key (not guessable like 1,2,3...)."""
    return str(uuid.uuid4())


class Event(Base):
    __tablename__ = "events"

    # Primary key — random UUID string.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Public name of the event, e.g. "TARAGOLD 2026".
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Unique URL slug, e.g. "taragold-2026". DB enforces uniqueness.
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Short emotional one-line description.
    subtitle: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Which HOST user owns this event. FK -> users.id.
    host_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    # The calendar date the event takes/happened place on.
    event_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Lifecycle status (LIVE / ENDED / ARCHIVED).
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"), nullable=False, default=EventStatus.LIVE
    )

    # Brand theme accent (gold / blue / rose / emerald).
    theme: Mapped[ThemeChoice] = mapped_column(
        Enum(ThemeChoice, name="theme_choice"), nullable=False, default=ThemeChoice.GOLD
    )

    # Timestamps (timezone-aware UTC).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Set when archived (soft archive). NULL until archived.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# ORM relationship to the owning user. We only need the host's
    # email/name for admin responses; we never expose password_hash.
    host: Mapped["User"] = relationship()  # type: ignore[name-defined]

    # ORM relationship to the guests who register for this event.
    # One event -> many guests. Phase 4. CASCADE so deleting an event
    # removes its guests and their sessions.
    guests: Mapped[list["Guest"]] = relationship(  # type: ignore[name-defined]
        back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id} slug={self.slug} status={self.status}>"


# Composite/all-key indexes for the queries we'll run most:
#   - lookups by slug (unique index already set above)
#   - list a host's events (host_id index set above)
#   - filter events by status
Index("ix_events_status", Event.status)
Index("ix_events_created_at", Event.created_at)
