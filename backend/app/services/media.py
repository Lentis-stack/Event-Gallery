# ============================================================
# Lentis Gallery — Media Service
# ------------------------------------------------------------
# Business logic for media upload, listing, deletion, quotas, and
# authorization. Routes stay THIN and call these functions.
#
#     Route  -->  MediaService  -->  Database + Object Storage
#
# WHAT LIVES HERE (the real rules):
#   * Guest session authentication (reuses guests service).
#   * Event must be LIVE before uploads are accepted.
#   * File is validated by CONTENT (magic bytes) + size from config.
#   * Quotas (3,000 photos / 500 videos) enforced SERVER-SIDE.
#   * The DB is the authority for counts — never trust the client.
#   * Metadata is written to the DB; bytes go to object storage.
#   * Event isolation: a guest can only touch media in their own
#     event; a host only their own events; admins broader.
#
# TRANSACTION / STORAGE CONSISTENCY:
#   We use a careful order so we never leave a broken record:
#     1. Validate everything (guest, event, file, quota).
#     2. Create the Media row (commit) — status UPLOADED.
#     3. Upload the bytes to object storage.
#     4. If the storage upload FAILS, we delete the metadata row so
#        we don't leave a record that claims a file exists.
#   (The reverse case — storage succeeds but the DB commit happens
#   after — is handled by writing the DB row BEFORE storage, so a
#   DB failure means storage is never attempted and no orphan
#   object is created. This is the simplest reliable order.)
# ============================================================

import hashlib
import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event, EventStatus
from app.models.guest import Guest
from app.models.media import Media, MediaStatus, MediaType
from app.models.user import User
from app.schemas.media import MediaQuota
from app.storage import StorageService, get_storage_service
from app.services import guests as guest_service
from app.utils.file_validation import detect_file_type, sanitize_filename

logger = logging.getLogger(__name__)

# Map our validated media category to the MediaType enum.
_TYPE_MAP = {
    "photo": MediaType.PHOTO,
    "video": MediaType.VIDEO,
}


# ============================================================
# Storage key generation
# ============================================================

def _build_storage_key(event_id: str, media_id: str, media_type: MediaType) -> str:
    """
    Build a safe, unpredictable object-storage key.
      events/{event_id}/media/{media_id}/original
    The media_id is a random UUID, so no two objects collide and a
    user cannot guess another object's path. The ORIGINAL file goes
    under 'original'; Phase 6 will add 'optimized' and 'thumbnail'
    siblings WITHOUT changing this scheme.
    """
    return f"events/{event_id}/media/{media_id}/original"


# ============================================================
# Quota helpers (server-side, concurrency-safe)
# ============================================================

def _count_media(db: Session, event_id: str, media_type: MediaType) -> int:
    """Count an event's media of a given type."""
    return db.scalar(
        select(func.count(Media.id)).where(
            Media.event_id == event_id,
            Media.media_type == media_type,
        )
    ) or 0


def _quota_limit(media_type: MediaType) -> int:
    """Return the configured limit for a media type."""
    if media_type == MediaType.PHOTO:
        return settings.MAX_PHOTOS_PER_EVENT
    return settings.MAX_VIDEOS_PER_EVENT


def _check_quota(db: Session, event_id: str, media_type: MediaType) -> None:
    """
    Reject an upload if the event has reached its limit for the type.
    To keep concurrent uploads from racing past the cap, we take a
    ROW LOCK on the event row (SELECT ... FOR UPDATE) within the same
    transaction as the count. That serializes two simultaneous
    uploads to the SAME event so the second one sees the first's new
    row and is correctly rejected once the cap is hit.
    """
    # Lock the event row for this transaction (FOR UPDATE). This is
    # what prevents two concurrent uploads from both counting 2,999
    # and both passing. On SQLite (tests) this is a no-op, but the
    # count is still correct per-request.
    db.execute(
        select(Event).where(Event.id == event_id).with_for_update()
    )

    count = _count_media(db, event_id, media_type)
    limit = _quota_limit(media_type)

    if count >= limit:
        kind = "photos" if media_type == MediaType.PHOTO else "videos"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This event has reached its {kind} limit of {limit}.",
        )


