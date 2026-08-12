# ============================================================
# Lentis Gallery — Video Processor (Phase 6)
# ------------------------------------------------------------
# Uses FFmpeg (a system binary, NOT pure Python) to derive an
# OPTIMIZED playback MP4 (H.264 + AAC) and a POSTER frame from a
# PRESERVED ORIGINAL. The original file is NEVER modified.
#
# WHY FFmpeg?
#   Video encoding is a low-level, CPU-heavy task. FFmpeg is the
#   industry-standard library for it. Reimplementing H.264 encoding
#   in Python would be slow, error-prone, and insecure. We shell out
#   to FFmpeg's CLI using an ARGUMENT ARRAY (never a shell string) so
#   no user-controlled input can ever be interpreted as a command.
#
# ENCODING SETTINGS (documented):
#   video  : libx264 (H.264, universally playable)
#   audio  : aac
#   container: mp4 (fast start / progressive download)
#   quality: CRF (constant rate factor) — we keep the configured CRF
#            (default 23) which is FFmpeg's "good quality, reasonable
#            size" default. We do NOT slam the bitrate to an arbitrary
#            low number and destroy quality.
#   preset : settings.VIDEO_PRESET (default "medium").
#   faststart places the moov atom at the front so the browser can
#            start playing before the whole file downloads.
#
# POSTER FRAME:
#   We extract a frame at ~1 second (or the first available frame for
#   videos shorter than 1s) and save it as a JPEG. If poster
#   extraction fails we DO NOT fail the whole item — the caller
#   records the poster failure and continues.
# ============================================================

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VideoDerivatives:
    """The derived assets a video processor produces on disk."""
    optimized_path: Path
    optimized_mime: str  # always video/mp4
    poster_path: Path | None
    poster_mime: str | None  # image/jpeg
    width: int
    height: int
    duration_seconds: float
    has_audio: bool


class VideoProcessorError(Exception):
    """Raised when a video cannot be processed safely."""


def _require_ffmpeg() -> str:
    """Return the ffmpeg binary path or raise a clear error."""
    path = shutil.which("ffmpeg")
    if not path:
        raise VideoProcessorError(
            "FFmpeg is not installed or not on PATH. Install FFmpeg and "
            "re-run processing. See backend/README.md for instructions."
        )
    return path


def _run(cmd: list[str], timeout: int | None = None) -> None:
    """
    Run a command safely as an ARGUMENT ARRAY (no shell). Raises
    VideoProcessorError on a non-zero exit so callers can record a
    clean failure.
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise VideoProcessorError("FFmpeg binary not found.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoProcessorError("Video processing timed out.") from exc

    if proc.returncode != 0:
        # Log the stderr for the operator but do NOT expose it to
        # guests (we only store a safe summary in the DB).
        stderr = proc.stderr.decode("utf-8", errors="replace")[-2000:]
        logger.error("FFmpeg failed (exit %d): %s", proc.returncode, stderr)
        raise VideoProcessorError(
            "FFmpeg could not process this video (invalid or unsupported file)."
        )


def _probe(input_path: Path) -> dict:
    """
    Use ffprobe to read the video's metadata (duration, resolution,
    audio presence). Raises VideoProcessorError if the file is not a
    decodable video.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise VideoProcessorError(
            "FFprobe is not installed. Install FFmpeg (which includes "
            "ffprobe) to process videos."
        )

    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(input_path),
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError as exc:
        raise VideoProcessorError("FFmpeg/ffprobe not found.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoProcessorError("Video probing timed out.") from exc

    if proc.returncode != 0:
        raise VideoProcessorError(
            "This video could not be read (invalid or corrupted file)."
        )

    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise VideoProcessorError("Could not parse video metadata.") from exc

    # Find the first video stream for resolution/duration.
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if not video_stream:
        raise VideoProcessorError("No video stream found in this file.")

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)

    # Duration: prefer the stream duration, fall back to format.
    duration = float(video_stream.get("duration") or 0)
    if not duration:
        duration = float(data.get("format", {}).get("duration") or 0)

    has_audio = any(
        s.get("codec_type") == "audio" for s in data.get("streams", [])
    )

    return {
        "width": width,
        "height": height,
        "duration": duration,
        "has_audio": has_audio,
    }


def process_video(input_path: Path, output_dir: Path) -> VideoDerivatives:
    """
    Generate the OPTIMIZED MP4 + a POSTER frame from a local copy of
    the original. Writes outputs into `output_dir` (a temp dir the
    caller cleans up). The original `input_path` is never modified.
    """
    ffmpeg = _require_ffmpeg()

    # 1) Probe the original to get metadata + validate it's a video.
    info = _probe(input_path)
    duration = info["duration"]

    if duration <= 0:
        raise VideoProcessorError("Could not determine video duration.")
    if duration > settings.MAX_VIDEO_DURATION_SECONDS:
        raise VideoProcessorError(
            f"Video is longer than the allowed "
            f"{settings.MAX_VIDEO_DURATION_SECONDS}s limit."
        )

    # 2) Build the OPTIMIZED playback MP4 (H.264 + AAC).
    optimized_path = output_dir / "optimized.mp4"
    cmd = [
        ffmpeg,
        "-y",  # overwrite our temp output if it exists
        "-i", str(input_path),
        "-map", "0:v:0",
    ]
    if info["has_audio"]:
        cmd += ["-map", "0:a:0?"]
    cmd += [
        "-c:v", "libx264",
        "-crf", str(settings.VIDEO_CRF),
        "-preset", settings.VIDEO_PRESET,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]
    if info["has_audio"]:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    cmd += [str(optimized_path)]

    _run(cmd)

    # 3) Extract a POSTER frame (as near 1s as possible).
    poster_path: Path | None = None
    poster_mime: str | None = None
    try:
        # Use a small, safe timestamp: 1s always exists for videos
        # >= 1s; for shorter videos we fall back to the first frame.
        ts = min(1.0, max(0.0, duration - 0.1)) if duration > 0.2 else 0.0
        poster = output_dir / "poster.jpg"
        poster_cmd = [
            ffmpeg,
            "-y",
            "-ss", f"{ts:.3f}",
            "-i", str(input_path),
            "-frames:v", "1",
            "-q:v", "2",  # high-quality JPEG
            str(poster),
        ]
        _run(poster_cmd)
        if poster.exists() and poster.stat().st_size > 0:
            poster_path = poster
            poster_mime = "image/jpeg"
    except VideoProcessorError as exc:
        # Poster failure must NOT fail the whole media item. We log
        # it; the caller records a poster-failure note and continues.
        logger.warning("Poster extraction failed (continuing): %s", exc)
        poster_path = None
        poster_mime = None

    logger.info(
        "Video processed width=%d height=%d duration=%.2f audio=%s poster=%s",
        info["width"], info["height"], duration, info["has_audio"],
        poster_path is not None,
    )

    return VideoDerivatives(
        optimized_path=optimized_path,
        optimized_mime="video/mp4",
        poster_path=poster_path,
        poster_mime=poster_mime,
        width=info["width"],
        height=info["height"],
        duration_seconds=duration,
        has_audio=info["has_audio"],
    )
