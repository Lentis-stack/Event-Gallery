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

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.dependencies import require_host
from app.db.session import get_db
from app.models.user import User
from app.schemas.event import EventOut, EventUpdate
from app.schemas.media import MediaListResponse, MediaOut, HostOverviewStats, RecentMemory
from app.services import events as event_service
from app.services import media as media_service
from app.models.media import Media, MediaPage, MediaRole, MediaSource, MediaStatus, MediaType, ModerationStatus
from app.models.guest import Guest
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BulkApproveResponse(BaseModel):
    approved_count: int


def _media_to_out(m: Media, db: Session) -> MediaOut:
    """Convert Media ORM object to MediaOut with media_url for display."""
    guest = db.get(Guest, m.guest_id) if m.guest_id else None
    return MediaOut(
        id=m.id,
        event_id=m.event_id,
        media_type=m.media_type,
        media_role=m.media_role,
        position=m.position,
        source=m.source,
        page=m.page,
        mime_type=m.mime_type,
        original_filename=m.original_filename,
        file_size=m.file_size,
        status=m.status,
        processing_status=m.processing_status,
        optimized=m.optimized or False,
        thumbnail=m.thumbnail or False,
        poster=m.poster or False,
        media_url=f"/api/media/{m.thumbnail_key or m.optimized_key or m.storage_key}" if m.storage_key else None,
        created_at=m.created_at,
        guest_name=guest.name if guest else None,
        moderation_status=m.moderation_status,
    )

router = APIRouter(prefix="/api/host/events", tags=["host-events"])


@router.post(
    "/{event_id}/start",
    response_model=EventOut,
    summary="Start event (host)",
    description=(
        "Host starts their own event: changes status from CREATED to LIVE. "
        "Only the event's owner host can start it."
    ),
)
def host_start_event(
    event_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.host_start_event(db, current_user.id, event_id)


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
    media_role: str | None = None,
    page: str | None = None,
) -> MediaListResponse:
    items = media_service.get_host_event_media(db, current_user.id, event_id)
    # Filter by media_role and page if provided
    if media_role:
        try:
            role_enum = MediaRole(media_role)
            items = [m for m in items if m.media_role == role_enum]
        except ValueError:
            pass
    if page:
        try:
            page_enum = MediaPage(page)
            items = [m for m in items if m.page == page_enum]
        except ValueError:
            pass
    return MediaListResponse(
        items=[_media_to_out(m, db) for m in items],
        total=len(items),
    )


# ============================================================
# POST /api/host/events/{event_id}/media  (host upload)
# ============================================================

@router.post(
    "/{event_id}/media",
    response_model=MediaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload media to my event (host)",
    description=(
        "Host uploads presentation media (hero, slideshow, etc.) to their "
        "own event. Accepts multipart form with 'file', 'media_role', "
        "optional 'page', and 'source' fields."
    ),
)
async def host_upload_event_media(
    event_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    media_role: str = Form(default="GALLERY"),
    source: str = Form(default="ADMIN"),
    page: str | None = Form(default=None),
) -> MediaOut:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    media = media_service.host_upload_media(
        db=db,
        host_id=current_user.id,
        event_id=event_id,
        filename=file.filename or "upload",
        data=data,
        media_role=MediaRole(media_role),
        source=MediaSource(source),
        page=MediaPage(page) if page else None,
    )
    return _media_to_out(media, db)


# ============================================================
# PATCH /api/host/events/{event_id}/media/{media_id}/role
# ============================================================

