# ============================================================
# Lentis Gallery — Media Model
# ------------------------------------------------------------
# Phase 5 + Phase 6. This SQLAlchemy model maps to the 'media'
# table.
#
# IMPORTANT ARCHITECTURAL RULE:
#   This table stores ONLY METADATA about a media item — never the
#   actual image/video bytes. The bytes live in OBJECT STORAGE
#   (Cloudflare R2 in production). PostgreSQL is the CATALOGUE;
#   object storage is the WAREHOUSE.
#
# WHAT WE STORE:
#   - Which event the media belongs to (event_id -> events.id)
#   - Which guest uploaded it  (guest_id  -> guests.id)
#   - A SAFE display filename  (original_filename)
#   - The object-storage key   (storage_key) — the location in R2
#   - The validated TYPE (PHOTO/VIDEO) + MIME type
#   - The actual byte size + a SHA-256 checksum for integrity
#   - A simple lifecycle status (UPLOADED / PENDING)
#   - Phase 6: async processing state + derived-variant metadata
#     (optimized/thumbnail/poster keys + sizes).
#
# CASCADE DELETE:
#   - If the event is deleted, its media rows go too.
#   - If the guest is deleted, their media rows go too.
# ============================================================

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class MediaType(str, enum.Enum):
    """Kind of media. Backend derives this from the validated file."""
    PHOTO = "PHOTO"
    VIDEO = "VIDEO"


class MediaRole(str, enum.Enum):
    """Role of this media within the event. Controls where it appears."""
    HERO = "HERO"
    SLIDESHOW = "SLIDESHOW"
    GALLERY = "GALLERY"
    HOST_SLIDESHOW = "HOST_SLIDESHOW"


class MediaSource(str, enum.Enum):
    """Who uploaded this media. Controls visibility and filtering."""
    ADMIN = "ADMIN"
    GUEST = "GUEST"


class MediaPage(str, enum.Enum):
    """Which page this media is assigned to. Controls slideshow display."""
    LANDING = "LANDING"
    GUEST = "GUEST"
    HOST = "HOST"
    CAMERA = "CAMERA"


class MediaStatus(str, enum.Enum):
    """
    Simple lifecycle.
    UPLOADED = admin-uploaded, immediately visible.
    PENDING = guest-uploaded, awaiting host approval.
    APPROVED = approved by host.
    HIDDEN = approved but hidden from public gallery by host.
    REJECTED = rejected by host.
    """
    UPLOADED = "UPLOADED"   # admin-uploaded, immediately visible
    PENDING = "PENDING"     # guest-uploaded, awaiting approval
    APPROVED = "APPROVED"   # approved by host
    HIDDEN = "HIDDEN"       # approved but hidden by host
    REJECTED = "REJECTED"   # rejected by host


class ProcessingStatus(str, enum.Enum):
    """
    Phase 6. The asynchronous media-processing pipeline state, stored
    in PostgreSQL. The frontend/host polls this to show progress.
        QUEUED     — awaiting a worker
        PROCESSING — a worker is actively processing
        READY      — processing complete (optimized/thumbs ready)
        FAILED     — processing failed; original is still preserved
    """
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class ModerationStatus(str, enum.Enum):
    """
    Host-controlled visibility. This is the legacy moderation status.
    Kept for backward compatibility. New code should use MediaStatus.
        VISIBLE — appears in the main gallery
        HIDDEN  — removed from the main gallery by a host
    """
    VISIBLE = "VISIBLE"
    HIDDEN = "HIDDEN"


def generate_uuid() -> str:
    """Random UUID string primary key (not guessable)."""
    return str(uuid.uuid4())


