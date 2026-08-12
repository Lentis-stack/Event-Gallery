# ============================================================
# Lentis Gallery — Host Event Routes
# ------------------------------------------------------------
# Endpoints for an Event HOST to access THEIR OWN events only:
#   - GET   /api/host/events              list my events
#   - GET   /api/host/events/{event_id}   view my event
#   - PATCH /api/host/events/{event_id}   update my event
#
# SECURITY: Every endpoint verifies ownership server-side.
# A host can ONLY ever see/update events where
#     event.host_id == current_user.id
# If someone else's event id is requested, we return 404 (not 403)
# so we do not reveal that the event exists.
#
# Hosts CANNOT:
#   - change event ownership (host_id)
#   - change status (LIVE/ENDED/ARCHIVED)
#   - archive events
# Those are admin-only actions.
# ============================================================

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_host
from app.db.session import get_db
from app.models.user import User
from app.schemas.event import EventOut, EventUpdate
from app.schemas.media import MediaListResponse, MediaOut
from app.services import events as event_service
from app.services import media as media_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/host/events", tags=["host-events"])


@router.get(
    "",
    response_model=list[EventOut],
    summary="List my events (host)",
    description="Returns ONLY the events owned by the authenticated host.",
)
def host_list_events(
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    return event_service.list_host_events(db, current_user.id)


@router.get(
    "/{event_id}",
    response_model=EventOut,
    summary="Get my event (host)",
    description=(
        "Returns one of the host's own events. If the event belongs to "
        "another host, returns 404 to avoid leaking its existence."
    ),
)
def host_get_event(
    event_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.get_host_event(db, current_user.id, event_id)


@router.patch(
    "/{event_id}",
    response_model=EventOut,
    summary="Update my event (host)",
    description=(
        "A host may update ONLY safe fields of their own event: name, "
        "subtitle, event_date, theme. Ownership (host_id) and status are "
        "admin-only and are ignored here. If the event belongs to another "
        "host, returns 404."
    ),
)
def host_update_event(
    event_id: str,
    body: EventUpdate,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.update_host_event(db, current_user.id, event_id, body)


# ============================================================
# GET /api/host/events/{event_id}/media  (host — owned event)
# ============================================================

@router.get(
    "/{event_id}/media",
    response_model=MediaListResponse,
    summary="List an event's media (host)",
    description=(
        "Returns media metadata for one of the host's OWN events. If the "
        "event belongs to another host, returns 404 (no existence leak). "
        "Only safe metadata is returned; internal storage keys are never "
        "exposed."
    ),
)
def host_list_event_media(
    event_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> MediaListResponse:
    items = media_service.get_host_event_media(db, current_user.id, event_id)
    return MediaListResponse(
        items=[MediaOut.model_validate(m) for m in items],
        total=len(items),
    )
