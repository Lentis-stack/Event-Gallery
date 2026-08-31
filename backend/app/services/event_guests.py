# ============================================================
# Lentis Gallery — Event Invited Guest Service
# ------------------------------------------------------------
# Business logic for managing invited guests on private events
# and authenticating private guests.
#
#     Route  -->  EventGuestService  -->  Database  -->  PostgreSQL
#
# SECURITY:
#   * Passwords are hashed with Argon2id (same as user passwords).
#   * Plaintext passwords are NEVER stored or returned by API.
#   * Guest authentication verifies event + name + password.
#   * Removed guests cannot authenticate.
# ============================================================

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    generate_guest_token,
    hash_guest_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.event import Event, EventAccessMode, EventStatus
from app.models.event_guest import EventInvitedGuest, InvitedGuestStatus
from app.models.guest import GuestSession, GuestSessionStatus
from app.schemas.event_guest import (
    InvitedGuestCreate,
    InvitedGuestListResponse,
    InvitedGuestOut,
    InvitedGuestUpdate,
)

logger = logging.getLogger(__name__)


def _get_event_or_404(db: Session, event_id: str) -> Event:
    """Return event or 404."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


def _get_live_event_by_slug(db: Session, slug: str) -> Event:
    """Return the event only if LIVE."""
    from sqlalchemy import select as sel
    event = db.scalar(sel(Event).where(Event.slug == slug))
    if event is None or event.status != EventStatus.LIVE:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


# ============================================================
# ADMIN: List invited guests for an event
# ============================================================

def list_invited_guests(db: Session, event_id: str) -> InvitedGuestListResponse:
    """List all invited guests for an event (admin only)."""
    _get_event_or_404(db, event_id)

    guests = list(
        db.scalars(
            select(EventInvitedGuest)
            .where(EventInvitedGuest.event_id == event_id)
            .order_by(EventInvitedGuest.created_at.desc())
        )
    )

    total = len(guests)
    joined = sum(1 for g in guests if g.status == InvitedGuestStatus.ACTIVE)
    not_joined = sum(1 for g in guests if g.status == InvitedGuestStatus.INVITED)

    return InvitedGuestListResponse(
        guests=[InvitedGuestOut.model_validate(g) for g in guests],
        total=total,
        joined=joined,
        not_joined=not_joined,
    )


# ============================================================
# ADMIN: Add invited guest
# ============================================================

def add_invited_guest(
    db: Session, event_id: str, payload: InvitedGuestCreate
) -> InvitedGuestOut:
    """Add an invited guest to a private event (admin only)."""
    event = _get_event_or_404(db, event_id)

    # Validate password strength
    strength_error = validate_password_strength(payload.password)
    if strength_error:
        raise HTTPException(status_code=400, detail=strength_error)

    # Check for duplicate name within the same event
    existing = db.scalar(
        select(EventInvitedGuest).where(
            EventInvitedGuest.event_id == event_id,
            EventInvitedGuest.name == payload.name.strip(),
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A guest named '{payload.name.strip()}' already exists for this event.",
        )

    # Create the invited guest
    invited_guest = EventInvitedGuest(
        event_id=event_id,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        status=InvitedGuestStatus.INVITED,
    )
    db.add(invited_guest)
    db.commit()
    db.refresh(invited_guest)

    logger.info(
        "Invited guest added: id=%s event_id=%s name=%s",
        invited_guest.id, event_id, invited_guest.name,
    )
    return InvitedGuestOut.model_validate(invited_guest)


# ============================================================
# ADMIN: Reset invited guest password
# ============================================================

def reset_invited_guest_password(
    db: Session, event_id: str, guest_id: str, payload: InvitedGuestUpdate
) -> InvitedGuestOut:
    """Reset an invited guest's password (admin only)."""
    _get_event_or_404(db, event_id)

    # Validate password strength
    strength_error = validate_password_strength(payload.password)
    if strength_error:
        raise HTTPException(status_code=400, detail=strength_error)

    # Find the guest
    invited_guest = db.scalar(
        select(EventInvitedGuest).where(
            EventInvitedGuest.id == guest_id,
            EventInvitedGuest.event_id == event_id,
        )
    )
    if invited_guest is None:
        raise HTTPException(status_code=404, detail="Guest not found.")

    invited_guest.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(invited_guest)

    logger.info(
        "Invited guest password reset: guest_id=%s event_id=%s",
        guest_id, event_id,
    )
    return InvitedGuestOut.model_validate(invited_guest)


