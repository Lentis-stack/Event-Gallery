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

from app.models.event import Event, EventAccessMode, EventStatus, ThemeChoice
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventUpdate
from app.services import auth as auth_service
from app.core.security import hash_password, validate_password_strength

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
    EventStatus.CREATED: {EventStatus.LIVE, EventStatus.ARCHIVED},
    EventStatus.LIVE: {EventStatus.ENDED, EventStatus.ARCHIVED},
    EventStatus.ENDED: {EventStatus.ARCHIVED},
    EventStatus.ARCHIVED: {EventStatus.CREATED},  # restore from archive
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

def _resolve_host(db: Session, payload: EventCreate) -> str:
    """
    Resolve the host for event creation.
    If host_id is provided, verify it exists and has HOST role.
    If host_email is provided, find or create the host user.
    Returns the host_id.
    """
    if payload.host_id:
        host = _get_host_or_404(db, payload.host_id)
        return host.id

    if payload.host_email:
        normalized_email = payload.host_email.strip().lower()
        # Try to find existing user
        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            # User exists — if they have HOST role, use them
            if existing.role == UserRole.HOST:
                # If a new password was provided, update it
                if payload.host_password:
                    strength_error = validate_password_strength(payload.host_password)
                    if strength_error:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=strength_error,
                        )
                    existing.password_hash = hash_password(payload.host_password)
                    db.commit()
                    logger.info("Updated host password for user_id=%s email=%s", existing.id, normalized_email)
                return existing.id
            # If they have ADMIN role, we can't assign them as host
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {normalized_email} already exists with role {existing.role.value}. Cannot assign as host.",
            )
        # User doesn't exist — create them
        if not payload.host_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host password is required when creating a new host user.",
            )
        user = auth_service.create_user(db, normalized_email, payload.host_password, UserRole.HOST)
        logger.info("Auto-created host user id=%s email=%s", user.id, normalized_email)
        return user.id

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either host_id or host_email must be provided.",
    )


def create_event(db: Session, payload: EventCreate) -> Event:
    """Admin creates a new event (starts in CREATED status, not LIVE)."""
    # 1. Resolve the host (find existing or create new).
    host_id = _resolve_host(db, payload)

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
        event_type=payload.event_type.strip() if payload.event_type else None,
        location=payload.location.strip() if payload.location else None,
        description=payload.description.strip() if payload.description else None,
        landing_message=payload.landing_message.strip() if payload.landing_message else None,
        host_id=host_id,
        event_date=payload.event_date,
        status=EventStatus.CREATED,
        theme=payload.theme,
        access_mode=payload.access_mode,
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
    if "event_type" in data:
        event.event_type = data["event_type"].strip() if data["event_type"] else None
    if "location" in data:
        event.location = data["location"].strip() if data["location"] else None
    if "description" in data:
        event.description = data["description"].strip() if data["description"] else None
    if "landing_message" in data:
        event.landing_message = data["landing_message"].strip() if data["landing_message"] else None
    if "event_date" in data:
        event.event_date = data["event_date"]
    if "theme" in data:
        event.theme = data["theme"]
    if "access_mode" in data and data["access_mode"] is not None:
        event.access_mode = data["access_mode"]
    if "status" in data and data["status"] is not None:
        _validate_transition(event.status, data["status"])
        event.status = data["status"]


def update_event(db: Session, event_id: str, payload: EventUpdate, admin_user_id: str | None = None) -> Event:
    """Admin updates any event (including host_id/status).

    SEC-021: When host_id changes, an audit log entry is recorded
    with the previous host, new host, and the admin who made the change.
    """
    event = get_event(db, event_id)

    data = payload.model_dump(exclude_unset=True)

    # Handle host reassignment by email
    if "host_email" in data and data["host_email"] is not None:
        normalized_email = data["host_email"].strip().lower()
        host_user = db.scalar(select(User).where(User.email == normalized_email))
        if host_user:
            if host_user.role != UserRole.HOST:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User {normalized_email} already exists with role {host_user.role.value}.",
                )
        else:
            # Create new host user
            if not data.get("host_password"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Host password is required when creating a new host user.",
                )
            host_user = auth_service.create_user(db, normalized_email, data["host_password"], UserRole.HOST)
        event.host_id = host_user.id

    # Handle host password update
    if "host_password" in data and data["host_password"] is not None and data["host_password"].strip():
        host_user = db.get(User, event.host_id)
        if host_user:
            strength_error = validate_password_strength(data["host_password"])
            if strength_error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=strength_error,
                )
            host_user.password_hash = hash_password(data["host_password"])
            logger.info("Admin reset host password for host_id=%s event_id=%s", event.host_id, event_id)

    # SEC-021: If the admin is re-assigning the host via host_id, log the change.
    if "host_id" in data and data["host_id"] is not None:
        old_host_id = event.host_id
        new_host_id = data["host_id"]
        if old_host_id != new_host_id:
            _get_host_or_404(db, new_host_id)
            logger.info(
                "SECURITY_AUDIT host_reassignment event_id=%s old_host_id=%s new_host_id=%s admin_user_id=%s",
                event_id, old_host_id, new_host_id, admin_user_id or "unknown",
            )
            event.host_id = new_host_id

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
                                  if k in ("name", "subtitle", "event_type", "location", "description", "landing_message", "event_date", "theme")})

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


def restore_event(db: Session, event_id: str) -> Event:
    """
    Restore an archived event: set status=CREATED and clear archived_at.
    """
    event = get_event(db, event_id)
    if event.status != EventStatus.CREATED:
        _validate_transition(event.status, EventStatus.CREATED)
        event.status = EventStatus.CREATED
        event.archived_at = None
        db.commit()
        db.refresh(event)
        logger.info("Event restored id=%s", event.id)
    return event


def permanent_delete_event(db: Session, event_id: str) -> None:
    """
    Permanently delete an event and all associated data.
    This is irreversible — use with caution.
    """
    event = get_event(db, event_id)

    # Delete associated media records and their storage objects
    from app.models.media import Media
    from app.storage import get_storage_service
    storage = get_storage_service()
    media_records = list(db.scalars(select(Media).where(Media.event_id == event_id)))
    for m in media_records:
        # Delete from object storage (best-effort)
        if m.storage_key:
            try:
                storage.delete(m.storage_key)
            except Exception:
                logger.warning("Failed to delete storage key %s for media %s", m.storage_key, m.id)
        # Delete processed variants
        for key_attr in ('optimized_key', 'thumbnail_key', 'poster_key'):
            key = getattr(m, key_attr, None)
            if key:
                try:
                    storage.delete(key)
                except Exception:
                    logger.warning("Failed to delete %s %s", key_attr, key)
        db.delete(m)

    # Delete associated guest sessions
    from app.models.guest import Guest
    db.query(Guest).filter(Guest.event_id == event_id).delete()

    # Delete the event itself
    db.delete(event)
    db.commit()
    logger.info("Event permanently deleted id=%s", event_id)


def host_start_event(db: Session, host_id: str, event_id: str) -> Event:
    """
    Host starts their own event: CREATED -> LIVE.
    Only the event's owner host can start it.
    """
    event = get_host_event(db, host_id, event_id)
    if event.status != EventStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event cannot be started from {event.status.value} status.",
        )
    event.status = EventStatus.LIVE
    db.commit()
    db.refresh(event)
    logger.info("Host started event id=%s host_id=%s", event.id, host_id)
    return event
