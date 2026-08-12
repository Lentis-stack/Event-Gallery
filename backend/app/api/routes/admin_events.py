# ============================================================
# Lentis Gallery — Admin Event Routes
# ------------------------------------------------------------
# Endpoints for the Lentis ADMIN to manage ALL events:
#   - GET   /api/admin/events              list all events
#   - GET   /api/admin/events/{event_id}   view one event
#   - PATCH /api/admin/events/{event_id}   update an event
#   - POST  /api/admin/events/{event_id}/archive  soft-archive
#
# Every endpoint here requires an ADMIN access token
# (require_admin). HOST users are rejected with 403.
# ============================================================

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.event import EventOut, EventUpdate
from app.schemas.media import MediaListResponse, MediaOut
from app.services import events as event_service
from app.services import media as media_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/events", tags=["admin-events"])


@router.get(
    "",
    response_model=list[EventOut],
    summary="List all events (admin only)",
    description="Returns every event across the platform, newest first.",
)
def admin_list_events(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    return event_service.list_events(db)


@router.get(
    "/{event_id}",
    response_model=EventOut,
    summary="Get one event (admin only)",
    description="Returns a single event by id. 404 if not found.",
)
def admin_get_event(
    event_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.get_event(db, event_id)


@router.patch(
    "/{event_id}",
    response_model=EventOut,
    summary="Update an event (admin only)",
    description=(
        "Updates allowed fields (name, subtitle, event_date, theme, host_id, "
        "status). If host_id changes, the new user must exist and have HOST "
        "role. Status transitions are validated (e.g. ENDED back to LIVE is "
        "not allowed)."
    ),
)
def admin_update_event(
    event_id: str,
    body: EventUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.update_event(db, event_id, body)


@router.post(
    "/{event_id}/archive",
    response_model=EventOut,
    status_code=status.HTTP_200_OK,
    summary="Archive an event (admin only)",
    description=(
        "Soft-archives an event: sets status to ARCHIVED and records "
        "archived_at. The row is NOT physically deleted."
    ),
)
def admin_archive_event(
    event_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.archive_event(db, event_id)


# ============================================================
# GET /api/admin/events/{event_id}/media  (admin — any event)
# ============================================================

@router.get(
    "/{event_id}/media",
    response_model=MediaListResponse,
    summary="List an event's media (admin)",
    description=(
        "Returns media metadata for any event (admin access). 404 if the "
        "event does not exist. Only safe metadata is returned; internal "
        "storage keys are never exposed."
    ),
)
def admin_list_event_media(
    event_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MediaListResponse:
    items = media_service.get_admin_event_media(db, event_id)
    return MediaListResponse(
        items=[MediaOut.model_validate(m) for m in items],
        total=len(items),
    )
