# ============================================================
# Lentis Gallery — Media Schemas
# ------------------------------------------------------------
# Pydantic schemas for the Media API (Phase 5).
#
# WHY SEPARATE SCHEMAS FROM THE ORM MODEL?
#   * We NEVER return the raw SQLAlchemy Media object. It contains
#     storage_key (a sensitive internal path) which guests must not
#     see.
#   * Schemas are the contract with the frontend. We decide exactly
#     which fields cross the API boundary.
#
# SECURITY:
#   - storage_key is INTERNAL. It is never returned to guests/hosts.
#   - We expose only safe, useful metadata.
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.media import MediaStatus, MediaType, ProcessingStatus


class MediaOut(BaseModel):
    """Safe view of a media record (no storage_key, no internal paths)."""
    id: str
    event_id: str
    media_type: MediaType
    mime_type: str
    original_filename: str
    file_size: int
    status: MediaStatus
    # Phase 6: async processing state + whether derived variants exist.
    processing_status: ProcessingStatus
    optimized: bool = False
    thumbnail: bool = False
    poster: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaUploadResponse(BaseModel):
    """Response to a successful media upload."""
    id: str
    media_type: MediaType
    status: MediaStatus
    processing_status: ProcessingStatus
    original_filename: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaProcessingStatusOut(BaseModel):
    """
    The processing-status payload returned by the status endpoint.
    Distinguishes the ORIGINAL (always present) from the derived
    OPTIMIZED / THUMBNAIL / POSTER variants. Never exposes storage
    keys or credentials.
    """
    media_id: str
    event_id: str
    status: ProcessingStatus
    original: bool = True           # the original is always preserved
    optimized: bool = False
    thumbnail: bool = False
    poster: bool = False
    processing_attempts: int = 0
    processing_error: str = ""
    processed_at: datetime | None = None


class MediaListResponse(BaseModel):
    """List of a guest's own media (or an event's media)."""
    items: list[MediaOut]
    total: int


class MediaQuota(BaseModel):
    """
    Per-event media usage vs limits. Hosts/admins use this to show
    capacity (e.g. "Photos: 1,284 / 3,000").
    """
    photo_count: int
    video_count: int
    max_photos: int
    max_videos: int
    photo_remaining: int
    video_remaining: int
