# ============================================================
# Lentis Gallery — Guest Registration & Session Tests (Phase 4)
# ------------------------------------------------------------
# Tests the REAL guest system:
#   - Public guest registration (name only) for a LIVE event
#   - Event must exist (404) and be LIVE (400)
#   - Name validation (empty / whitespace / too long → 422)
#   - Session token minting: randomness + only-hash stored
#   - GET /guests/me validates the token
#   - STRICT event isolation: a token for Event A fails on Event B
#   - Invalid / revoked / expired token rejection (401)
#   - Session revocation (logout) makes the token unusable
#
# Uses the isolated in-memory test DB from conftest.py.
# ============================================================

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_guest_token,
)
from app.models.event import Event, EventStatus
from app.models.guest import GuestSession, GuestSessionStatus
from app.models.user import User, UserRole
from app.services import guests as guest_service


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _create_user(db: Session, email: str, role: UserRole = UserRole.HOST) -> User:
    """Create a user directly in the test DB (bypasses the API)."""
    from app.core.security import hash_password
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
    """Build an Authorization header for a user's access token."""
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def _make_live_event(client: TestClient, db: Session, name: str = "TARAGOLD 2026") -> dict:
    """Create a LIVE event via the admin API and return its JSON.

    This helper is safe to call multiple times within one test: it only
    creates the admin/host users if they don't already exist (the
    clean_tables autouse fixture wipes rows between tests, so each test
    starts fresh).
    """
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
    assert resp.status_code == 201
    return resp.json()


def _register_guest(client: TestClient, slug: str, name: str = "John Doe"):
    """Register a guest and return the full response object."""
    return client.post(f"/api/events/{slug}/guests", json={"name": name})


def _register_ok(client: TestClient, slug: str, name: str = "John Doe"):
    """Register a guest and return (json, raw_token)."""
    resp = _register_guest(client, slug, name)
    assert resp.status_code == 201, resp.text
    return resp.json(), resp.json()["session"]["session_token"]


def _guest_headers(token: str) -> dict[str, str]:
    return {"X-Guest-Token": token}


def _make_ended_event(client: TestClient, db: Session, name: str = "Ended Event") -> dict:
    """Create an event then archive it (status=ARCHIVED) and return JSON."""
    evt = _make_live_event(client, db, name)
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    client.post(f"/api/admin/events/{evt['id']}/archive", headers=_auth_headers(admin))
    # Re-fetch to confirm it's archived.
    resp = client.get(f"/api/events/{evt['slug']}/public")
    return resp.json()


# ============================================================
# REGISTRATION
# ============================================================

