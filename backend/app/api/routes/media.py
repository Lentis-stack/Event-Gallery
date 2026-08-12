# ============================================================
# Lentis Gallery — Guest Media Routes
# ------------------------------------------------------------
# Endpoints for a GUEST to manage their own media:
#   - POST   /api/events/{slug}/media            upload media
#   - GET    /api/events/{slug}/media/me         list my media
#   - DELETE /api/events/{slug}/media/{media_id} delete my media
#   - GET    /api/events/{slug}/media/{id}/status processing status
#
# AUTHENTICATION:
#   Guests authenticate with the X-Guest-Token header (the opaque
#   session token from Phase 4). The backend derives the guest + event
#   from the session — it NEVER trusts event_id/guest_id from the body.
#
# EVENT ISOLATION:
#   A guest can only ever upload/list/delete media in THEIR event.
#   The get_authenticated_guest() helper enforces this server-side.
# ============================================================

import logging

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_optional_current_user
from app.db.session import get_db
from app.models.media import ProcessingStatus
from app.models.user import User
from app.schemas.media import (
    MediaListResponse,
    MediaOut,
    MediaProcessingStatusOut,
    MediaUploadResponse,
)
from app.services import media as media_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])

# Header guests use to present their session token (same as guests.py).
GUEST_TOKEN_HEADER = "X-Guest-Token"


class _Message(BaseModel):
    detail: str


def _require_token(token: str | None) -> None:
    """Raise 401 if no guest token was supplied."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest session token is required.",
        )


# ============================================================
# POST /api/events/{slug}/media  (guest upload)
# ============================================================

@router.post(
    "/api/events/{slug}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload media (guest)",
    description=(
        "Authenticated guest uploads a photo or video to a LIVE event. "
        "The file is validated by content (magic bytes) and size. The "
        "upload counts toward the event's server-side quota (3,000 photos "
        "/ 500 videos). Returns the created media metadata. Requires the "
        "guest session token in the X-Guest-Token header."
    ),
)
async def upload_media(
    slug: str,
    file: UploadFile = File(..., description="Photo (JPEG/PNG/WebP) or video (MP4/WebM/MOV)"),
    x_guest_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> MediaUploadResponse:
    _require_token(x_guest_token)

    # Read the file bytes (bounded by the app's max video size to
    # avoid unbounded memory use).
    data = await file.read()

    media = media_service.upload_media(
        db,
        slug=slug,
        raw_token=x_guest_token,
        filename=file.filename or "upload",
        data=data,
    )

    return MediaUploadResponse(
        id=media.id,
        media_type=media.media_type,
        status=media.status,
        processing_status=media.processing_status,
        original_filename=media.original_filename,
        file_size=media.file_size,
        created_at=media.created_at,
    )


# ============================================================
# GET /api/events/{slug}/media/me  (guest's own media)
# ============================================================

@router.get(
    "/api/events/{slug}/media/me",
    response_model=MediaListResponse,
    summary="List my media (guest)",
    description=(
        "Returns ONLY the media the current guest uploaded to the current "
        "event. Requires the guest session token in the X-Guest-Token header."
    ),
)
def list_my_media(
    slug: str,
    x_guest_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> MediaListResponse:
    _require_token(x_guest_token)
    items = media_service.list_my_media(db, slug, x_guest_token)
    return MediaListResponse(
        items=[MediaOut.model_validate(m) for m in items],
        total=len(items),
    )


# ============================================================
# DELETE /api/events/{slug}/media/{media_id}  (guest deletes own)
# ============================================================

@router.delete(
    "/api/events/{slug}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my media (guest)",
    description=(
        "Deletes a media item the current guest uploaded to the current "
        "event. Removes the object from storage and the metadata row. "
        "Returns 404 if the media does not belong to the current guest/event."
    ),
)
def delete_my_media(
    slug: str,
    media_id: str,
    x_guest_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _require_token(x_guest_token)
    media_service.delete_my_media(db, slug, x_guest_token, media_id)
    return None


# ============================================================
# GET /api/events/{slug}/media/{media_id}/status  (processing)
# ============================================================
# Phase 6: lets an authorized caller poll the async processing
# state of a media item. Supports three credential styles:
#   - guest token (X-Guest-Token)  -> only their own media
#   - host bearer token            -> only their own event's media
#   - admin bearer token           -> any event's media
# Event isolation is enforced server-side (404 on any mismatch).

@router.get(
    "/api/events/{slug}/media/{media_id}/status",
    response_model=MediaProcessingStatusOut,
    summary="Get media processing status",
    description=(
        "Returns the async processing state of a media item plus which "
        "derived variants (original/optimized/thumbnail/poster) exist. "
        "Authorized for the owning guest (X-Guest-Token), the event's host "
        "(Bearer), or an admin (Bearer). Enforces strict event isolation; "
        "404 if the caller has no access."
    ),
)
def get_media_processing_status(
    slug: str,
    media_id: str,
    x_guest_token: str | None = Header(default=None),
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> MediaProcessingStatusOut:
    # If a valid Bearer token was supplied, `user` is a host or admin.
    # Otherwise it is None and we fall back to the guest token.
    host = None
    admin = None
    if user is not None:
        if user.role.value == "ADMIN":
            admin = user
        else:
            host = user

    media = media_service.get_processing_status(
        db,
        slug=slug,
        media_id=media_id,
        raw_token=x_guest_token,
        host=host,
        admin=admin,
    )
    return MediaProcessingStatusOut(
        media_id=media.id,
        event_id=media.event_id,
        status=media.processing_status,
        original=True,
        optimized=media.optimized,
        thumbnail=media.thumbnail,
        poster=media.poster,
        processing_error=media.processing_error,
        processing_attempts=media.processing_attempts,
        processed_at=media.processed_at,
    )
