# ============================================================
# Lentis Gallery — File Validation (magic bytes)
# ------------------------------------------------------------
# Phase 5. This module decides whether an uploaded file is a
# supported, safe PHOTO or VIDEO by inspecting its ACTUAL CONTENT
# (magic bytes), NOT the filename or the browser-supplied MIME.
#
# WHY MAGIC BYTES?
#   A user can name anything "photo.jpg" and set Content-Type to
#   "image/jpeg". Those are just TEXT a client sends — trivially
#   spoofed. The only trustworthy signal is the bytes themselves.
#   Most file formats start with a recognizable "magic number"
#   (e.g. JPEG files start with b'\\xff\\xd8\\xff'). We read the
#   first few bytes and match them.
#
# APPROACH:
#   - We try to use 'python-magic' (libmagic) if available because
#     it is more thorough.
#   - We ALSO include a self-contained manual signature matcher so
#     the system works even where libmagic/system deps aren't
#     installed (e.g. the test suite). Production R2 setups can
#     install python-magic for stronger detection.
#
# SECURITY:
#   - We reject anything that isn't a known image/video signature.
#   - Executables, scripts, HTML, and arbitrary binaries have no
#     matching signature and are rejected by default.
# ============================================================

import logging
from dataclasses import dataclass

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Max bytes we read to detect the type (signatures are tiny).
_SNIFF_LEN = 512


@dataclass(frozen=True)
class FileType:
    """The validated result of inspecting a file."""
    media_type: str      # "photo" or "video"
    mime_type: str       # e.g. "image/jpeg"
    extension: str       # e.g. "jpg"


# Offset-aware signature matchers. Each entry is:
#   (label, expected_bytes, offset, mime, media_category, extension)
# We check data[offset:offset+len(sig)] == sig.
_SIGNATURES: list[tuple[str, bytes, int, str, str, str]] = [
    # --- Images ---
    ("jpeg", b"\xff\xd8\xff", 0, "image/jpeg", "photo", "jpg"),
    ("png", b"\x89PNG\r\n\x1a\n", 0, "image/png", "photo", "png"),
    # WebP: "RIFF" .... "WEBP"
    ("webp", b"WEBP", 8, "image/webp", "photo", "webp"),
    # GIF (commonly uploaded; harmless)
    ("gif", b"GIF87a", 0, "image/gif", "photo", "gif"),
    ("gif", b"GIF89a", 0, "image/gif", "photo", "gif"),
    # --- Videos ---
    # MP4 (ftyp box at offset 4)
    ("mp4", b"ftyp", 4, "video/mp4", "video", "mp4"),
    # WebM / Matroska
    ("webm", b"\x1a\x45\xdf\xa3", 0, "video/webm", "video", "webm"),
    # QuickTime MOV
    ("mov", b"moov", 4, "video/quicktime", "video", "mov"),
    ("mov", b"mdat", 4, "video/quicktime", "video", "mov"),
]


def _detect_by_signature(data: bytes) -> FileType | None:
    """Detect the file type from magic bytes (no external deps)."""
    for _label, sig, offset, mime, category, ext in _SIGNATURES:
        start = offset
        end = offset + len(sig)
        if len(data) >= end and data[start:end] == sig:
            return FileType(
                media_type=category,
                mime_type=mime,
                extension=ext,
            )
    return None


def _detect_with_magic(data: bytes) -> FileType | None:
    """
    Try to use python-magic for a more authoritative detection.
    Returns None if python-magic isn't installed, so we gracefully
    fall back to signature matching.
    """
    try:
        import magic  # type: ignore
    except ImportError:
        return None

    try:
        detected = magic.from_buffer(data, mime=True)
    except Exception:  # noqa: BLE001 — libmagic can throw on odd input
        return None

    mime = detected or ""
    if mime in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        category = "photo"
        ext = {"image/jpeg": "jpg", "image/png": "png",
               "image/webp": "webp", "image/gif": "gif"}.get(mime, "bin")
        return FileType(media_type=category, mime_type=mime, extension=ext)
    if mime in ("video/mp4", "video/webm", "video/quicktime"):
        category = "video"
        ext = {"video/mp4": "mp4", "video/webm": "webm",
               "video/quicktime": "mov"}.get(mime, "bin")
        return FileType(media_type=category, mime_type=mime, extension=ext)
    return None


def detect_file_type(data: bytes) -> FileType:
    """
    Determine the validated file type from raw bytes.
    Raises HTTPException(415) for unsupported/unknown content.
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Empty file.",
        )

    # 1) Signature-based (always available).
    result = _detect_by_signature(data[:_SNIFF_LEN])
    # 2) If python-magic is available, prefer it (it agrees with and
    #    extends signature detection).
    magic_result = _detect_with_magic(data[:_SNIFF_LEN])
    if magic_result is not None:
        result = magic_result

    if result is None:
        logger.warning("Rejected upload: unrecognized file signature "
                       "(first bytes: %s)", data[:16].hex())
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Upload a JPEG, PNG, WebP, "
                   "MP4, WebM, or MOV file.",
        )

    return result


def sanitize_filename(filename: str) -> str:
    """
    Normalize a user-supplied filename into a safe display string.
    We strip path components, control chars, and weird characters.
    The result is used ONLY for display (never as a storage path).
    """
    import os

    # Take just the base name (drop any directory path).
    base = os.path.basename(filename or "upload")
    # Keep only printable characters, collapse spaces.
    safe = "".join(ch for ch in base if ch.isprintable() and ch not in '<>:"/\\|?*')
    safe = " ".join(safe.split())
    # Limit length.
    safe = safe[:255]
    return safe or "upload"


def enforce_size_limit(media_type: str, size: int, max_photo_mb: int, max_video_mb: int) -> None:
    """
    Reject files larger than the configured maximum BEFORE they are
    stored. media_type is "photo" or "video".
    """
    if media_type == "photo":
        limit_bytes = max_photo_mb * 1024 * 1024
        kind = "photo"
    else:
        limit_bytes = max_video_mb * 1024 * 1024
        kind = "video"

    if size > limit_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum {kind} size of "
                   f"{max_photo_mb if media_type == 'photo' else max_video_mb} MB.",
        )
