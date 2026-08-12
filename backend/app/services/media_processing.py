# ============================================================
# Lentis Gallery — Media Processing Service (Phase 6)
# ------------------------------------------------------------
# This is the glue between the API, the job queue, the processors,
# and object storage. It is what the WORKER calls to actually run a
# processing job, and what the API calls to ENQUEUE a job.
#
# FLOW:
#   API (on upload)          -> enqueue_processing(media_id)
#   RQ worker (runs job)     -> process_media(media_id)
#
# process_media() does the real work:
#   1. Marks the media PROCESSING.
#   2. Downloads the PRESERVED ORIGINAL from storage.
#   3. Writes it to a secure temp file.
#   4. Runs the right processor (Pillow for images, FFmpeg for video).
#   5. Uploads the derived variants to storage.
#   6. Records derivative metadata + sets status READY.
#
# On ANY failure it:
#   - NEVER deletes the original.
#   - Records a SAFE error string (never a stack trace/path).
#   - Either retries (if attempts remain) or marks FAILED.
#
# RETRY MODEL:
#   We use a bounded retry. The worker increments processing_attempts
#   each time it runs. If another attempt is allowed, the job is
#   re-enqueued; otherwise it is marked FAILED. No infinite loops.
# ============================================================

import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.media import Media, MediaType, ProcessingStatus
from app.processors import image as image_processor
from app.processors import video as video_processor
from app.storage import StorageService, get_storage_service

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Storage-key helpers for the derived variants.
#
# The ORIGINAL lives at events/{event_id}/media/{media_id}/original
# (see media_service._build_storage_key). The derived siblings are
# predictable from the same media_id but are distinct objects:
#   .../optimized   (image optimized / video playback MP4)
#   .../thumbnail   (image grid thumbnail / video poster)
#   .../poster      (video poster frame)
# Because media_id is a random UUID, none of these paths are
# guessable, and the original filename is NEVER used as a key.
# ------------------------------------------------------------------
def _variant_key(media: Media, variant: str) -> str:
    return f"events/{media.event_id}/media/{media.id}/{variant}"


# ------------------------------------------------------------------
# Enqueue — called by the API after a successful upload.
# ------------------------------------------------------------------
def enqueue_processing(media_id: str) -> None:
    """
    Push a media item onto the processing queue. This runs inside the
    upload request and returns quickly — the guest does NOT wait for
    processing. If Redis is unavailable we log the problem and leave
    the media in QUEUED (the original is never deleted).
    """
    try:
        from rq import Queue
        from redis import Redis

        conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue(settings.PROCESSING_QUEUE, connection=conn)
        queue.enqueue(
            "app.workers.media_worker.process_media_job",
            media_id,
            job_timeout=600,  # 10-minute safety cap per job
        )
        logger.info("Enqueued processing job for media %s", media_id)
    except Exception as exc:  # noqa: BLE001 — never fail the upload
        logger.error("Failed to enqueue processing for media %s: %s", media_id, exc)


# ------------------------------------------------------------------
# Temp-file handling
# ------------------------------------------------------------------
def _temp_dir() -> Path:
    """Return the configured temp dir (or the system temp dir)."""
    if settings.PROCESSING_TEMP_DIR:
        path = Path(settings.PROCESSING_TEMP_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path(tempfile.gettempdir())


def _write_temp(original_bytes: bytes, extension: str) -> Path:
    """
    Write the original bytes to a SECURE temp file with a random
    name (no predictable path, no user-controlled name). Returns the
    path. Callers MUST delete it in a finally block.
    """
    base = _temp_dir()
    name = f"lentis-{uuid.uuid4().hex}{extension}"
    path = base / name
    path.write_bytes(original_bytes)
    return path


def _cleanup(paths: list[Path]) -> None:
    """Best-effort removal of temp files. Never raises."""
    for p in paths:
        try:
            if p and p.exists():
                p.unlink()
        except Exception:  # noqa: BLE001
            logger.warning("Could not remove temp file %s", p)


# ------------------------------------------------------------------
# The main processing routine (called by the worker)
# ------------------------------------------------------------------
def process_media(db: Session, media_id: str, storage: StorageService | None = None) -> Media:
    """
    Run the full processing pipeline for one media item. Raises on
    failure so the worker can record the error and apply retry logic.
    The ORIGINAL is always preserved.
    """
    storage = storage or get_storage_service()

    media = db.get(Media, media_id)
    if media is None:
        raise ValueError(f"Media {media_id} not found.")

    # Mark PROCESSING (from QUEUED) and bump the attempt counter.
    media.processing_status = ProcessingStatus.PROCESSING
    media.processing_attempts = (media.processing_attempts or 0) + 1
    media.processing_error = ""
    db.commit()

    temp_paths: list[Path] = []
    try:
        # 1) Download the PRESERVED ORIGINAL from storage.
        original_bytes = storage.download(media.storage_key)

        # 2) Write it to a secure temp file.
        ext = _extension_for(media.mime_type)
        temp_paths.append(_write_temp(original_bytes, ext))

        if media.media_type == MediaType.PHOTO:
            _process_photo(db, media, temp_paths[0], storage)
        elif media.media_type == MediaType.VIDEO:
            _process_video(db, media, temp_paths[0], storage)
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unknown media type: {media.media_type}")

        # 3) Success — mark READY.
        media.processing_status = ProcessingStatus.READY
        media.processing_error = ""
        media.processed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Media %s processed and READY", media_id)
        return media

    except Exception as exc:  # noqa: BLE001 — top-level failure handling
        _record_failure(db, media, str(exc))
        raise
    finally:
        _cleanup(temp_paths)


def _extension_for(mime: str) -> str:
    """Map a MIME type to a safe temp-file extension."""
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
    }.get(mime, ".bin")