# ============================================================
# ADMIN: Remove invited guest
# ============================================================

def remove_invited_guest(
    db: Session, event_id: str, guest_id: str
) -> None:
    """Remove an invited guest (admin only). Sets status to REMOVED.
    Does NOT delete the row or their existing media."""
    _get_event_or_404(db, event_id)

    invited_guest = db.scalar(
        select(EventInvitedGuest).where(
            EventInvitedGuest.id == guest_id,
            EventInvitedGuest.event_id == event_id,
        )
    )
    if invited_guest is None:
        raise HTTPException(status_code=404, detail="Guest not found.")

    invited_guest.status = InvitedGuestStatus.REMOVED

    # Also revoke any active sessions for this invited guest
    _revoke_invited_guest_sessions(db, event_id, invited_guest.name)

    db.commit()
    logger.info(
        "Invited guest removed: guest_id=%s event_id=%s name=%s",
        guest_id, event_id, invited_guest.name,
    )


def _revoke_invited_guest_sessions(db: Session, event_id: str, guest_name: str) -> None:
    """Revoke all guest sessions matching the invited guest name + event."""
    # Find all Guest rows for this name in this event
    from app.models.guest import Guest
    guests = list(
        db.scalars(
            select(Guest).where(
                Guest.event_id == event_id,
                Guest.name == guest_name,
            )
        )
    )
    for guest in guests:
        sessions = list(
            db.scalars(
                select(GuestSession).where(
                    GuestSession.guest_id == guest.id,
                    GuestSession.status == GuestSessionStatus.ACTIVE,
                )
            )
        )
        for sess in sessions:
            sess.status = GuestSessionStatus.REVOKED
            sess.revoked_at = datetime.now(timezone.utc)


# ============================================================
# PRIVATE GUEST: Login (authenticate with name + password)
# ============================================================

def private_guest_login(
    db: Session,
    slug: str,
    name: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[EventInvitedGuest, GuestSession, str]:
    """
    Authenticate a private event guest with name + password.
    Returns (invited_guest, session, raw_token).

    Flow:
    1. Find event by slug, verify LIVE + PRIVATE.
    2. Find invited guest by name + event_id.
    3. Verify password.
    4. Check status (not REMOVED).
    5. Create a GuestSession (reuse existing Guest model for media ownership).
    6. Create a Guest row (for media FK).
    """
    event = _get_live_event_by_slug(db, slug)

    # Must be a private event
    if event.access_mode != EventAccessMode.PRIVATE:
        raise HTTPException(
            status_code=400,
            detail="This event does not require private access.",
        )

    # Find the invited guest
    invited_guest = db.scalar(
        select(EventInvitedGuest).where(
            EventInvitedGuest.event_id == event.id,
            EventInvitedGuest.name == name.strip(),
        )
    )

    # Generic error (don't reveal whether name or password is wrong)
    auth_error = HTTPException(
        status_code=401,
        detail="Invalid name or password.",
    )

    if invited_guest is None:
        raise auth_error

    # Check status
    if invited_guest.status == InvitedGuestStatus.REMOVED:
        raise HTTPException(
            status_code=403,
            detail="Your access to this event has been removed.",
        )

    # Verify password
    if not verify_password(password, invited_guest.password_hash):
        raise auth_error

    # Create a Guest row for media ownership (reuses existing Guest model)
    from app.models.guest import Guest
    guest = Guest(event_id=event.id, name=invited_guest.name)
    db.add(guest)
    db.flush()

    # Create a session token
    raw_token = generate_guest_token()
    expires_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(
        hours=settings.GUEST_SESSION_EXPIRE_HOURS
    )

    session = GuestSession(
        guest_id=guest.id,
        event_id=event.id,
        token_hash=hash_guest_token(raw_token),
        status=GuestSessionStatus.ACTIVE,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=user_agent,
    )
    db.add(session)

    # Update invited guest status + last_login_at
    if invited_guest.status == InvitedGuestStatus.INVITED:
        invited_guest.status = InvitedGuestStatus.ACTIVE
    invited_guest.last_login_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(guest)
    db.refresh(session)

    logger.info(
        "Private guest login: invited_guest_id=%s event_id=%s guest_id=%s",
        invited_guest.id, event.id, guest.id,
    )
    return invited_guest, session, raw_token
