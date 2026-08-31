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
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event, EventStatus
from app.models.guest import Guest
from app.models.media import Media, MediaPage, MediaRole, MediaSource, MediaStatus, MediaType, ModerationStatus
from datetime import datetime, timezone
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
    """
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


def _check_storage_limit(db: Session, event: Event, file_size: int) -> None:
    """
    Reject an upload if it would exceed the event's storage limit.
    """
    limit_bytes = (event.storage_limit_gb or 50) * 1024 * 1024 * 1024
    current_used = event.storage_used_bytes or 0
    if current_used + file_size > limit_bytes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event storage limit of {event.storage_limit_gb} GB reached.",
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

    # 6b) Enforce storage limit.
    _check_storage_limit(db, event, len(data))

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
        media_role=MediaRole.GALLERY,
        source=MediaSource.GUEST,
        mime_type=file_type.mime_type,
        file_size=len(data),
        checksum=checksum,
        status=MediaStatus.PENDING,  # Guest uploads start as PENDING
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
        )    # 11) Enqueue an ASYNC processing job (Phase 6).
    try:
        from app.services import media_processing
        media_processing.enqueue_processing(media.id)
    except Exception:  # noqa: BLE001 — never fail the upload
        logger.error("Processing enqueue failed for media %s", media.id)

    # 12) Atomically update event storage usage (concurrency-safe).
    db.execute(
        update(Event)
        .where(Event.id == event.id)
        .values(storage_used_bytes=Event.storage_used_bytes + len(data))
    )
    db.commit()

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
# ADMIN UPLOAD (admin uploads media to any event)
# ============================================================

def admin_upload_media(
    db: Session,
    event_id: str,
    filename: str,
    data: bytes,
    media_role: MediaRole = MediaRole.GALLERY,
    source: MediaSource = MediaSource.ADMIN,
    page: MediaPage | None = None,
    storage: StorageService | None = None,
) -> Media:
    """
    Admin uploads media directly to an event (no guest session needed).
    Used for slideshow images, hero images, etc.
    """
    storage = storage or get_storage_service()

    # 1) Verify the event exists.
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    # 2) Validate the file by CONTENT (magic bytes), not filename.
    file_type = detect_file_type(data)

    # 3) Enforce the configured max file size BEFORE storing.
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

    # 4) Map validated category to the DB enum.
    media_type = _TYPE_MAP[file_type.media_type]

    # 5) Enforce the quota (concurrency-safe via row lock).
    _check_quota(db, event.id, media_type)

    # 5b) Enforce storage limit.
    _check_storage_limit(db, event, len(data))

    # 6) Compute a checksum for integrity tracking.
    checksum = hashlib.sha256(data).hexdigest()

    # 7) Create a synthetic guest row for admin uploads.
    from app.models.guest import Guest
    admin_guest = Guest(event_id=event.id, name="Admin Upload")
    db.add(admin_guest)
    db.flush()

    # 8) Create the Media metadata row.
    media = Media(
        event_id=event.id,
        guest_id=admin_guest.id,
        original_filename=sanitize_filename(filename),
        storage_key="",  # filled after we know the id
        media_type=media_type,
        media_role=media_role,
        source=source,
        page=page,
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
        logger.error("Storage upload failed for admin media %s; removing record", media.id)
        db.delete(media)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to store media. Please try again.",
        )

    # 11) Enqueue processing job (best-effort).
    try:
        from app.services import media_processing
        media_processing.enqueue_processing(media.id)
    except Exception:  # noqa: BLE001
        logger.error("Processing enqueue failed for admin media %s", media.id)

    # 12) Atomically update event storage usage (concurrency-safe).
    db.execute(
        update(Event)
        .where(Event.id == event.id)
        .values(storage_used_bytes=Event.storage_used_bytes + len(data))
    )
    db.commit()

    logger.info(
        "Admin media uploaded id=%s event_id=%s type=%s size=%d",
        media.id, event.id, media_type.value, len(data),
    )
    return media


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


# ============================================================
# ADMIN MEDIA MANAGEMENT
# ============================================================

def admin_delete_media(
    db: Session,
    event_id: str,
    media_id: str,
    storage: StorageService | None = None,
) -> None:
    """
    Admin deletes media from any event. Removes from storage + DB.
    Updates event storage_used_bytes.
    """
    storage = storage or get_storage_service()
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    file_size = media.file_size

    # Delete from storage
    try:
        storage.delete(media.storage_key)
    except Exception:
        logger.error("Storage delete failed for media %s", media.id)
        raise HTTPException(status_code=502, detail="Failed to delete media.")

    db.delete(media)

    # Atomically decrement event storage (concurrency-safe).
    db.execute(
        update(Event)
        .where(Event.id == event_id, Event.storage_used_bytes >= file_size)
        .values(storage_used_bytes=Event.storage_used_bytes - file_size)
    )
    db.commit()
    logger.info("Admin deleted media id=%s event_id=%s", media_id, event_id)


def admin_set_media_role(
    db: Session,
    event_id: str,
    media_id: str,
    new_role: MediaRole,
    page: MediaPage | None = None,
) -> Media:
    """
    Admin changes a media item's role (hero/slideshow/gallery).
    If setting HERO, clears existing hero.
    If setting SLIDESHOW, assigns next position.
    """
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    # If setting SLIDESHOW, assign next position
    if new_role == MediaRole.SLIDESHOW:
        max_pos = db.scalar(
            select(func.coalesce(func.max(Media.position), 0)).where(
                Media.event_id == event_id,
                Media.media_role == MediaRole.SLIDESHOW,
            )
        ) or 0
        media.position = max_pos + 1
    else:
        media.position = None

    media.media_role = new_role
    media.page = page
    db.commit()
    db.refresh(media)
    return media


def admin_reorder_slideshow(
    db: Session,
    event_id: str,
    ordered_ids: list[str],
) -> None:
    """
    Reorder slideshow media for an event.
    ordered_ids is the list of media IDs in desired order.
    Only affects media with role=SLIDESHOW.
    """
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    # Fetch all slideshow media for this event
    slideshow_media = list(
        db.scalars(
            select(Media).where(
                Media.event_id == event_id,
                Media.media_role == MediaRole.SLIDESHOW,
            )
        )
    )
    media_map = {m.id: m for m in slideshow_media}

    # Update positions based on ordered_ids
    for idx, media_id in enumerate(ordered_ids, start=1):
        if media_id in media_map:
            media_map[media_id].position = idx

    db.commit()
    logger.info("Slideshow reordered event_id=%s count=%d", event_id, len(ordered_ids))


# ============================================================
# HOST MODERATION
# ============================================================

def host_approve_media(
    db: Session,
    host_id: str,
    event_id: str,
    media_id: str,
) -> Media:
    """
    Host approves a guest's media upload.
    Verifies host owns the event.
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    media.status = MediaStatus.APPROVED
    media.moderation_status = ModerationStatus.VISIBLE
    media.moderated_at = datetime.now(timezone.utc)
    media.moderated_by = host_id
    db.commit()
    db.refresh(media)
    return media


