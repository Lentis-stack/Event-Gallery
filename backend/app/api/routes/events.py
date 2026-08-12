# ============================================================
# Lentis Gallery — Events Routes
# ------------------------------------------------------------
# Two kinds of endpoints live here:
#   - POST /api/events        (ADMIN only — create an event)
#   - GET /api/events/{slug}/public  (PUBLIC — guest lookup)
#
# The create endpoint is grouped here because it's the canonical
# "create an event" action. The admin list/detail/update/archive
# endpoints live in admin_events.py, and host endpoints in
# host_events.py.
# ============================================================

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.event import EventCreate, EventOut, PublicEventOut
from app.services import events as event_service

logger = logging.getLogger(__name__)

# No prefix here — paths are fully written out so the public and
# admin routes are clearly separated.
router = APIRouter(tags=["events"])


# ============================================================
# POST /api/events  (ADMIN only)
# ============================================================

@router.post(
    "/api/events",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an event (admin only)",
    description=(
        "Creates a new LIVE event and assigns it to an existing HOST user. "
        "Requires an ADMIN access token. The slug is auto-generated from the "
        "name unless one is provided. Returns 409 if the slug is not unique."
    ),
)
def create_event(
    body: EventCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.create_event(db, body)


# ============================================================
# GET /api/events/{slug}/public  (PUBLIC)
# ============================================================
# This is the endpoint a guest's browser hits when they open an
# event link like /event/taragold-2026. It needs NO authentication
# and returns only safe, public fields.

@router.get(
    "/api/events/{slug}/public",
    response_model=PublicEventOut,
    summary="Get public event info (no auth)",
    description=(
        "Returns only safe, public information about an event needed by "
        "the guest frontend. No authentication required. Returns 404 for "
        "an unknown slug."
    ),
)
def get_public_event(slug: str, db: Session = Depends(get_db)) -> PublicEventOut:
    event = event_service.get_event_by_slug(db, slug)
    return PublicEventOut.model_validate(event)