def test_guest_can_register_for_live_event(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    body, _ = _register_ok(client, evt["slug"], "Amara Okafor")
    assert body["guest"]["name"] == "Amara Okafor"
    assert body["guest"]["event_id"] == evt["id"]
    assert body["session"]["session_token"]  # raw token present
    assert body["session"]["expires_at"]  # expiry present


def test_guest_name_is_trimmed(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    body, _ = _register_ok(client, evt["slug"], "  John   Doe  ")
    assert body["guest"]["name"] == "John Doe"


def test_register_for_unknown_slug_404(client: TestClient):
    resp = _register_guest(client, "does-not-exist", "John")
    assert resp.status_code == 404


def test_register_for_non_live_event_400(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    # Archive it -> status ARCHIVED, not LIVE.
    client.post(f"/api/admin/events/{evt['id']}/archive", headers=_auth_headers(admin))
    resp = _register_guest(client, evt["slug"], "John")
    assert resp.status_code == 400


def test_register_empty_name_rejected(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    resp = client.post(f"/api/events/{evt['slug']}/guests", json={"name": ""})
    assert resp.status_code == 422


def test_register_whitespace_name_rejected(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    resp = client.post(f"/api/events/{evt['slug']}/guests", json={"name": "   "})
    assert resp.status_code == 422


def test_register_missing_name_rejected(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    resp = client.post(f"/api/events/{evt['slug']}/guests", json={})
    assert resp.status_code == 422


def test_register_name_too_long_rejected(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    resp = client.post(f"/api/events/{evt['slug']}/guests", json={"name": "X" * 500})
    assert resp.status_code == 422


# ============================================================
# TOKEN SECURITY
# ============================================================

def test_session_token_is_random_and_unique(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    _, t1 = _register_ok(client, evt["slug"], "Guest One")
    _, t2 = _register_ok(client, evt["slug"], "Guest Two")
    assert t1 != t2
    # Both are long opaque strings.
    assert len(t1) >= 40
    assert len(t2) >= 40


def test_only_hash_of_token_stored_in_db(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    _, raw_token = _register_ok(client, evt["slug"], "John")
    # The raw token must NOT appear anywhere in the DB.
    stored = db.query(GuestSession).all()
    assert len(stored) == 1
    assert stored[0].token_hash == hash_guest_token(raw_token)
    assert stored[0].token_hash != raw_token
    # No session row contains the raw token.
    for row in stored:
        assert raw_token not in (row.token_hash,)


def test_multiple_guests_can_register_independently(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    _register_ok(client, evt["slug"], "Guest A")
    _register_ok(client, evt["slug"], "Guest B")
    _register_ok(client, evt["slug"], "Guest C")
    assert db.query(GuestSession).count() == 3


# ============================================================
# GET /guests/me
# ============================================================

def test_me_with_valid_token(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    body, token = _register_ok(client, evt["slug"], "John Doe")
    resp = client.get(f"/api/events/{evt['slug']}/guests/me", headers=_guest_headers(token))
    assert resp.status_code == 200
    assert resp.json()["guest"]["name"] == "John Doe"
    assert resp.json()["guest"]["event_id"] == evt["id"]
    assert resp.json()["session_status"] == "ACTIVE"


def test_me_without_token_401(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    resp = client.get(f"/api/events/{evt['slug']}/guests/me")
    assert resp.status_code == 401


def test_me_with_invalid_token_401(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    resp = client.get(
        f"/api/events/{evt['slug']}/guests/me",
        headers=_guest_headers("not-a-real-token"),
    )
    assert resp.status_code == 401


# ============================================================
# EVENT ISOLATION
# ============================================================

def test_session_for_event_a_fails_on_event_b(client: TestClient, db: Session):
    evt_a = _make_live_event(client, db, "Event Alpha")
    evt_b = _make_live_event(client, db, "Event Beta")
    _, token_a = _register_ok(client, evt_a["slug"], "John")
    # John's token is valid on Event A.
    ok = client.get(f"/api/events/{evt_a['slug']}/guests/me", headers=_guest_headers(token_a))
    assert ok.status_code == 200
    # The SAME token must FAIL on Event B (strict isolation).
    bad = client.get(f"/api/events/{evt_b['slug']}/guests/me", headers=_guest_headers(token_a))
    assert bad.status_code == 401


def test_revoked_session_rejected(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    _, token = _register_ok(client, evt["slug"], "John")
    # Revoke.
    revoke = client.post(
        f"/api/events/{evt['slug']}/guests/session/revoke",
        headers=_guest_headers(token),
    )
    assert revoke.status_code == 204
    # Now the token is dead.
    resp = client.get(f"/api/events/{evt['slug']}/guests/me", headers=_guest_headers(token))
    assert resp.status_code == 401


def test_expired_session_rejected(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    _, token = _register_ok(client, evt["slug"], "John")
    # Force the session to be expired in the DB (simulating time passing).
    session = db.query(GuestSession).one()
    session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    session.status = GuestSessionStatus.EXPIRED
    db.commit()
    resp = client.get(f"/api/events/{evt['slug']}/guests/me", headers=_guest_headers(token))
    assert resp.status_code == 401


# ============================================================
# REVOCATION
# ============================================================

def test_revoke_requires_valid_token(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    resp = client.post(
        f"/api/events/{evt['slug']}/guests/session/revoke",
        headers=_guest_headers("bogus"),
    )
    assert resp.status_code == 401


def test_revoke_then_reuse_returns_401(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    _, token = _register_ok(client, evt["slug"], "John")
    client.post(
        f"/api/events/{evt['slug']}/guests/session/revoke",
        headers=_guest_headers(token),
    )
    # Reusing the revoked token fails.
    resp = client.get(f"/api/events/{evt['slug']}/guests/me", headers=_guest_headers(token))
    assert resp.status_code == 401


# ============================================================
# SERVICE LAYER (unit-level)
# ============================================================

def test_service_creates_guest_and_session(client: TestClient, db: Session):
    evt = _make_live_event(client, db)
    slug = evt["slug"]
    from app.schemas.guest import GuestRegister
    payload = GuestRegister(name="  Service  Person ")
    guest, session, raw_token = guest_service.register_guest(db, slug, payload)
    assert guest.name == "Service Person"
    assert guest.event_id == evt["id"]
    assert session.event_id == evt["id"]
    assert session.status == GuestSessionStatus.ACTIVE
    assert session.token_hash == hash_guest_token(raw_token)
    assert session.token_hash != raw_token
    # SQLite (test DB) returns naive datetimes; normalize before comparing.
    expiry = session.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    assert expiry > datetime.now(timezone.utc)


def test_service_get_my_guest_event_scoped(client: TestClient, db: Session):
    evt_a = _make_live_event(client, db, "Event Alpha")
    evt_b = _make_live_event(client, db, "Event Beta")
    _, token = _register_ok(client, evt_a["slug"], "John")
    # Valid on Event A.
    guest, session = guest_service.get_my_guest(db, evt_a["slug"], token)
    assert guest.name == "John"
    # Same token must fail on Event B.
    with pytest.raises(Exception):
        guest_service.get_my_guest(db, evt_b["slug"], token)


def test_service_register_for_ended_event_raises(client: TestClient, db: Session):
    evt = _make_ended_event(client, db)
    from app.schemas.guest import GuestRegister
    from fastapi import HTTPException
    payload = GuestRegister(name="John")
    with pytest.raises(HTTPException) as exc:
        guest_service.register_guest(db, evt["slug"], payload)
    assert exc.value.status_code == 400
