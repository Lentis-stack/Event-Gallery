# ============================================================
# Lentis Gallery — Guest Service
# ------------------------------------------------------------
# Business logic for guest registration + session management.
#
#     Route  -->  GuestService  -->  Database  -->  PostgreSQL
#
# WHAT LIVES HERE (the real rules):
#   * Event must exist and be LIVE before a guest can register.
#   * Guest names are validated/sanitized.
#   * A cryptographically random session token is minted; only its
#     SHA-256 hash is stored.
#   * Sessions are STRICTLY event-scoped: a session issued for
#     Event A can never authenticate against Event B.
#   * Session validation checks ACTIVE status + expiry + event match.
#   * Revocation sets status=REVOKED so the token dies immediately.
#
# WHY THE SERVICE LAYER?
#   Keeping business rules here (not in the route) means every
#   caller gets the same, correct behavior. The route stays thin.
# ============================================================

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    generate_guest_token,
    hash_guest_token,
)
from app.models.event import Event, EventStatus
from app.models.guest import Guest, GuestSession, GuestSessionStatus
from app.schemas.guest import GuestRegister

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _get_live_event_by_slug(db: Session, slug: str) -> Event:
    """
    Return the event, but only if it exists AND is LIVE.
    A guest cannot register for a non-existent, ended, or archived
    event. We return 404 for a missing slug and 400 for a known
    event that isn't live (so we don't leak event existence to
    random probes, but give a clear message when the event is real).
    """
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )
    if event.status != EventStatus.LIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event is not currently accepting guests.",
        )
    return event


def _get_event_session_or_404(
    db: Session, event_id: str, raw_token: str
) -> GuestSession:
    """
    Find the ACTIVE, unexpired guest session for the given event,
    or raise 401. This is the core event-isolation check.
    """
    token_hash = hash_guest_token(raw_token)
    session = db.scalar(
        select(GuestSession).where(GuestSession.token_hash == token_hash)
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest session.",
        )
    # EVENT ISOLATION: the session must belong to the requested event.
    if session.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest session.",
        )
    if session.status != GuestSessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest session.",
        )
# EXPIRY: reject if now >= expires_at.
    # NOTE on timezone: PostgreSQL stores timezone-aware timestamps.
    # SQLite (used ONLY in tests) stores them WITHOUT tz info, so
    # session.expires_at may come back naive. We normalize before
    # comparing so the logic works on both backends.
    expiry = session.expires_at
    now = datetime.now(timezone.utc)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if now >= expiry:
        # Mark it expired so it cannot be reused.
        session.status = GuestSessionStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest session has expired.",
        )
    return session


# ============================================================
# Registration
# ============================================================

def register_guest(
    db: Session,
    slug: str,
    payload: GuestRegister,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[Guest, GuestSession, str]:
    """
    Create a guest + a fresh session for a LIVE event.
    Returns (guest, session, raw_token). The raw token is returned
    ONLY to the caller (the route hands it to the client once);
    it is never stored.
    """
    event = _get_live_event_by_slug(db, slug)

    # Sanitize + validate the name (the schema already trims, but we
    # defensively trim again here).
    name = " ".join(payload.name.strip().split())
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Guest name cannot be empty.",
        )

    # 1. Create the Guest row.
    guest = Guest(event_id=event.id, name=name)
    db.add(guest)
    db.flush()  # assign guest.id

    # 2. Mint a random token + compute its expiry.
    raw_token = generate_guest_token()
    expires_at = datetime.now(timezone.utc).replace(
        microsecond=0
    ) + _session_timedelta()

    # 3. Create the GuestSession row (store ONLY the hash).
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

    db.commit()
    db.refresh(guest)
    db.refresh(session)

    logger.info(
        "Guest registered event_id=%s guest_id=%s session_id=%s",
        event.id, guest.id, session.id,
    )
    return guest, session, raw_token


def _session_timedelta() -> timedelta:
    """Return the guest-session lifetime as a timedelta."""
    return timedelta(hours=settings.GUEST_SESSION_EXPIRE_HOURS)


# ============================================================
# Session validation (GET /guests/me)
# ============================================================

def get_my_guest(
    db: Session, slug: str, raw_token: str
) -> tuple[Guest, GuestSession]:
    """
    Validate a guest session and return the guest it belongs to.
    Verifies: token exists + hash matches + ACTIVE + not expired +
    event matches the URL slug's event.
    """
    event = _get_live_event_by_slug(db, slug)
    session = _get_event_session_or_404(db, event.id, raw_token)
    guest = db.get(Guest, session.guest_id)
    if guest is None or guest.event_id != event.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest session.",
        )
    return guest, session


def get_authenticated_guest(
    db: Session, slug: str, raw_token: str
) -> tuple[Event, Guest, GuestSession]:
    """
    Full guest authentication used by media endpoints (Phase 5).
    Returns (event, guest, session) after verifying:
      - the event exists and is LIVE,
      - the session token is valid, ACTIVE, unexpired, and
        belongs to THIS event (strict event isolation),
      - the guest exists and belongs to the same event.
    """
    event = _get_live_event_by_slug(db, slug)
    session = _get_event_session_or_404(db, event.id, raw_token)
    guest = db.get(Guest, session.guest_id)
    if guest is None or guest.event_id != event.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest session.",
        )
    return event, guest, session


# ============================================================
# Session revocation (POST /guests/session/revoke)
# ============================================================

def revoke_guest_session(db: Session, slug: str, raw_token: str) -> None:
    """
    Revoke the current guest session immediately. The token becomes
    unusable right away (status=REVOKED).
    """
    event = _get_live_event_by_slug(db, slug)
    session = _get_event_session_or_404(db, event.id, raw_token)
    session.status = GuestSessionStatus.REVOKED
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Guest session revoked session_id=%s", session.id)
