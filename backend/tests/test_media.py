# ============================================================
# Lentis Gallery — Media Upload & Access Tests (Phase 5)
# ------------------------------------------------------------
# Tests the REAL media system:
#   - Guest upload (photo/video) to a LIVE event
#   - Magic-byte validation (fake JPEG/PNG/MP4 accepted; junk rejected)
#   - Event must be LIVE (archived events reject uploads)
#   - File-size limits (oversized file -> 413)
#   - Server-side quota enforcement (3,000 photos / 500 videos)
#   - Guest listing + strict event isolation
#   - Guest delete (own media only)
#   - Host access (own events only)
#   - Admin access (any event)
#
# Uses the isolated in-memory test DB + a FAKE in-memory storage
# provider so no real files are written to disk during tests.
# ============================================================

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.services import media as media_service


# ------------------------------------------------------------
# Fake in-memory storage provider (no disk writes)
# ------------------------------------------------------------

class FakeStorage:
    """In-memory object store. Mirrors the StorageService interface."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_upload = False
        self.fail_delete = False

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        if self.fail_upload:
            from app.storage.base import StorageError
            raise StorageError("simulated upload failure")
        self.objects[key] = data

    def delete(self, key: str) -> None:
        if self.fail_delete:
            from app.storage.base import StorageError
            raise StorageError("simulated delete failure")
        self.objects.pop(key, None)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

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


# Minimal valid file payloads (magic bytes only; content needn't be a
# real decodable image/video — validation only checks signatures).
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
MP4_BYTES = b"\x00\x00\x00\x18ftyp" + b"\x00" * 100
EVIL_HTML = b"<html><script>alert(1)</script></html>"


@pytest.fixture()
def fake_storage() -> FakeStorage:
    """Patch the media service's storage with an in-memory fake."""
    fs = FakeStorage()
    media_service.get_storage_service = lambda: fs  # type: ignore
    return fs


# ============================================================
# UPLOAD
# ============================================================