class Media(Base):
    __tablename__ = "media"

    # Primary key — random UUID string.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Which event this media belongs to. FK -> events.id (CASCADE).
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Which guest uploaded it. FK -> guests.id (CASCADE).
    guest_id: Mapped[str] = mapped_column(
        ForeignKey("guests.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # The host's original filename — sanitized at the API layer and
    # used ONLY for display. NEVER used as a storage path.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # The object-storage key where the bytes live, e.g.
    # events/{event_id}/media/{media_id}/original. Backend-generated.
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # Validated media type + MIME (from magic bytes, not the client).
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type"), nullable=False
    )
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)

    # Actual byte size reported by the backend.
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # SHA-256 hex digest of the object's bytes (integrity check).
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Lifecycle status.
    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus, name="media_status"),
        nullable=False,
        default=MediaStatus.UPLOADED,
    )

    # --- Phase 6: media processing state & derived variants -------
    # The async processing pipeline state (QUEUED/PROCESSING/READY/FAILED).
    # The original is NEVER overwritten; these fields track the derived
    # optimized/thumbnail/poster variants and processing metadata.
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"),
        nullable=False,
        default=ProcessingStatus.QUEUED,
        server_default="QUEUED",
    )
    # A SAFE internal error string on failure (never a raw stack trace
    # or filesystem path). Empty when there is no error.
    processing_error: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # How many processing attempts have been made (for the retry system).
    processing_attempts: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    # When processing finished (reached READY or FAILED). Nullable.
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Object-storage keys for the derived variants. All are nullable
    # because they only exist after processing creates them.
    optimized_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    poster_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Sizes of the derived variants (bytes). Nullable until created.
    optimized_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    thumbnail_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    poster_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # MIME type of the optimized variant (e.g. 'image/jpeg').
    optimized_mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # MIME type of the thumbnail variant (e.g. 'image/png').
    thumbnail_mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Media intrinsic metadata (filled by processing).
    width: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    height: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Thumbnail/poster dimensions (filled by processing).
    thumbnail_width: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    thumbnail_height: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # For videos: duration in seconds.
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    # --- Phase 3: Media Role & Position -------------------------------
    # Controls WHERE this media appears: hero, slideshow, or gallery.
    # Only one HERO per event (enforced at service layer).
    media_role: Mapped[MediaRole] = mapped_column(
        Enum(MediaRole, name="media_role"),
        nullable=False,
        default=MediaRole.GALLERY,
        server_default="GALLERY",
    )
    # Position within slideshow (1-indexed). Only meaningful for
    # SLIDESHOW role. NULL for hero and gallery media.
    position: Mapped[int | None] = mapped_column(nullable=True)

    # --- Phase 13.4: Media Source & Page ------------------------------
    # Source distinguishes admin-uploaded vs guest-uploaded media.
    source: Mapped[MediaSource] = mapped_column(
        Enum(MediaSource, name="media_source"),
        nullable=False,
        default=MediaSource.ADMIN,
        server_default="ADMIN",
    )
    # Page indicates which page this media is assigned to.
    # Only meaningful for SLIDESHOW/HOST_SLIDESHOW roles.
    page: Mapped[MediaPage | None] = mapped_column(
        Enum(MediaPage, name="media_page"),
        nullable=True,
        default=None,
        server_default=None,
    )

    # --- Phase 7: Host Media Moderation -----------------------------
    # Host-controlled visibility in the main gallery. Default is VISIBLE.
    moderation_status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus, name="moderation_status"),
        nullable=False,
        default=ModerationStatus.VISIBLE,
        server_default="VISIBLE",
    )
    # When the moderation status was last changed.
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Which user (host/admin) last changed the moderation status.
    # FK -> users.id. Set to NULL if the user is deleted.
    moderated_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps (timezone-aware UTC).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # ------------------------------------------------------------------
    # Computed helpers (Phase 6). These tell the API/frontend whether
    # each DERIVED variant has been produced. They read the storage-key
    # columns directly; they never expose the keys themselves.
    # ------------------------------------------------------------------
    @property
    def optimized(self) -> bool:
        """True once an optimized variant exists in storage."""
        return bool(self.optimized_key)

    @property
    def thumbnail(self) -> bool:
        """True once a thumbnail/poster-frame variant exists."""
        return bool(self.thumbnail_key)

    @property
    def poster(self) -> bool:
        """True once a video poster frame exists."""
        return bool(self.poster_key)

    def __repr__(self) -> str:
        return (
            f"<Media id={self.id} event_id={self.event_id} "
            f"type={self.media_type.value if self.media_type else None} "
            f"status={self.status.value if self.status else None}>"
        )


# Composite indexes for the queries the quota + listing code runs:
#   - Count an event's photos/videos: (event_id, media_type)
#   - List a guest's media: (event_id, guest_id)
#   - Gallery listing: (event_id, status, created_at)
#   - Processing worker queue: (processing_status, event_id)
#   - Role-based queries: (event_id, media_role, status)
Index("ix_media_event_type", Media.event_id, Media.media_type)
Index("ix_media_event_guest", Media.event_id, Media.guest_id)
Index("ix_media_created_at", Media.created_at)
Index("ix_media_processing_status", Media.processing_status)
Index("ix_media_event_role_status", Media.event_id, Media.media_role, Media.status)
Index("ix_media_event_status_created", Media.event_id, Media.status, Media.created_at)