def host_reject_media(
    db: Session,
    host_id: str,
    event_id: str,
    media_id: str,
) -> Media:
    """
    Host rejects a guest's media upload.
    Verifies host owns the event.
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    media.status = MediaStatus.REJECTED
    media.moderation_status = ModerationStatus.HIDDEN
    media.moderated_at = datetime.now(timezone.utc)
    media.moderated_by = host_id
    db.commit()
    db.refresh(media)
    return media


def host_delete_media(
    db: Session,
    host_id: str,
    event_id: str,
    media_id: str,
    storage: StorageService | None = None,
) -> None:
    """
    Host deletes any media from their own event.
    """
    storage = storage or get_storage_service()
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    file_size = media.file_size
    try:
        storage.delete(media.storage_key)
    except Exception:
        logger.error("Storage delete failed for media %s", media.id)
        raise HTTPException(status_code=502, detail="Failed to delete media.")

    db.delete(media)
    # Atomically decrement event storage (concurrency-safe).
    db.execute(
        update(Event)
        .where(Event.id == event_id, Event.storage_used_bytes >= file_size)
        .values(storage_used_bytes=Event.storage_used_bytes - file_size)
    )
    db.commit()


def host_hide_media(
    db: Session,
    host_id: str,
    event_id: str,
    media_id: str,
) -> Media:
    """
    Host hides approved guest media. Sets status=HIDDEN and
    moderation_status=HIDDEN. The media is removed from the public
    gallery but can be restored by the host.
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    media.status = MediaStatus.HIDDEN
    media.moderation_status = ModerationStatus.HIDDEN
    media.moderated_at = datetime.now(timezone.utc)
    media.moderated_by = host_id
    db.commit()
    db.refresh(media)
    return media


