# ============================================================
# Lentis Gallery — Media Schemas
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.media import MediaPage, MediaRole, MediaSource, MediaType, MediaStatus, ModerationStatus, ProcessingStatus


class MediaOut(BaseModel):
    """Safe view of a media record — includes media_url for display."""
    id: str
    event_id: str
    media_type: MediaType
    media_role: MediaRole = MediaRole.GALLERY
    position: int | None = None
    source: MediaSource = MediaSource.ADMIN
    page: MediaPage | None = None
    mime_type: str
    original_filename: str
    file_size: int
    status: MediaStatus
    processing_status: ProcessingStatus
    optimized: bool = False
    thumbnail: bool = False
    poster: bool = False
    media_url: str | None = None
    created_at: datetime
    guest_name: str | None = None
    moderation_status: ModerationStatus = ModerationStatus.VISIBLE
    
    model_config = ConfigDict(from_attributes=True)


class MediaUploadResponse(BaseModel):
    """Response to a successful media upload."""
    id: str
    media_type: MediaType
    media_role: MediaRole = MediaRole.GALLERY
    position: int | None = None
    source: MediaSource = MediaSource.ADMIN
    page: MediaPage | None = None
    status: MediaStatus
    processing_status: ProcessingStatus
    original_filename: str
    file_size: int
    created_at: datetime


class MediaRoleUpdate(BaseModel):
    """Request to change a media item's role."""
    media_role: MediaRole
    page: MediaPage | None = None


class MediaReorderRequest(BaseModel):
    """Request to reorder slideshow media."""
    ordered_ids: list[str]


class MediaProcessingStatusOut(BaseModel):
    """Media processing status response."""
    media_id: str
    event_id: str | None = None
    status: str
    original: bool = True
    optimized: bool = False
    thumbnail: bool = False
    poster: bool = False
    processing_error: str | None = None
    processing_attempts: int = 0
    processed_at: str | None = None


class MediaQuota(BaseModel):
    """Media usage stats for an event."""
    photo_count: int
    video_count: int
    max_photos: int
    max_videos: int
    photo_remaining: int = 0
    video_remaining: int = 0


class MediaListResponse(BaseModel):
    """Paginated list of media items."""
    items: list[MediaOut]
    total: int


class RecentMemory(BaseModel):
    """A recent guest memory for the overview."""
    id: str
    media_url: str
    media_type: MediaType
    guest_name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class HostOverviewStats(BaseModel):
    """Host dashboard overview statistics."""
    total_uploads: int
    photos: int
    videos: int
    storage_bytes: int
    contributing_guests: int
    recent_memories: list[RecentMemory]
    
    model_config = ConfigDict(from_attributes=True)
