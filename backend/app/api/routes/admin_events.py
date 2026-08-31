# ============================================================
# Lentis Gallery — Admin Event Routes
# ------------------------------------------------------------
# Endpoints for the Lentis ADMIN to manage ALL events:
#   - GET   /api/admin/events              list all events
#   - GET   /api/admin/events/{event_id}   view one event
#   - PATCH /api/admin/events/{event_id}   update an event
#   - POST  /api/admin/events/{event_id}/archive  soft-archive
#   - POST  /api/admin/events/{event_id}/media    upload media
#
# Every endpoint here requires an ADMIN access token
# (require_admin). HOST users are rejected with 403.
# ============================================================

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.event import EventOut, EventUpdate
from app.schemas.media import MediaListResponse, MediaOut, MediaRoleUpdate, MediaReorderRequest, MediaUploadResponse
from app.services import events as event_service
from app.services import media as media_service
from app.models.media import Media, MediaPage, MediaRole, MediaSource

logger = logging.getLogger(__name__)


def _media_to_out(m: Media) -> MediaOut:
    """Convert Media ORM object to MediaOut with media_url for display."""
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
    )

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
    # SEC-021: Pass admin_user_id for audit logging on host reassignment.
    return event_service.update_event(db, event_id, body, admin_user_id=_admin.id)


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


@router.post(
    "/{event_id}/restore",
    response_model=EventOut,
    status_code=status.HTTP_200_OK,
    summary="Restore an archived event (admin only)",
    description=(
        "Restores an archived event: sets status to CREATED and clears "
        "archived_at. The event returns to the active event list."
    ),
)
def admin_restore_event(
    event_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.restore_event(db, event_id)


# ============================================================
# DELETE /api/admin/events/{event_id}  (admin — soft-delete)
# ============================================================

@router.delete(
    "/{event_id}",
    response_model=EventOut,
    status_code=status.HTTP_200_OK,
    summary="Delete event (admin — soft-delete)",
    description=(
        "Soft-deletes an event: sets status to ARCHIVED and records "
        "archived_at. The row is NOT physically deleted. Use the "
        "/permanent endpoint for irreversible deletion."
    ),
)
def admin_delete_event(
    event_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EventOut:
    return event_service.archive_event(db, event_id)


# ============================================================
# DELETE /api/admin/events/{event_id}/permanent  (admin — irreversible)
# ============================================================

@router.delete(
    "/{event_id}/permanent",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete event (admin — irreversible)",
    description=(
        "Permanently deletes an event and all associated data "
        "(media, guests). This operation is irreversible."
    ),
)
def admin_permanent_delete_event(
    event_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event_service.permanent_delete_event(db, event_id)
    return None


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
        items=[_media_to_out(m) for m in items],
        total=len(items),
    )


# ============================================================
# POST /api/admin/events/{event_id}/media  (admin upload)
# ============================================================

@router.post(
    "/{event_id}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload media to event (admin)",
    description=(
        "Admin uploads a photo or video directly to an event. "
        "No guest session required. The file is validated by content "
        "(magic bytes) and size. Returns the created media metadata."
    ),
)
async def admin_upload_event_media(
    event_id: str,
    file: UploadFile = File(..., description="Photo or video file"),
    media_role: str = Form("GALLERY"),
    source: str = Form("ADMIN"),
    page: str | None = Form(None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MediaUploadResponse:
    data = await file.read()
    role = MediaRole(media_role.upper()) if media_role.upper() in [r.value for r in MediaRole] else MediaRole.GALLERY
    src = MediaSource(source.upper()) if source.upper() in [s.value for s in MediaSource] else MediaSource.ADMIN
    pg = MediaPage(page.upper()) if page and page.upper() in [p.value for p in MediaPage] else None
    media = media_service.admin_upload_media(
        db,
        event_id=event_id,
        filename=file.filename or "upload",
        data=data,
        media_role=role,
        source=src,
        page=pg,
    )
    return MediaUploadResponse(
        id=media.id,
        media_type=media.media_type,
        media_role=media.media_role,
        position=media.position,
        source=media.source,
        page=media.page,
        status=media.status,
        processing_status=media.processing_status,
        original_filename=media.original_filename,
        file_size=media.file_size,
        created_at=media.created_at,
    )


# ============================================================
# DELETE /api/admin/events/{event_id}/media/{media_id}  (admin)
# ============================================================

@router.delete(
    "/{event_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete media (admin)",
    description="Deletes a media item from an event. Removes from storage and database.",
)
def admin_delete_event_media(
    event_id: str,
    media_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    media_service.admin_delete_media(db, event_id, media_id)
    return None


# ============================================================
# PATCH /api/admin/events/{event_id}/media/{media_id}/role  (admin)
# ============================================================

@router.patch(
    "/{event_id}/media/{media_id}/role",
    response_model=MediaOut,
    summary="Set media role (admin)",
    description="Changes a media item's role (hero/slideshow/gallery).",
)
def admin_set_media_role(
    event_id: str,
    media_id: str,
    body: MediaRoleUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MediaOut:
    media = media_service.admin_set_media_role(db, event_id, media_id, body.media_role, body.page)
    return _media_to_out(media)


# ============================================================
# POST /api/admin/events/{event_id}/media/reorder  (admin)
# ============================================================

@router.post(
    "/{event_id}/media/reorder",
    status_code=status.HTTP_200_OK,
    summary="Reorder slideshow media (admin)",
    description="Reorders slideshow images. Pass the ordered list of media IDs.",
)
def admin_reorder_media(
    event_id: str,
    body: MediaReorderRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    media_service.admin_reorder_slideshow(db, event_id, body.ordered_ids)
    return {"detail": "Slideshow reordered."}
