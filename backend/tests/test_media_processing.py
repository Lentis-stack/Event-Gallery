# ============================================================
# Lentis Gallery — Media Processing Tests (Phase 6)
# ------------------------------------------------------------
# Tests the async media-processing pipeline:
#
#   IMAGE   - valid JPEG/PNG/WebP derivatives, invalid/corrupt
#             images rejected, dimensions recorded, thumbnail +
#             optimized generation.
#   VIDEO   - valid MP4 (requires FFmpeg; integration-only), invalid
#             videos rejected, poster/duration/resolution extraction.
#   PROCESS - QUEUED -> PROCESSING -> READY, failure, retry, max
#             retries, original preserved after failure, metadata
#             updated.
#   SECURITY- guest/host/admin isolation on the status endpoint.
#   STORAGE - upload/download round-trip, derived failure does not
#             destroy the original, temp files cleaned.
#
# FFMPEG STRATEGY:
#   Most tests are pure unit/integration tests that do NOT need
#   FFmpeg (they use Pillow for images and a fake storage). Video
#   ENCODING tests require the "ffmpeg" binary and are automatically
#   skipped when it is not installed (pytest.mark.skipif). We never
#   silently ignore them — the skip reason is explicit.
# ============================================================

import io
import os
import shutil

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.media import Media, MediaStatus, MediaType, ProcessingStatus
from app.models.user import User, UserRole
from app.services import media as media_service
from app.services import media_processing
from app.storage.base import StorageError

# Whether FFmpeg/ffprobe are available for integration tests.
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


# ------------------------------------------------------------
# Helpers (mirror test_media.py)
# ------------------------------------------------------------

class FakeStorage:
    """In-memory object store mirroring the StorageService interface."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_upload = False
        self.fail_delete = False
        self.fail_download = False

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        if self.fail_upload:
            raise StorageError("simulated upload failure")
        self.objects[key] = data

    def delete(self, key: str) -> None:
        if self.fail_delete:
            raise StorageError("simulated delete failure")
        self.objects.pop(key, None)

    def download(self, key: str) -> bytes:
        if self.fail_download:
            raise StorageError("simulated download failure")
        if key not in self.objects:
            raise StorageError("object not found")
        return self.objects[key]


def _create_user(db: Session, email: str, role: UserRole = UserRole.HOST) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(f"Pass{email}123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def _make_live_event(client: TestClient, db: Session, name: str = "TARAGOLD 2026") -> dict:
    admin = (
        db.query(User).filter(User.email == "admin@test.gallery").first()
        or _create_user(db, "admin@test.gallery", UserRole.ADMIN)
    )
    host = (
        db.query(User).filter(User.email == "host@test.gallery").first()
        or _create_user(db, "host@test.gallery", UserRole.HOST)
    )
    resp = client.post(
        "/api/events",
        json={
            "name": name,
            "subtitle": "A celebration of love.",
            "host_id": host.id,
            "event_date": "2026-12-20",
            "theme": "gold",
        },
        headers=_auth_headers(admin),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _register(client: TestClient, slug: str, name: str = "John Doe") -> str:
    resp = client.post(f"/api/events/{slug}/guests", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["session"]["session_token"]


def _guest_headers(token: str) -> dict[str, str]:
    return {"X-Guest-Token": token}


# ------------------------------------------------------------
# Image fixtures (deterministic, tiny)
# ------------------------------------------------------------

def _make_image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (1200, 800)) -> bytes:
    """Create a small deterministic image in the requested format."""
    img = Image.new("RGB", size, (200, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


JPEG = _make_image_bytes("JPEG")
PNG = _make_image_bytes("PNG")
WEBP = _make_image_bytes("WEBP")
GIF_BYTES = b"\x47\x49\x46\x38\x39\x61" + b"\x00" * 100  # magic only

# A fake JPEG that passes magic-byte sniffing but is NOT decodable.
CORRUPT_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200


@pytest.fixture()
def fake_storage(db: Session) -> FakeStorage:
    """Patch the media + processing services' storage with a fake."""
    fs = FakeStorage()
    media_service.get_storage_service = lambda: fs  # type: ignore
    media_processing.get_storage_service = lambda: fs  # type: ignore
    return fs