def _process_photo(db: Session, media: Media, original_path: Path, storage: StorageService) -> None:
    """Image pipeline: optimized + thumbnail, then upload + record."""
    data = original_path.read_bytes()
    derivatives = image_processor.process_image(data)

    # Upload optimized variant.
    optimized_key = _variant_key(media, "optimized")
    storage.upload(optimized_key, derivatives.optimized_bytes, derivatives.optimized_mime)

    # Upload thumbnail variant.
    thumb_key = _variant_key(media, "thumbnail")
    storage.upload(thumb_key, derivatives.thumbnail_bytes, derivatives.thumbnail_mime)

    # Record metadata in the DB.
    media.optimized_key = optimized_key
    media.optimized_size = len(derivatives.optimized_bytes)
    media.optimized_mime_type = derivatives.optimized_mime
    media.thumbnail_key = thumb_key
    media.thumbnail_size = len(derivatives.thumbnail_bytes)
    media.thumbnail_mime_type = derivatives.thumbnail_mime
    media.width = derivatives.width
    media.height = derivatives.height
    media.thumbnail_width = derivatives.thumbnail_width
    media.thumbnail_height = derivatives.thumbnail_height
    db.commit()


def _process_video(db: Session, media: Media, original_path: Path, storage: StorageService) -> None:
    """Video pipeline: optimized MP4 + poster, then upload + record."""
    # Process into an isolated sub-temp dir so FFmpeg's outputs are
    # contained and cleaned up together.
    out_dir = Path(tempfile.mkdtemp(dir=_temp_dir()))
    try:
        derivatives = video_processor.process_video(original_path, out_dir)

        # Upload optimized playback MP4.
        opt_key = _variant_key(media, "optimized")
        opt_bytes = derivatives.optimized_path.read_bytes()
        storage.upload(opt_key, opt_bytes, derivatives.optimized_mime)

        media.optimized_key = opt_key
        media.optimized_size = len(opt_bytes)
        media.optimized_mime_type = derivatives.optimized_mime
        media.width = derivatives.width
        media.height = derivatives.height
        media.duration_seconds = derivatives.duration_seconds

        # Upload poster frame (best-effort; failure is recorded, not fatal).
        if derivatives.poster_path is not None:
            poster_key = _variant_key(media, "poster")
            poster_bytes = derivatives.poster_path.read_bytes()
            storage.upload(poster_key, poster_bytes, derivatives.poster_mime or "image/jpeg")
            media.poster_key = poster_key
            media.poster_size = len(poster_bytes)
            media.thumbnail_key = poster_key
            media.thumbnail_size = len(poster_bytes)
            media.thumbnail_mime_type = derivatives.poster_mime or "image/jpeg"
        else:
            logger.warning("Poster extraction failed for media %s (continuing)", media.id)
            media.poster_key = None
            media.poster_size = None
            media.thumbnail_key = None
            media.thumbnail_size = None
        db.commit()
    finally:
        _cleanup([out_dir])


def _record_failure(db: Session, media: Media, message: str) -> None:
    """
    Safely record a processing failure. `message` is a SAFE summary
    (from our processors), never a raw stack trace or filesystem path.
    The ORIGINAL and the Media row are always preserved.
    """
    safe = (message or "Processing failed.").replace("\n", " ").replace("\r", " ")[:480]

    if (media.processing_attempts or 0) >= settings.PROCESSING_MAX_RETRIES:
        media.processing_status = ProcessingStatus.FAILED
        media.processing_error = safe
        media.processed_at = datetime.now(timezone.utc)
        logger.error("Media %s permanently FAILED after %d attempts: %s",
                     media.id, media.processing_attempts, safe)
    else:
        # Still have retries left: return to QUEUED so a worker can
        # pick it up again on the next attempt.
        media.processing_status = ProcessingStatus.QUEUED
        media.processing_error = safe
        logger.warning("Media %s reprocessing queued (attempt %d): %s",
                       media.id, media.processing_attempts, safe)
    db.commit()
