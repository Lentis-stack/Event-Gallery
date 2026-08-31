# ============================================================
# Lentis Gallery — Events Routes
# ------------------------------------------------------------
# Endpoints:
#   - POST /api/events                     (ADMIN only — create)
#   - GET  /api/events/{slug}/public       (PUBLIC — guest lookup)
#   - GET  /api/events/{event_id}/stats    (ADMIN/HOST — real stats)
#   - GET  /api/media/{key:path}           (PUBLIC — serve media)
#
# ============================================================

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, require_admin
from app.db.session import get_db
from app.models.event import Event, EventStatus
from app.models.media import Media, MediaPage, MediaRole, MediaSource, MediaType, MediaStatus, ModerationStatus
from app.models.user import User
from app.schemas.event import EventCreate, EventOut, PublicEventOut
from app.services import events as event_service
from app.storage import get_storage_service

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
    if event.status == EventStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Event not found.")
    # CREATED events are visible (guests can register before event starts)
    return PublicEventOut.model_validate(event)


# ============================================================
# Helper: choose the best public URL for a media record
# ============================================================
# Priority: thumbnail (small/fast) for grids, optimized for full,
# original as final fallback. Never exposes storage keys directly.
# ============================================================

def _best_media_url(m: Media, *, prefer_full: bool = False) -> str:
    """Return the best public URL for a media record.
    prefer_full=True  -> optimized (display-ready)
    prefer_full=False -> thumbnail (grid/preview, faster loading)
    """
    if prefer_full:
        key = m.optimized_key or m.thumbnail_key or m.storage_key
    else:
        key = m.thumbnail_key or m.optimized_key or m.storage_key
    return f"/api/media/{key}"


def _best_full_url(m: Media) -> str:
    """Full-size URL (optimized > original)."""
    key = m.optimized_key or m.storage_key
    return f"/api/media/{key}"


# ============================================================
# GET /api/events/{event_id}/public-media  (PUBLIC)
# ============================================================
# Returns the public media (slideshow + hero images) for an event.
# Gallery is paginated; hero + slideshow are small and immediate.

GALLERY_PAGE_SIZE = 50