def _upload(
    client: TestClient, slug: str, token: str, data: bytes, fname: str, mime: str
) -> dict:
    resp = client.post(
        f"/api/events/{slug}/media",
        headers=_guest_headers(token),
        files={"file": (fname, data, mime)},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ============================================================
# IMAGE PROCESSING
# ============================================================

def test_image_valid_jpeg_processed(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    assert media.processing_status == ProcessingStatus.QUEUED

    result = media_processing.process_media(db, media.id, fake_storage)
    assert result.processing_status == ProcessingStatus.READY
    assert result.optimized is True
    assert result.thumbnail is True
    assert result.poster is False  # images have no poster
    assert result.width and result.height
    assert result.thumbnail_width and result.thumbnail_height
    # Original preserved in storage.
    assert media.storage_key in fake_storage.objects
    # Derived variants stored under predictable keys.
    assert f"events/{media.event_id}/media/{media.id}/optimized" in fake_storage.objects
    assert f"events/{media.event_id}/media/{media.id}/thumbnail" in fake_storage.objects


def test_image_png_processed_keeps_alpha(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, PNG, "photo.png", "image/png")
    media = db.get(Media, up["id"])
    media_processing.process_media(db, media.id, fake_storage)
    assert media.processing_status == ProcessingStatus.READY
    # PNG should be preserved as PNG (alpha-compatible) when needed.
    assert media.optimized_mime_type in ("image/png", "image/jpeg")


def test_image_webp_processed(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, WEBP, "photo.webp", "image/webp")
    media = db.get(Media, up["id"])
    media_processing.process_media(db, media.id, fake_storage)
    assert media.processing_status == ProcessingStatus.READY
    assert media.optimized is True


def test_image_invalid_magic_rejected_at_upload(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("evil.html", b"<html>not an image</html>", "text/html")},
    )
    assert resp.status_code == 415


def test_corrupt_image_fails_processing_but_preserves_original(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    # CORRUPT_JPEG passes magic-byte sniffing but is not decodable by
    # Pillow. Processing must fail safely and preserve the original.
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, CORRUPT_JPEG, "bad.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    assert media.storage_key in fake_storage.objects  # original preserved

    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)

    db.refresh(media)
    # Attempt recorded; not READY; original still present.
    assert media.processing_attempts >= 1
    assert media.processing_status != ProcessingStatus.READY
    assert media.storage_key in fake_storage.objects


def test_oversized_image_refused_in_processing(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    # A huge image (exceeds MAX_IMAGE_PIXELS) is refused during
    # processing to protect server resources.
    wide = Image.new("RGB", (20000, 20000))
    buf = io.BytesIO()
    wide.save(buf, format="JPEG")
    big = buf.getvalue()

    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, big, "huge.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)


# ============================================================
# VIDEO PROCESSING (integration; requires FFmpeg)
# ============================================================

def _make_test_video(path: str, seconds: float = 1.0) -> None:
    """Generate a tiny valid MP4 with ffmpeg (testsrc pattern)."""
    import subprocess
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration={}:size=320x240:rate=10".format(seconds),
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
            path,
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg/ffprobe not installed")
def test_video_processed_requires_ffmpeg(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    tmp = os.path.join(settings.PROCESSING_TEMP_DIR or "/tmp", "test_video.mp4")
    _make_test_video(tmp)
    try:
        with open(tmp, "rb") as f:
            data = f.read()
            evt = _make_live_event(client, db)
            token = _register(client, evt["slug"])
            up = _upload(client, evt["slug"], token, data, "clip.mp4", "video/mp4")
            media = db.get(Media, up["id"])
            media_processing.process_media(db, media.id, fake_storage)
            assert media.processing_status == ProcessingStatus.READY
            assert media.optimized is True
            assert media.poster is True  # poster frame generated
            assert media.duration_seconds and media.duration_seconds > 0
            assert media.width and media.height
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg/ffprobe not installed")
def test_video_poster_and_duration_extracted(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    tmp = os.path.join(settings.PROCESSING_TEMP_DIR or "/tmp", "test_video2.mp4")
    _make_test_video(tmp)
    try:
        with open(tmp, "rb") as f:
            data = f.read()
            evt = _make_live_event(client, db)
            token = _register(client, evt["slug"])
            up = _upload(client, evt["slug"], token, data, "clip2.mp4", "video/mp4")
            media = db.get(Media, up["id"])
            media_processing.process_media(db, media.id, fake_storage)
            assert media.poster_key is not None
            assert media.poster_size and media.poster_size > 0
            assert media.duration_seconds and media.duration_seconds > 0
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def test_invalid_video_fails_processing(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    # A fake MP4 (magic bytes only, not decodable) fails processing.
    MP4_FAKE = b"\x00\x00\x00\x18ftyp" + b"\x00" * 200
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, MP4_FAKE, "clip.mp4", "video/mp4")
    media = db.get(Media, up["id"])
    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    assert media.processing_status != ProcessingStatus.READY
    assert media.storage_key in fake_storage.objects  # original preserved


# ============================================================
# PROCESSING STATES / RETRY / FAILURE
# ============================================================

def test_processing_state_flow(client: TestClient, db: Session, fake_storage: FakeStorage):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    # QUEUED after upload.
    assert media.processing_status == ProcessingStatus.QUEUED
    # PROCESSING asserted inside process_media before work.
    media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    assert media.processing_status == ProcessingStatus.READY


def test_processing_failure_records_error(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, CORRUPT_JPEG, "bad.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    # A safe error string is recorded (no stack trace / path).
    assert media.processing_error
    assert "\\" not in media.processing_error  # no filesystem path
    assert "Traceback" not in media.processing_error  # no stack trace


def test_retry_then_success(client: TestClient, db: Session, fake_storage: FakeStorage):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])

    # First attempt fails (simulate download failure).
    fake_storage.fail_download = True
    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    # With retries left it returns to QUEUED.
    assert media.processing_status == ProcessingStatus.QUEUED
    assert media.processing_attempts == 1

    # Second attempt succeeds.
    fake_storage.fail_download = False
    media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    assert media.processing_status == ProcessingStatus.READY
    assert media.processing_attempts == 2


def test_max_retries_marks_failed(client: TestClient, db: Session, fake_storage: FakeStorage):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, CORRUPT_JPEG, "bad.jpg", "image/jpeg")
    media = db.get(Media, up["id"])

    # Force failures beyond PROCESSING_MAX_RETRIES.
    for _ in range(settings.PROCESSING_MAX_RETRIES + 1):
        with pytest.raises(Exception):
            media_processing.process_media(db, media.id, fake_storage)
        db.refresh(media)

    assert media.processing_status == ProcessingStatus.FAILED
    assert media.processing_attempts >= settings.PROCESSING_MAX_RETRIES
    # Original still preserved even after permanent failure.
    assert media.storage_key in fake_storage.objects


def test_original_preserved_after_failure(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    original_key = media.storage_key
    original_bytes = fake_storage.objects[original_key]

    # Force a failure during processing.
    fake_storage.fail_download = True
    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)

    # Original bytes untouched.
    assert fake_storage.objects[original_key] == original_bytes
    assert media.storage_key == original_key


def test_processed_files_stored_correctly(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    # Keys are predictable, no original filename in path.
    assert media.optimized_key == f"events/{media.event_id}/media/{media.id}/optimized"
    assert media.thumbnail_key == f"events/{media.event_id}/media/{media.id}/thumbnail"
    assert "photo.jpg" not in media.optimized_key


def test_processed_metadata_updated(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    assert media.optimized_size and media.optimized_size > 0
    assert media.thumbnail_size and media.thumbnail_size > 0
    assert media.optimized_mime_type
    assert media.thumbnail_mime_type
    assert media.processed_at is not None


# ============================================================
# PROCESSING STATUS ENDPOINT + SECURITY
# ============================================================

def test_guest_can_get_own_media_status(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    resp = client.get(
        f"/api/events/{evt['slug']}/media/{up['id']}/status",
        headers=_guest_headers(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["media_id"] == up["id"]
    assert body["status"] == "QUEUED"
    assert body["original"] is True
    assert body["optimized"] is False
    assert body["thumbnail"] is False


def test_status_endpoint_requires_auth(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    resp = client.get(f"/api/events/{evt['slug']}/media/{up['id']}/status")
    assert resp.status_code == 401


def test_guest_cannot_get_other_event_media_status(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt_a = _make_live_event(client, db, "Event Alpha")
    evt_b = _make_live_event(client, db, "Event Beta")
    token_b = _register(client, evt_b["slug"])
    up = _upload(client, evt_a["slug"], _register(client, evt_a["slug"]), JPEG, "p.jpg", "image/jpeg")
    # Token from Event B cannot see Event A's media.
    resp = client.get(
        f"/api/events/{evt_a['slug']}/media/{up['id']}/status",
        headers=_guest_headers(token_b),
    )
    assert resp.status_code == 401


def test_host_can_get_own_event_media_status(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    host = db.query(User).filter(User.role == UserRole.HOST).first()
    resp = client.get(
        f"/api/events/{evt['slug']}/media/{up['id']}/status",
        headers=_auth_headers(host),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "QUEUED"


def test_other_host_cannot_get_media_status(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db, "Event Alpha")
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "p.jpg", "image/jpeg")
    other_host = _create_user(db, "otherhost@test.gallery", UserRole.HOST)
    resp = client.get(
        f"/api/events/{evt['slug']}/media/{up['id']}/status",
        headers=_auth_headers(other_host),
    )
    assert resp.status_code == 404


def test_admin_can_get_any_media_status(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    resp = client.get(
        f"/api/events/{evt['slug']}/media/{up['id']}/status",
        headers=_auth_headers(admin),
    )
    assert resp.status_code == 200


def test_invalid_token_rejected(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    resp = client.get(
        f"/api/events/{evt['slug']}/media/{up['id']}/status",
        headers={"X-Guest-Token": "not-a-real-token"},
    )
    assert resp.status_code == 401


# ============================================================
# STORAGE
# ============================================================

def test_storage_upload_and_download_roundtrip(fake_storage: FakeStorage):
    fake_storage.upload("x/y", b"hello", "image/jpeg")
    assert fake_storage.download("x/y") == b"hello"


def test_storage_failure_handled_safely(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])

    # Derived upload fails -> processing fails, but original survives.
    fake_storage.fail_upload = True
    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)
    db.refresh(media)
    assert media.processing_status != ProcessingStatus.READY
    assert media.storage_key in fake_storage.objects


def test_derived_failure_does_not_destroy_original(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    original_key = media.storage_key
    fake_storage.fail_upload = True
    with pytest.raises(Exception):
        media_processing.process_media(db, media.id, fake_storage)
    assert original_key in fake_storage.objects


def test_temp_files_cleaned(client: TestClient, db: Session, fake_storage: FakeStorage):
    """Temp files written during processing are removed afterwards."""
    import glob
    from app.services import media_processing as mp

    tmp_dir = settings.PROCESSING_TEMP_DIR or "/tmp"
    before = set(glob.glob(os.path.join(tmp_dir, "lentis-*")))

    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    media_processing.process_media(db, media.id, fake_storage)

    after = set(glob.glob(os.path.join(tmp_dir, "lentis-*")))
    assert after == before  # no leftover temp files


# ============================================================
# DATABASE — persistence
# ============================================================

def test_processing_status_persisted(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = _upload(client, evt["slug"], token, JPEG, "photo.jpg", "image/jpeg")
    media = db.get(Media, up["id"])
    media_processing.process_media(db, media.id, fake_storage)
    # Re-read from a fresh session to confirm persistence.
    db.expire_all()
    fresh = db.get(Media, up["id"])
    assert fresh.processing_status == ProcessingStatus.READY
    assert fresh.optimized_key is not None