def get_event_media_usage(db: Session, event_id: str) -> MediaQuota:
    """Return an event's current media usage vs its limits."""
    photo_count = _count_media(db, event_id, MediaType.PHOTO)
    video_count = _count_media(db, event_id, MediaType.VIDEO)
    max_photos = settings.MAX_PHOTOS_PER_EVENT
    max_videos = settings.MAX_VIDEOS_PER_EVENT
    return MediaQuota(
        photo_count=photo_count,
        video_count=video_count,
        max_photos=max_photos,
        max_videos=max_videos,
        photo_remaining=max(0, max_photos - photo_count),
        video_remaining=max(0, max_videos - video_count),
    )


# ============================================================
# GUEST UPLOAD
# ============================================================

def upload_media(
    db: Session,
    slug: str,
    raw_token: str,
    filename: str,
    data: bytes,
    storage: StorageService | None = None,
) -> Media:
    """
    Authenticate a guest, validate the file, enforce the quota, and
    store the media. Returns the created Media record.
    """
    storage = storage or get_storage_service()

    # 1) Authenticate the guest + load the LIVE event (server-side).
    event, guest, _session = guest_service.get_authenticated_guest(db, slug, raw_token)

    # 2) The event must be LIVE (get_authenticated_guest already
    #    enforces this, but we assert it for clarity).
    if event.status != EventStatus.LIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event is not accepting uploads.",
        )

    # 3) Validate the file by CONTENT (magic bytes), not filename.
    file_type = detect_file_type(data)

    # 4) Enforce the configured max file size BEFORE storing.
    #    (detect_file_type gives us the media category.)
    if file_type.media_type == "photo":
        limit_mb = settings.MAX_IMAGE_SIZE_MB
    else:
        limit_mb = settings.MAX_VIDEO_SIZE_MB
    if len(data) > limit_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum {'photo' if file_type.media_type == 'photo' else 'video'} "
                   f"size of {limit_mb} MB.",
        )

    # 5) Map validated category to the DB enum.
    media_type = _TYPE_MAP[file_type.media_type]

    # 6) Enforce the quota (concurrency-safe via row lock).
    _check_quota(db, event.id, media_type)

    # 7) Compute a checksum for integrity tracking.
    checksum = hashlib.sha256(data).hexdigest()

    # 8) Create the Media metadata row (commit BEFORE storage so a
    #    DB failure never leaves an orphan object).
    media = Media(
        event_id=event.id,
        guest_id=guest.id,
        original_filename=sanitize_filename(filename),
        storage_key="",  # filled after we know the id
        media_type=media_type,
        mime_type=file_type.mime_type,
        file_size=len(data),
        checksum=checksum,
        status=MediaStatus.UPLOADED,
    )
    db.add(media)
    db.flush()  # assign media.id

    # 9) Build the storage key from the now-known media id + upload.
    media.storage_key = _build_storage_key(event.id, media.id, media_type)
    db.commit()
    db.refresh(media)

    # 10) Upload the actual bytes to object storage.
    try:
        storage.upload(media.storage_key, data, media.mime_type)
    except Exception:
        # Storage failed. Delete the metadata row so we don't leave a
        # broken record that pretends a file exists.
        logger.error("Storage upload failed for media %s; removing record", media.id)
        db.delete(media)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to store media. Please try again.",
        )

# 11) Enqueue an ASYNC processing job (Phase 6). The request
    #     returns immediately; a background RQ worker derives the
    #     optimized/thumbnail/poster variants. If enqueueing fails
    #     (e.g. Redis is down), the media stays QUEUED and the
    #     original remains safe — we do NOT delete it.
    try:
        from app.services import media_processing
        media_processing.enqueue_processing(media.id)
    except Exception:  # noqa: BLE001 — never fail the upload
        logger.error("Processing enqueue failed for media %s", media.id)

    logger.info(
        "Media uploaded id=%s event_id=%s type=%s size=%d",
        media.id, event.id, media_type.value, len(data),
    )
    return media


# ============================================================
# GUEST LISTING (own media)
# ============================================================