def _encode_cursor(created_at: str, media_id: str) -> str:
    """Create a simple opaque cursor from timestamp + id."""
    import base64
    return base64.urlsafe_b64encode(f"{created_at}|{media_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, str]:
    """Decode cursor back to (created_at, media_id)."""
    import base64
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts, mid = raw.rsplit("|", 1)
    return ts, mid


@router.get(
    "/api/events/{slug}/public-media",
    summary="Get event public media (no auth)",
    description=(
        "Returns approved media URLs for an event's public display. "
        "Hero + slideshow are always returned in full. Gallery is "
        "paginated with cursor-based navigation."
    ),
)
def get_public_event_media(
    slug: str,
    gallery_cursor: str | None = None,
    gallery_limit: int = GALLERY_PAGE_SIZE,
    db: Session = Depends(get_db),
) -> dict:
    event = event_service.get_event_by_slug(db, slug)

    # Don't serve media for archived events (CREATED and LIVE are ok)
    if event.status == EventStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Event not found.")

    # Clamp limit
    gallery_limit = min(max(gallery_limit, 1), 200)

    # --- Hero images (multiple, admin-uploaded only) ---
    hero_items = list(
        db.scalars(
            select(Media).where(
                Media.event_id == event.id,
                Media.media_role == MediaRole.HERO,
                Media.media_type == MediaType.PHOTO,
                Media.source == MediaSource.ADMIN,
                Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            ).order_by(Media.position.asc().nullslast(), Media.created_at.asc())
        )
    )
    hero_data = [
        {
            "src": _best_media_url(m, prefer_full=True),
            "alt": m.original_filename,
            "id": m.id,
        }
        for m in hero_items
    ]

    # --- Landing slideshow images (admin-uploaded, page=LANDING) ---
    slideshow_items = list(
        db.scalars(
            select(Media).where(
                Media.event_id == event.id,
                Media.media_role == MediaRole.SLIDESHOW,
                Media.media_type == MediaType.PHOTO,
                Media.source == MediaSource.ADMIN,
                Media.page == MediaPage.LANDING,
                Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            ).order_by(Media.position.asc().nullslast(), Media.created_at.asc())
        )
    )
    slideshow = []
    for m in slideshow_items:
        slideshow.append({
            "src": _best_media_url(m, prefer_full=True),
            "alt": m.original_filename,
            "id": m.id,
        })

    # --- Guest slideshow (for guest page) ---
    guest_slideshow_items = list(
        db.scalars(
            select(Media).where(
                Media.event_id == event.id,
                Media.media_role == MediaRole.SLIDESHOW,
                Media.media_type == MediaType.PHOTO,
                Media.source == MediaSource.ADMIN,
                Media.page == MediaPage.GUEST,
                Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            ).order_by(Media.position.asc().nullslast(), Media.created_at.asc())
        )
    )
    guest_slideshow = []
    for m in guest_slideshow_items:
        guest_slideshow.append({
            "src": _best_media_url(m, prefer_full=True),
            "alt": m.original_filename,
            "id": m.id,
        })

    # --- Camera slideshow (for camera page) ---
    camera_slideshow_items = list(
        db.scalars(
            select(Media).where(
                Media.event_id == event.id,
                Media.media_role == MediaRole.SLIDESHOW,
                Media.media_type == MediaType.PHOTO,
                Media.source == MediaSource.ADMIN,
                Media.page == MediaPage.CAMERA,
                Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            ).order_by(Media.position.asc().nullslast(), Media.created_at.asc())
        )
    )
    camera_slideshow = []
    for m in camera_slideshow_items:
        camera_slideshow.append({
            "src": _best_media_url(m, prefer_full=True),
            "alt": m.original_filename,
            "id": m.id,
        })

    # --- Gallery images (paginated, cursor-based) ---
    # Gallery includes BOTH admin-uploaded and guest-approved media
    gallery_query = (
        select(Media).where(
            Media.event_id == event.id,
            Media.media_role == MediaRole.GALLERY,
            Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            Media.moderation_status == ModerationStatus.VISIBLE,
        ).order_by(Media.created_at.desc(), Media.id.desc())
    )

    # Apply cursor for pagination
    if gallery_cursor:
        try:
            cursor_ts, cursor_id = _decode_cursor(gallery_cursor)
            from datetime import datetime as dt
            cursor_dt = dt.fromisoformat(cursor_ts)
            gallery_query = gallery_query.where(
                (Media.created_at < cursor_dt)
                | ((Media.created_at == cursor_dt) & (Media.id < cursor_id))
            )
        except Exception:
            pass  # Invalid cursor — ignore and return first page

    # Fetch one extra to detect if there's a next page
    gallery_items = list(db.scalars(gallery_query.limit(gallery_limit + 1)))
    has_next = len(gallery_items) > gallery_limit
    gallery_items = gallery_items[:gallery_limit]

    gallery = []
    for m in gallery_items:
        gallery.append({
            "src": _best_media_url(m, prefer_full=False),
            "alt": m.original_filename,
            "id": m.id,
            "full_src": _best_full_url(m),
            "media_type": m.media_type.value,
        })

    next_cursor = None
    if has_next and gallery_items:
        last = gallery_items[-1]
        next_cursor = _encode_cursor(last.created_at.isoformat(), last.id)

    # Total gallery count for progress indication (lightweight query)
    gallery_total = db.scalar(
        select(func.count(Media.id)).where(
            Media.event_id == event.id,
            Media.media_role == MediaRole.GALLERY,
            Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            Media.moderation_status == ModerationStatus.VISIBLE,
        )
    ) or 0

    return {
        "hero": hero_data,
        "slideshow": slideshow,
        "guest_slideshow": guest_slideshow,
        "camera_slideshow": camera_slideshow,
        "gallery": gallery,
        "gallery_total": gallery_total,
        "next_cursor": next_cursor,
        "images": hero_data + slideshow,  # backward compat: all admin design media
    }


# ============================================================
# GET /api/events/{slug}/host-slideshow  (PUBLIC)
# ============================================================
# Returns host slideshow media (HOST_SLIDESHOW / HOST) for an event.
# Used by the Host login page and other public host-facing pages.
# ============================================================

@router.get(
    "/api/events/{slug}/host-slideshow",
    summary="Get host slideshow media (public)",
    description="Returns HOST_SLIDESHOW media for an event. No authentication required.",
)
def get_public_host_slideshow(
    slug: str,
    db: Session = Depends(get_db),
) -> list[dict]:
    event = event_service.get_event_by_slug(db, slug)
    
    # Don't serve media for archived events
    if event.status == EventStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Event not found.")
    
    items = list(
        db.scalars(
            select(Media).where(
                Media.event_id == event.id,
                Media.media_role == MediaRole.HOST_SLIDESHOW,
                Media.media_type == MediaType.PHOTO,
                Media.source == MediaSource.ADMIN,
                Media.page == MediaPage.HOST,
                Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
            ).order_by(Media.position.asc().nullslast(), Media.created_at.asc())
        )
    )
    
    return [
        {
            "src": _best_media_url(m, prefer_full=True),
            "alt": m.original_filename,
            "id": m.id,
        }
        for m in items
    ]


# ============================================================
# GET /api/events/{slug}/gallery  (PUBLIC — paginated)
# ============================================================
# Dedicated gallery endpoint for infinite-scroll / lazy loading.
# Returns only gallery-role media (excludes hero/slideshow from
# the paginated set to avoid duplication).

def get_public_gallery(
    slug: str,
    cursor: str | None = None,
    limit: int = GALLERY_PAGE_SIZE,
    media_type: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    Paginated public gallery for an event. Supports:
    - cursor-based pagination (next_cursor in response)
    - optional media_type filter (PHOTO / VIDEO)
    - returns thumbnail URLs for grid display
    """
    event = event_service.get_event_by_slug(db, slug)
    limit = min(max(limit, 1), 200)

    base_filters = [
        Media.event_id == event.id,
        Media.media_role == MediaRole.GALLERY,
        Media.status.in_([MediaStatus.UPLOADED, MediaStatus.APPROVED]),
        Media.moderation_status == ModerationStatus.VISIBLE,
    ]
    if media_type and media_type.upper() in ('PHOTO', 'VIDEO'):
        base_filters.append(Media.media_type == MediaType(media_type.upper()))

    query = select(Media).where(*base_filters).order_by(
        Media.created_at.desc(), Media.id.desc()
    )

    if cursor:
        try:
            cursor_ts, cursor_id = _decode_cursor(cursor)
            from datetime import datetime as dt
            cursor_dt = dt.fromisoformat(cursor_ts)
            query = query.where(
                (Media.created_at < cursor_dt)
                | ((Media.created_at == cursor_dt) & (Media.id < cursor_id))
            )
        except Exception:
            pass

    items = list(db.scalars(query.limit(limit + 1)))
    has_next = len(items) > limit
    items = items[:limit]

    results = []
    for m in items:
        results.append({
            "id": m.id,
            "src": _best_media_url(m, prefer_full=False),
            "full_src": _best_full_url(m),
            "alt": m.original_filename,
            "media_type": m.media_type.value,
            "width": m.thumbnail_width or m.width,
            "height": m.thumbnail_height or m.height,
            "file_size": m.file_size,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    next_cursor = None
    if has_next and items:
        last = items[-1]
        next_cursor = _encode_cursor(last.created_at.isoformat(), last.id)

    total = db.scalar(select(func.count(Media.id)).where(*base_filters)) or 0

    return {
        "items": results,
        "total": total,
        "next_cursor": next_cursor,
    }


# Register the gallery endpoint
@router.get(
    "/api/events/{slug}/gallery",
    summary="Get event gallery (paginated, public)",
    description="Returns paginated gallery media with cursor-based navigation.",
)
def get_public_gallery_route(
    slug: str,
    cursor: str | None = None,
    limit: int = GALLERY_PAGE_SIZE,
    media_type: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return get_public_gallery(slug, cursor, limit, media_type, db)


# ============================================================
# GET /api/events/{event_id}/stats  (ADMIN/HOST)
# ============================================================
# Returns real-time statistics for an event.

@router.get(
    "/api/events/{event_id}/stats",
    summary="Get event statistics",
    description="Returns real-time stats: photo count, video count, storage used, etc.",
)
def get_event_stats(
    event_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    # Real counts from the database — only guest-uploaded media
    photo_count = db.scalar(
        select(func.count(Media.id)).where(
            Media.event_id == event_id,
            Media.media_type == MediaType.PHOTO,
            Media.source == MediaSource.GUEST,
        )
    ) or 0
    video_count = db.scalar(
        select(func.count(Media.id)).where(
            Media.event_id == event_id,
            Media.media_type == MediaType.VIDEO,
            Media.source == MediaSource.GUEST,
        )
    ) or 0
    total_uploads = photo_count + video_count

    # Storage used (tracked on the event row)
    storage_used_bytes = event.storage_used_bytes or 0
    storage_used_mb = round(storage_used_bytes / (1024 * 1024), 1)
    storage_used_gb = round(storage_used_bytes / (1024 * 1024 * 1024), 2)

    # Unique contributors (distinct guest_ids that uploaded media)
    from app.models.guest import Guest
    contributor_count = db.scalar(
        select(func.count(func.distinct(Media.guest_id))).where(
            Media.event_id == event_id,
            Media.source == MediaSource.GUEST,
        )
    ) or 0

    return {
        "event_id": event_id,
        "photo_count": photo_count,
        "video_count": video_count,
        "total_uploads": total_uploads,
        "contributor_count": contributor_count,
        "storage_used_bytes": storage_used_bytes,
        "storage_used_mb": storage_used_mb,
        "storage_used_gb": storage_used_gb,
        "storage_limit_gb": event.storage_limit_gb,
    }


# ============================================================
# GET /api/media/{key:path}  (PUBLIC — serve stored media)
# ============================================================
# Serves media files from the configured storage provider.
# For local storage: serves files from disk.
# For R2: generates a signed URL (or redirects).
# SECURITY: Only serves files under the events/ prefix.

# Content-type mapping for media serving
_CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}

# Cache TTL for immutable processed media (optimized/thumbnail/poster)
# These files never change once created, so long caching is safe.
_IMMUTABLE_CACHE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year
_ORIGINAL_CACHE_MAX_AGE = 60 * 60 * 24 * 7       # 1 week


@router.get(
    "/api/media/{key:path}",
    summary="Serve a media file",
    description="Serves media files from object storage. Only event media keys are allowed.",
)
def serve_media(key: str, request: Request):
    # Security: only allow keys under events/ prefix
    if not key.startswith("events/"):
        raise HTTPException(status_code=403, detail="Access denied.")

    # Determine cache policy: processed variants are immutable,
    # originals may be replaced during processing.
    is_processed = any(
        variant in key for variant in ("/optimized", "/thumbnail", "/poster")
    )
    cache_max_age = _IMMUTABLE_CACHE_MAX_AGE if is_processed else _ORIGINAL_CACHE_MAX_AGE
    cache_headers = {
        "Cache-Control": f"public, max-age={cache_max_age}, immutable" if is_processed
                         else f"public, max-age={cache_max_age}",
    }

    # For local storage, serve directly from the file system
    storage_provider = settings.STORAGE_PROVIDER or "local"
    if storage_provider == "local":
        base_path = Path(settings.LOCAL_STORAGE_PATH).resolve()
        file_path = (base_path / key).resolve()
        # Prevent path traversal
        if not str(file_path).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="Access denied.")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Media not found.")
        # Determine content type from extension
        ext = file_path.suffix.lower()
        content_type = _CONTENT_TYPE_MAP.get(ext, "application/octet-stream")
        return FileResponse(
            str(file_path),
            media_type=content_type,
            headers=cache_headers,
        )

    # For R2, proxy the content through the backend (stable URLs)
    try:
        import boto3
        from botocore.config import Config as BotoConfig

        if not (settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_ENDPOINT):
            raise HTTPException(status_code=500, detail="Storage not configured.")

        client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=BotoConfig(signature_version="s3v4"),
        )
        obj = client.get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
        content = obj["Body"].read()
        content_type = obj.get("ContentType", "application/octet-stream")
        from fastapi.responses import Response
        return Response(content=content, media_type=content_type, headers=cache_headers)
    except Exception as e:
        logger.error("Failed to proxy R2 media for %s: %s", key, e)
        raise HTTPException(status_code=500, detail="Failed to serve media.")