def host_unhide_media(
    db: Session,
    host_id: str,
    event_id: str,
    media_id: str,
) -> Media:
    """
    Host restores hidden media. Sets status=APPROVED and
    moderation_status=VISIBLE.
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    media.status = MediaStatus.APPROVED
    media.moderation_status = ModerationStatus.VISIBLE
    media.moderated_at = datetime.now(timezone.utc)
    media.moderated_by = host_id
    db.commit()
    db.refresh(media)
    return media


def host_approve_all_media(
    db: Session,
    host_id: str,
    event_id: str,
) -> int:
    """
    Host bulk-approves all pending guest media for their event.
    Verifies host owns the event.
    Only approves media that are:
    - source == GUEST
    - status == PENDING
    - event_id matches
    Returns the count of approved media items.
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found.")

    # Find all pending guest media for this event
    pending_media = db.scalars(
        select(Media).where(
            Media.event_id == event_id,
            Media.source == MediaSource.GUEST,
            Media.status == MediaStatus.PENDING,
        )
    ).all()

    approved_count = 0
    now = datetime.now(timezone.utc)

    for media in pending_media:
        media.status = MediaStatus.APPROVED
        media.moderation_status = ModerationStatus.VISIBLE
        media.moderated_at = now
        media.moderated_by = host_id
        approved_count += 1

    if approved_count > 0:
        db.commit()

    logger.info("Host bulk approved %d media items for event %s", approved_count, event_id)
    return approved_count


# ============================================================
# HOST UPLOAD (host uploads presentation media to their own event)
# ============================================================

def host_upload_media(
    db: Session,
    host_id: str,
    event_id: str,
    filename: str,
    data: bytes,
    media_role: MediaRole = MediaRole.GALLERY,
    source: MediaSource = MediaSource.ADMIN,
    page: MediaPage | None = None,
    storage: StorageService | None = None,
) -> Media:
    """
    Host uploads presentation media to their own event.
    Verifies host owns the event before upload.
    Reuses the same logic as admin_upload_media.
    """
    storage = storage or get_storage_service()

    # Verify host owns this event
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    # Validate file by content (magic bytes)
    file_type = detect_file_type(data)

    # Enforce max file size
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

    media_type = _TYPE_MAP[file_type.media_type]

    # Enforce quota
    _check_quota(db, event.id, media_type)

    # Enforce storage limit
    _check_storage_limit(db, event, len(data))

    checksum = hashlib.sha256(data).hexdigest()

    # Create synthetic guest row for host uploads
    host_guest = Guest(event_id=event.id, name="Host Upload")
    db.add(host_guest)
    db.flush()

    # Create Media metadata row
    media = Media(
        event_id=event.id,
        guest_id=host_guest.id,
        original_filename=sanitize_filename(filename),
        storage_key="",
        media_type=media_type,
        media_role=media_role,
        source=source,
        page=page,
        mime_type=file_type.mime_type,
        file_size=len(data),
        checksum=checksum,
        status=MediaStatus.UPLOADED,
    )
    db.add(media)
    db.flush()

    media.storage_key = _build_storage_key(event.id, media.id, media_type)
    db.commit()
    db.refresh(media)

    # Upload to object storage
    try:
        storage.upload(media.storage_key, data, media.mime_type)
    except Exception:
        logger.error("Storage upload failed for host media %s; removing record", media.id)
        db.delete(media)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to store media. Please try again.",
        )

    # Enqueue processing job (best-effort)
    try:
        from app.services import media_processing
        media_processing.enqueue_processing(media.id)
    except Exception:
        logger.error("Processing enqueue failed for host media %s", media.id)

    # Update event storage usage
    db.execute(
        update(Event)
        .where(Event.id == event.id)
        .values(storage_used_bytes=Event.storage_used_bytes + len(data))
    )
    db.commit()
    db.refresh(media)

    logger.info("Host uploaded media %s for event %s (role=%s, page=%s)",
                media.id, event_id, media_role, page)
    return media


# ============================================================
# HOST SET MEDIA ROLE (host reassigns media in their own event)
# ============================================================

def host_set_media_role(
    db: Session,
    host_id: str,
    event_id: str,
    media_id: str,
    new_role: MediaRole,
    page: MediaPage | None = None,
) -> Media:
    """
    Host changes a media item's role and page in their own event.
    Verifies host owns the event.
    """
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_id:
        raise HTTPException(status_code=404, detail="Event not found.")

    media = db.scalar(
        select(Media).where(Media.id == media_id, Media.event_id == event_id)
    )
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    # If setting SLIDESHOW, assign next position
    if new_role == MediaRole.SLIDESHOW:
        max_pos = db.scalar(
            select(func.coalesce(func.max(Media.position), 0)).where(
                Media.event_id == event_id,
                Media.media_role == MediaRole.SLIDESHOW,
            )
        ) or 0
        media.position = max_pos + 1

    media.media_role = new_role
    media.page = page
    db.commit()
    db.refresh(media)

    logger.info("Host set media %s role=%s page=%s for event %s",
                media_id, new_role, page, event_id)
    return media