def test_guest_uploads_photo(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["media_type"] == "PHOTO"
    assert body["status"] == "UPLOADED"
    assert body["original_filename"] == "photo.jpg"
    assert body["file_size"] == len(JPEG_BYTES)
    # The bytes were "stored".
    assert len(fake_storage.objects) == 1


def test_guest_uploads_video(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("clip.mp4", MP4_BYTES, "video/mp4")},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["media_type"] == "VIDEO"


def test_upload_requires_guest_token(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        files={"file": ("a.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert resp.status_code == 401


def test_upload_rejects_invalid_magic_bytes(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("evil.html", EVIL_HTML, "text/html")},
    )
    assert resp.status_code == 415
    assert len(fake_storage.objects) == 0


def test_upload_rejects_empty_file(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert resp.status_code == 415


def test_upload_rejected_when_event_not_live(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    # Archive the event -> not LIVE.
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    client.post(f"/api/admin/events/{evt['id']}/archive", headers=_auth_headers(admin))
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("a.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert resp.status_code == 400


def test_wrong_event_token_cannot_upload(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt_a = _make_live_event(client, db, "Event Alpha")
    evt_b = _make_live_event(client, db, "Event Beta")
    token_a = _register(client, evt_a["slug"])
    # Token from Event A must fail on Event B.
    resp = client.post(
        f"/api/events/{evt_b['slug']}/media",
        headers=_guest_headers(token_a),
        files={"file": ("a.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert resp.status_code == 401
    assert len(fake_storage.objects) == 0


# ============================================================
# FILE SIZE LIMIT
# ============================================================

def test_upload_oversized_photo_rejected(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    from app.core.config import settings
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    big = JPEG_BYTES + b"\x00" * (settings.MAX_IMAGE_SIZE_MB * 1024 * 1024)
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert resp.status_code == 413
    assert len(fake_storage.objects) == 0


# ============================================================
# QUOTA ENFORCEMENT (server-side)
# ============================================================

def test_photo_quota_enforced(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    from app.core.config import settings
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    # Grab the registering guest's id so our bulk rows have a valid
    # non-null guest_id foreign key.
    from app.models.guest import Guest
    guest_id = db.query(Guest).filter(Guest.event_id == evt["id"]).first().id
    # Fill the event up to the limit by inserting rows directly, then
    # verify the very next upload is rejected with 409.
    from app.models.media import Media, MediaType, MediaStatus
    for i in range(settings.MAX_PHOTOS_PER_EVENT):
        db.add(Media(
            event_id=evt["id"],
            guest_id=guest_id,
            original_filename="bulk.jpg",
            storage_key=f"bulk/{i}.jpg",
            media_type=MediaType.PHOTO,
            mime_type="image/jpeg",
            file_size=100,
            checksum="x",
            status=MediaStatus.UPLOADED,
        ))
    db.commit()

    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert resp.status_code == 409
    assert len(fake_storage.objects) == 0


def test_get_event_media_usage(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    from app.core.config import settings
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])

    # Upload 2 photos and 1 video.
    client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("p1.jpg", JPEG_BYTES, "image/jpeg")},
    )
    client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("p2.png", PNG_BYTES, "image/png")},
    )
    client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("v1.mp4", MP4_BYTES, "video/mp4")},
    )

    usage = media_service.get_event_media_usage(db, evt["id"])
    assert usage.photo_count == 2
    assert usage.video_count == 1
    assert usage.max_photos == settings.MAX_PHOTOS_PER_EVENT
    assert usage.max_videos == settings.MAX_VIDEOS_PER_EVENT
    assert usage.photo_remaining == settings.MAX_PHOTOS_PER_EVENT - 2
    assert usage.video_remaining == settings.MAX_VIDEOS_PER_EVENT - 1


# ============================================================
# GUEST LISTING + EVENT ISOLATION
# ============================================================

def test_guest_lists_only_own_media(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"], "John")
    other_token = _register(client, evt["slug"], "Jane")

    client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("john.jpg", JPEG_BYTES, "image/jpeg")},
    )
    client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(other_token),
        files={"file": ("jane.jpg", JPEG_BYTES, "image/jpeg")},
    )

    resp = client.get(
        f"/api/events/{evt['slug']}/media/me",
        headers=_guest_headers(token),
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["original_filename"] == "john.jpg"


def test_guest_listing_requires_token(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    resp = client.get(f"/api/events/{evt['slug']}/media/me")
    assert resp.status_code == 401


# ============================================================
# GUEST DELETE (own media only)
# ============================================================

def test_guest_can_delete_own_media(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    up = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("mine.jpg", JPEG_BYTES, "image/jpeg")},
    )
    media_id = up.json()["id"]
    assert len(fake_storage.objects) == 1

    resp = client.delete(
        f"/api/events/{evt['slug']}/media/{media_id}",
        headers=_guest_headers(token),
    )
    assert resp.status_code == 204
    assert len(fake_storage.objects) == 0


def test_guest_cannot_delete_others_media(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token_john = _register(client, evt["slug"], "John")
    token_jane = _register(client, evt["slug"], "Jane")

    up = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token_john),
        files={"file": ("john.jpg", JPEG_BYTES, "image/jpeg")},
    )
    media_id = up.json()["id"]

    # Jane tries to delete John's media -> 404.
    resp = client.delete(
        f"/api/events/{evt['slug']}/media/{media_id}",
        headers=_guest_headers(token_jane),
    )
    assert resp.status_code == 404
    # John's media still exists.
    assert len(fake_storage.objects) == 1


# ============================================================
# HOST ACCESS (own events only)
# ============================================================

def test_host_lists_own_event_media(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("a.jpg", JPEG_BYTES, "image/jpeg")},
    )
    host = db.query(User).filter(User.role == UserRole.HOST).first()
    resp = client.get(
        f"/api/host/events/{evt['id']}/media",
        headers=_auth_headers(host),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_host_cannot_list_other_hosts_event(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db, "Event Alpha")
    # Create a SECOND host who does NOT own this event.
    other_host = _create_user(db, "otherhost@test.gallery", UserRole.HOST)
    resp = client.get(
        f"/api/host/events/{evt['id']}/media",
        headers=_auth_headers(other_host),
    )
    assert resp.status_code == 404


# ============================================================
# ADMIN ACCESS (any event)
# ============================================================

def test_admin_lists_any_event_media(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("a.jpg", JPEG_BYTES, "image/jpeg")},
    )
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    resp = client.get(
        f"/api/admin/events/{evt['id']}/media",
        headers=_auth_headers(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_admin_media_requires_admin_role(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    host = db.query(User).filter(User.role == UserRole.HOST).first()
    resp = client.get(
        f"/api/admin/events/{evt['id']}/media",
        headers=_auth_headers(host),
    )
    assert resp.status_code == 403


# ============================================================
# STORAGE FAILURE HANDLING
# ============================================================

def test_upload_rolls_back_metadata_on_storage_failure(
    client: TestClient, db: Session, fake_storage: FakeStorage
):
    evt = _make_live_event(client, db)
    token = _register(client, evt["slug"])
    fake_storage.fail_upload = True
    resp = client.post(
        f"/api/events/{evt['slug']}/media",
        headers=_guest_headers(token),
        files={"file": ("a.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert resp.status_code == 502
    # No media row left behind.
    from app.models.media import Media
    assert db.query(Media).count() == 0