@router.patch(
    "/{event_id}/media/{media_id}/role",
    response_model=MediaOut,
    summary="Update media role/page (host)",
    description=(
        "Host reassigns a media item's role and page within their own event."
    ),
)
def host_update_media_role(
    event_id: str,
    media_id: str,
    body: dict,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> MediaOut:
    media_role = body.get("media_role", "GALLERY")
    page = body.get("page")
    media = media_service.host_set_media_role(
        db=db,
        host_id=current_user.id,
        event_id=event_id,
        media_id=media_id,
        new_role=MediaRole(media_role),
        page=MediaPage(page) if page else None,
    )
    return _media_to_out(media, db)


# ============================================================
# POST /api/host/events/{event_id}/media/{media_id}/approve
# ============================================================

@router.post(
    "/{event_id}/media/{media_id}/approve",
    response_model=MediaOut,
    summary="Approve guest media (host)",
    description="Approves a guest's media upload. Makes it visible in the public gallery.",
)
def host_approve_event_media(
    event_id: str,
    media_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> MediaOut:
    media = media_service.host_approve_media(db, current_user.id, event_id, media_id)
    return _media_to_out(media, db)


# ============================================================
# POST /api/host/events/{event_id}/media/{media_id}/reject
# ============================================================

@router.post(
    "/{event_id}/media/{media_id}/reject",
    response_model=MediaOut,
    summary="Reject guest media (host)",
    description="Rejects a guest's media upload. Hides it from the public gallery.",
)
def host_reject_event_media(
    event_id: str,
    media_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> MediaOut:
    media = media_service.host_reject_media(db, current_user.id, event_id, media_id)
    return _media_to_out(media, db)


# POST /api/host/events/{event_id}/media/{media_id}/hide
# ============================================================

@router.post(
    "/{event_id}/media/{media_id}/hide",
    response_model=MediaOut,
    summary="Hide approved guest media (host)",
    description="Hides approved guest media from the public gallery. The media becomes HIDDEN but can be restored.",
)
def host_hide_event_media(
    event_id: str,
    media_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> MediaOut:
    media = media_service.host_hide_media(db, current_user.id, event_id, media_id)
    return _media_to_out(media, db)


# POST /api/host/events/{event_id}/media/{media_id}/unhide
# ============================================================

@router.post(
    "/{event_id}/media/{media_id}/unhide",
    response_model=MediaOut,
    summary="Restore hidden guest media (host)",
    description="Restores hidden guest media to the public gallery.",
)
def host_unhide_event_media(
    event_id: str,
    media_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> MediaOut:
    media = media_service.host_unhide_media(db, current_user.id, event_id, media_id)
    return _media_to_out(media, db)



# ============================================================
# DELETE /api/host/events/{event_id}/media/{media_id}
# ============================================================

@router.delete(
    "/{event_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete media (host)",
    description="Deletes any media from the host's own event.",
)
def host_delete_event_media(
    event_id: str,
    media_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
):
    media_service.host_delete_media(db, current_user.id, event_id, media_id)
    return None


# ============================================================
# GET /api/host/events/{event_id}/slideshow  (host — owned event)
# ============================================================
# Returns host-slideshow media for the host console slideshow page.

@router.get(
    "/{event_id}/slideshow",
    summary="Get host slideshow media (host)",
    description="Returns HOST_SLIDESHOW media for the host's own event.",
)
def host_get_slideshow(
    event_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> list[dict]:
    event = event_service.get_host_event(db, current_user.id, event_id)
    items = list(
        db.scalars(
            select(Media).where(
                Media.event_id == event.id,
                Media.media_role == MediaRole.HOST_SLIDESHOW,
                Media.media_type == MediaType.PHOTO,
                Media.source == MediaSource.ADMIN,
                Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            ).order_by(Media.position.asc().nullslast(), Media.created_at.asc())
        )
    )
    return [
        {
            "src": f"/api/media/{m.thumbnail_key or m.optimized_key or m.storage_key}",
            "alt": m.original_filename,
            "id": m.id,
        }
        for m in items
    ]


@router.post(
    "/{event_id}/media/approve-all",
    response_model=BulkApproveResponse,
    summary="Approve all pending guest media (host)",
    description=(
        "Approves all pending guest media uploads for the host's event. "
        "Only affects guest-uploaded media with PENDING status. "
        "Returns the count of approved items."
    ),
)
def host_approve_all_media(
    event_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> BulkApproveResponse:
    approved_count = media_service.host_approve_all_media(db, current_user.id, event_id)
    return BulkApproveResponse(approved_count=approved_count)


@router.get(
    "/{event_id}/overview",
    response_model=HostOverviewStats,
    summary="Get host overview statistics (host)",
    description="Returns real media statistics and recent memories for the host's event.",
)
def host_get_overview(
    event_id: str,
    current_user: User = Depends(require_host),
    db: Session = Depends(get_db),
) -> HostOverviewStats:
    event = event_service.get_host_event(db, current_user.id, event_id)
    from app.services import media as media_service
    from sqlalchemy import func
    
    # Count guest uploads only (not admin media)
    photo_count = db.scalar(
        select(func.count(Media.id)).where(
            Media.event_id == event.id,
            Media.source == MediaSource.GUEST,
            Media.media_type == MediaType.PHOTO,
        )
    ) or 0
    video_count = db.scalar(
        select(func.count(Media.id)).where(
            Media.event_id == event.id,
            Media.source == MediaSource.GUEST,
            Media.media_type == MediaType.VIDEO,
        )
    ) or 0
    total_uploads = photo_count + video_count
    
    storage_bytes = event.storage_used_bytes or 0
    
    contributing_guests = db.scalar(
        select(func.count(func.distinct(Media.guest_id))).where(
            Media.event_id == event.id,
            Media.source == MediaSource.GUEST,
        )
    ) or 0
    
    # Get recent memories (guest media, newest first)
    recent_media = list(db.scalars(
        select(Media).where(
            Media.event_id == event.id,
            Media.source == MediaSource.GUEST,
        ).order_by(Media.created_at.desc()).limit(6)
    ))
    
    recent_memories = []
    for m in recent_media:
        guest = db.get(Guest, m.guest_id) if m.guest_id else None
        recent_memories.append(RecentMemory(
            id=m.id,
            media_url=f"/api/media/{m.thumbnail_key or m.optimized_key or m.storage_key}" if m.storage_key else None,
            media_type=m.media_type,
            guest_name=guest.name if guest else "Guest",
            created_at=m.created_at,
        ))
    
    return HostOverviewStats(
        total_uploads=total_uploads,
        photos=photo_count,
        videos=video_count,
        storage_bytes=storage_bytes,
        contributing_guests=contributing_guests,
        recent_memories=recent_memories,
    )