def list_my_media(db: Session, slug: str, raw_token: str) -> list[Media]:
    """Return ONLY the current guest's media for the current event."""
    event, guest, _session = guest_service.get_authenticated_guest(db, slug, raw_token)
    return _list_media_for(db, event.id, guest_id=guest.id)


def _list_media_for(
    db: Session, event_id: str, guest_id: str | None = None
) -> list[Media]:
    """Query media for an event, optionally filtered to one guest."""
    query = (
        select(Media)
        .where(Media.event_id == event_id)
        .order_by(Media.created_at.desc())
    )
    if guest_id is not None:
        query = query.where(Media.guest_id == guest_id)
    return list(db.scalars(query))


# ============================================================
# GUEST DELETE (own media)
# ============================================================

def delete_my_media(
    db: Session,
    slug: str,
    raw_token: str,
    media_id: str,
    storage: StorageService | None = None,
) -> None:
    """
    Delete a media item the CURRENT GUEST uploaded. Enforces:
      - guest is authenticated + event-scoped,
      - the media belongs to the current guest AND current event,
      - otherwise 404 (no existence leak).
    Deletes the object from storage, then the metadata row.
    """
    storage = storage or get_storage_service()
    event, guest, _session = guest_service.get_authenticated_guest(db, slug, raw_token)

    # Strict ownership: media must belong to this guest + this event.
    media = db.scalar(
        select(Media).where(
            Media.id == media_id,
            Media.event_id == event.id,
            Media.guest_id == guest.id,
        )
    )
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found.",
        )

    # Delete the object from storage FIRST. If this fails, we do NOT
    # delete the DB row (avoid an orphaned storage object).
    try:
        storage.delete(media.storage_key)
    except Exception:
        logger.error("Storage delete failed for media %s; DB row kept", media.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete media.",
        )

    # Now it's safe to remove the metadata row.
    db.delete(media)
    db.commit()
    logger.info("Media deleted id=%s event_id=%s", media.id, event.id)


# ============================================================
# HOST ACCESS (owned event's media)
# ============================================================

def get_host_event_media(db: Session, host_id: str, event_id: str) -> list[Media]:
    """
    Return media for an event the HOST OWNS. If the event belongs to
    another host, return 404 (no existence leak).
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )
    return _list_media_for(db, event.id)


# ============================================================
# ADMIN ACCESS (any event's media)
# ============================================================

def get_admin_event_media(db: Session, event_id: str) -> list[Media]:
    """Return media for any event (admin access). 404 if not found."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )
    return _list_media_for(db, event.id)


# ============================================================
# PROCESSING STATUS (Phase 6)
# ============================================================

def get_processing_status(
    db: Session,
    slug: str,
    media_id: str,
    raw_token: str | None = None,
    host: User | None = None,
    admin: User | None = None,
) -> Media:
    """
    Return a media record for its PROCESSING STATUS, enforcing strict
    event isolation and role-based authorization:
      - a GUEST may only inspect media they uploaded to the event in
        `slug` (they prove identity with the guest token),
      - a HOST may only inspect media in an event they OWN,
      - an ADMIN may inspect any event's media.
    Returns 404 when the caller has no access (no existence leak).
    """
    # Resolve the event by slug so we can bound the media query to it.
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found.",
        )

    # Admin: any event's media.
    if admin is not None:
        media = db.get(Media, media_id)
        if media is None or media.event_id != event.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found.",
            )
        return media

    # Host: must own the event.
    if host is not None:
        if event.host_id != host.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found.",
            )
        media = db.get(Media, media_id)
        if media is None or media.event_id != event.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found.",
            )
        return media

    # Guest: must own the media in this event.
    if raw_token:
        # Authenticate the guest against this event (strict isolation).
        _event, guest, _session = guest_service.get_authenticated_guest(
            db, slug, raw_token
        )
        media = db.scalar(
            select(Media).where(
                Media.id == media_id,
                Media.event_id == event.id,
                Media.guest_id == guest.id,
            )
        )
        if media is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found.",
            )
        return media

    # No recognized credential.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required to view media processing status.",
    )
