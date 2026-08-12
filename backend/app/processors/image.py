# ============================================================
# Lentis Gallery — Image Processor (Phase 6)
# ------------------------------------------------------------
# Uses Pillow to derive an OPTIMIZED image and a THUMBNAIL from a
# PRESERVED ORIGINAL. The original file is NEVER modified.
#
# PRINCIPLES:
#   * Never upscale. We only shrink images larger than the target
#     maximum dimension. Small originals stay pixel-for-pixel.
#   * Preserve aspect ratio (never stretch).
#   * Correct EXIF orientation so rotated phone photos display
#     upright.
#   * Avoid unnecessary quality loss — use a high JPEG/WebP quality
#     and only re-encode when it actually helps.
#   * Preserve transparency for PNG/WebP where the format needs it.
#   * Strip most metadata (EXIF) to shrink size and privacy; we
#     keep only the information that matters (we read orientation
#     BEFORE stripping).
#
# OUTPUT:
#   * optimized  — a high-quality, display-ready image
#   * thumbnail  — a small grid thumbnail
# ============================================================

import io
import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

# Pillow is imported lazily so the module is importable even where
# Pillow isn't installed (e.g. very minimal test environments).
try:
    from PIL import Image, ImageOps, UnidentifiedImageError  # type: ignore
    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - dev-only fallback
    Image = None  # type: ignore
    ImageOps = None  # type: ignore
    UnidentifiedImageError = Exception
    _PIL_AVAILABLE = False


@dataclass
class ImageDerivatives:
    """The derived assets an image processor produces (in memory)."""
    optimized_bytes: bytes
    optimized_mime: str
    thumbnail_bytes: bytes
    thumbnail_mime: str
    width: int
    height: int
    thumbnail_width: int
    thumbnail_height: int


class ImageProcessorError(Exception):
    """Raised when an image cannot be processed safely."""


def _require_pillow() -> None:
    if not _PIL_AVAILABLE:
        raise ImageProcessorError(
            "Pillow is not installed. Add 'Pillow' to requirements.txt "
            "and reinstall dependencies."
        )


def _downscale(img: "Image.Image", max_dimension: int) -> "Image.Image":
    """
    Shrink an image so its longest side is at most `max_dimension`.
    NEVER enlarges: if the image is already smaller we return it
    unchanged. Aspect ratio is preserved.
    """
    if max(img.size) <= max_dimension:
        return img
    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    return img


def _encode_jpeg(img: "Image.Image", quality: int) -> bytes:
    """Encode an RGB image as an optimized, progressive JPEG."""
    buf = io.BytesIO()
    img.save(
        buf,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return buf.getvalue()


def _encode_for_output(img: "Image.Image", quality: int) -> tuple[bytes, str]:
    """
    Choose the best output format for a derivative based on the
    image's current mode and whether it has transparency.
      - RGBA / palette with transparency -> PNG (lossless, keeps alpha)
      - Otherwise -> JPEG (best size/quality for photos)
    """
    has_alpha = (
        img.mode in ("RGBA", "LA")
        or (img.mode == "P" and "transparency" in img.info)
    )
    if has_alpha:
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "image/png"

    buf = io.BytesIO()
    img.save(
        buf,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return buf.getvalue(), "image/jpeg"


def _load_image(data: bytes) -> "Image.Image":
    """Open raw bytes as a Pillow image, honoring EXIF orientation."""
    _require_pillow()
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Never trust the magic bytes alone — Pillow is the real
        # validator here. A file that passes magic-byte sniffing but
        # is not a decodable image is rejected DURING processing.
        raise ImageProcessorError("Not a valid, decodable image.") from exc

    # Correct EXIF orientation so the image displays upright.
    img = ImageOps.exif_transpose(img)
    # Convert CMYK / P / LA to RGB(A) for consistent downstream math.
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    return img


def process_image(data: bytes) -> ImageDerivatives:
    """
    Generate the optimized + thumbnail variants from the original
    bytes. The original `data` is NOT modified.
    """
    _require_pillow()
    img = _load_image(data)

    # Dimensions of the ORIGINAL (after orientation correction).
    original_w, original_h = img.size

    # Cap the total pixel count to bound memory/CPU on hostile
    # uploads (a decompression-bomb guard).
    max_pixels = original_w * original_h
    if max_pixels > settings.MAX_IMAGE_PIXELS:
        raise ImageProcessorError(
            f"Image is too large ({original_w}x{original_h}). "
            "Processing refused to protect server resources."
        )

    # --- OPTIMIZED variant ------------------------------------
    optimized = _downscale(img, settings.IMAGE_OPTIMIZED_MAX_DIMENSION)
    optimized_bytes, optimized_mime = _encode_for_output(
        optimized, settings.IMAGE_QUALITY
    )
    opt_w, opt_h = optimized.size

    # --- THUMBNAIL variant ------------------------------------
    thumb = _downscale(img, settings.IMAGE_THUMBNAIL_MAX_DIMENSION)
    thumb_bytes, thumb_mime = _encode_for_output(
        thumb, settings.IMAGE_QUALITY
    )
    th_w, th_h = thumb.size

    logger.info(
        "Image processed original=%dx%d optimized=%dx%d thumbnail=%dx%d",
        original_w, original_h, opt_w, opt_h, th_w, th_h,
    )

    return ImageDerivatives(
        optimized_bytes=optimized_bytes,
        optimized_mime=optimized_mime,
        thumbnail_bytes=thumb_bytes,
        thumbnail_mime=thumb_mime,
        width=opt_w,
        height=opt_h,
        thumbnail_width=th_w,
        thumbnail_height=th_h,
    )
