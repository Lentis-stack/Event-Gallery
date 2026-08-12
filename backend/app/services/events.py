# ============================================================
# Lentis Gallery — Event Service
# ------------------------------------------------------------
# Business logic for events. Routes stay THIN and call these
# functions. The service owns the real rules:
#
#     Route  -->  EventService  -->  Database  -->  PostgreSQL
#
# WHAT LIVES HERE:
#   - slug generation + uniqueness (duplicate -> 409)
#   - verifying the assigned host exists AND has HOST role
#   - status transition rules (LIVE -> ENDED -> ARCHIVED, etc.)
#   - host OWNERSHIP checks (a host only sees their own event)
#   - soft archive (set ARCHIVED + archived_at, never delete)
#
# These rules are enforced server-side, so no frontend/API caller
# can bypass them.
# ============================================================

import logging
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event, EventStatus, ThemeChoice
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventUpdate

logger = logging.getLogger(__name__)


# ============================================================
# Slug helpers
# ============================================================

def slugify(name: str) -> str:
    """Turn an event name into a URL-safe, lowercase slug.

    Examples:
        "TARAGOLD 2026"   -> "taragold-2026"
        "Aurora Spring!"  -> "aurora-spring"
    """
    slug = name.strip().lower()
    # Replace any run of non-alphanumeric chars with a single dash.
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Trim leading/trailing dashes.
    slug = slug.strip("-")
    return slug


def _ensure_unique_slug(db: Session, slug: str, exclude_event_id: str | None = None) -> str:
    """Guarantee a globally unique slug.

    If the slug is already taken, append a numeric suffix until it
    is available (e.g. "taragold-2026-2"). This avoids a 500 error
    from the DB unique constraint and gives the admin a usable link.
    """
    candidate = slug
    counter = 2
    while True:
        query = select(Event).where(Event.slug == candidate)
        if exclude_event_id:
            query = query.where(Event.id != exclude_event_id)
        existing = db.scalar(query)
        if existing is None:
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


# ============================================================
# Validation helpers
# ============================================================

def _get_host_or_404(db: Session, host_id: str) -> User:
    """Return a user, but ONLY if they exist and have HOST role."""
    host = db.get(User, host_id)
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host user not found.",
        )
    if host.role != UserRole.HOST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned host must have the HOST role.",
        )
    return host


# ============================================================
# Status transition rules
# ============================================================

# Allowed transitions. Over-engineering is avoided; these are the
# only sensible moves for an event lifecycle.
ALLOWED_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.LIVE: {EventStatus.ENDED, EventStatus.ARCHIVED},
    EventStatus.ENDED: {EventStatus.ARCHIVED},
    EventStatus.ARCHIVED: set(),  # archived is terminal in Phase 3
}


def _validate_transition(current: EventStatus, new: EventStatus) -> None:
    """Reject nonsensical status moves (e.g. ENDED -> LIVE)."""
    if new == current:
        return
    if new not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition event from {current.value} to {new.value}.",
        )


# ============================================================
# CRUD operations
# ============================================================

def create_event(db: Session, payload: EventCreate) -> Event:
    """Admin creates a new LIVE event for a real HOST user."""
    # 1. Verify the host exists + has HOST role.
    _get_host_or_404(db, payload.host_id)

    # 2. Determine the slug (provided or generated from the name).
    base_slug = payload.slug if payload.slug else slugify(payload.name)
    if not base_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event name must produce a valid slug.",
        )
    unique_slug = _ensure_unique_slug(db, base_slug)

    # 3. Build + persist the event.
    event = Event(
        name=payload.name.strip(),
        slug=unique_slug,
        subtitle=payload.subtitle.strip() if payload.subtitle else None,
        host_id=payload.host_id,
        event_date=payload.event_date,
        status=EventStatus.LIVE,  # default status on admin creation
        theme=payload.theme,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info("Event created id=%s slug=%s host_id=%s", event.id, event.slug, event.host_id)
    return event


def get_event(db: Session, event_id: str) -> Event:
    """Return an event by id, or 404."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return event


def get_event_by_slug(db: Session, slug: str) -> Event:
    """Return an event by unique slug, or 404."""
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return event


def list_events(db: Session) -> list[Event]:
    """Return ALL events (admin view), newest first."""
    return list(db.scalars(select(Event).order_by(Event.created_at.desc())))


def list_host_events(db: Session, host_id: str) -> list[Event]:
    """Return ONLY the events owned by a specific host."""
    return list(
        db.scalars(
            select(Event)
            .where(Event.host_id == host_id)
            .order_by(Event.created_at.desc())
        )
    )


def get_host_event(db: Session, host_id: str, event_id: str) -> Event:
    """
    Return an event IF it belongs to the given host. If the event
    exists but belongs to another host, return 404 so we do NOT
    leak that the event exists at all.
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return event


# ============================================================
# Updates
# ============================================================

def _apply_update(event: Event, payload: EventUpdate) -> None:
    """Apply allowed field changes to an event object (no commit)."""
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        event.name = data["name"].strip()
    if "subtitle" in data:
        event.subtitle = data["subtitle"].strip() if data["subtitle"] else None
    if "event_date" in data:
        event.event_date = data["event_date"]
    if "theme" in data:
        event.theme = data["theme"]
    if "status" in data and data["status"] is not None:
        _validate_transition(event.status, data["status"])
        event.status = data["status"]


def update_event(db: Session, event_id: str, payload: EventUpdate) -> Event:
    """Admin updates any event (including host_id/status)."""
    event = get_event(db, event_id)

    # If the admin is re-assigning the host, validate the new user.
    data = payload.model_dump(exclude_unset=True)
    if "host_id" in data and data["host_id"] is not None:
        _get_host_or_404(db, data["host_id"])
        event.host_id = data["host_id"]

    _apply_update(event, payload)
    db.commit()
    db.refresh(event)
    logger.info("Event updated id=%s", event.id)
    return event


def update_host_event(db: Session, host_id: str, event_id: str, payload: EventUpdate) -> Event:
    """
    A host updates ONLY their own event, and ONLY safe fields.
    host_id/status are intentionally NOT applied for hosts.
    """
    event = get_host_event(db, host_id, event_id)

    # Build a host-safe payload: strip host_id and status.
    data = payload.model_dump(exclude_unset=True)
    host_payload = EventUpdate(**{k: v for k, v in data.items()
                                  if k in ("name", "subtitle", "event_date", "theme")})

    _apply_update(event, host_payload)
    db.commit()
    db.refresh(event)
    logger.info("Host updated event id=%s host_id=%s", event.id, host_id)
    return event


def archive_event(db: Session, event_id: str) -> Event:
    """
    Soft-archive an event: set status=ARCHIVED and archived_at=now.
    The row is NEVER physically deleted (we need history later).
    """
    event = get_event(db, event_id)
    if event.status != EventStatus.ARCHIVED:
        _validate_transition(event.status, EventStatus.ARCHIVED)
        event.status = EventStatus.ARCHIVED
        event.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(event)
        logger.info("Event archived id=%s", event.id)
    return event
