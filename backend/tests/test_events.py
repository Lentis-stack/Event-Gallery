# ============================================================
# Lentis Gallery — Event Management Tests (Phase 3)
# ------------------------------------------------------------
# Tests the REAL event management system:
#   - Admin: create / list / view / update / archive events
#   - Host: list / view / update ONLY their own events
#   - Authorization: hosts blocked from admin routes, ownership
#     enforced, unauthenticated rejected
#   - Validation: bad host, duplicate slug, missing event, invalid
#     status transitions
#   - Public: guest event lookup (no auth), safe fields only
#   - Persistence: events survive session/request lifecycle
#
# Uses the isolated in-memory test DB from conftest.py.
# ============================================================

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.event import Event, EventStatus, ThemeChoice
from app.models.user import User, UserRole
from app.services import events as event_service


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _create_user(db: Session, email: str, role: UserRole = UserRole.HOST) -> User:
    """Create a user directly in the test DB (bypasses the API)."""
    import sys
    sys.path.insert(0, ".")
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


def _admin_token(db: Session) -> User:
    """Create + return an admin user."""
    return _create_user(db, "admin@test.gallery", UserRole.ADMIN)


def _host_token(db: Session, email: str = "host@test.gallery") -> User:
    """Create + return a HOST user."""
    return _create_user(db, email, UserRole.HOST)


def _create_event_payload(host_id: str, name: str = "TARAGOLD 2026", **overrides) -> dict:
    """Build a valid event-create payload."""
    payload = {
        "name": name,
        "subtitle": "A celebration of love, memories & moments.",
        "host_id": host_id,
        "event_date": "2026-12-20",
        "theme": "gold",
    }
    payload.update(overrides)
    return payload


# ============================================================
# ADMIN — create
# ============================================================

def test_admin_can_create_event(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    resp = client.post(
        "/api/events",
        json=_create_event_payload(host.id),
        headers=_auth_headers(admin),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "TARAGOLD 2026"
    assert body["slug"] == "taragold-2026"
    assert body["status"] == "LIVE"  # default status on create
    assert body["host_id"] == host.id
    assert "password_hash" not in body


def test_create_event_generates_slug_when_omitted(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    resp = client.post(
        "/api/events",
        json=_create_event_payload(host.id, name="Aurora Spring 2026"),
        headers=_auth_headers(admin),
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "aurora-spring-2026"


def test_admin_create_event_defaults_to_live(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    resp = client.post(
        "/api/events",
        json=_create_event_payload(host.id),
        headers=_auth_headers(admin),
    )
    assert resp.json()["status"] == "LIVE"


# ============================================================
# ADMIN — validation
# ============================================================

def test_missing_event_name_rejected(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    payload = _create_event_payload(host.id, name="")
    resp = client.post("/api/events", json=payload, headers=_auth_headers(admin))
    assert resp.status_code == 422


def test_invalid_host_rejected(client: TestClient, db: Session):
    admin = _admin_token(db)
    payload = _create_event_payload("no-such-host-id")
    resp = client.post("/api/events", json=payload, headers=_auth_headers(admin))
    assert resp.status_code == 404


def test_non_host_user_rejected_as_host(client: TestClient, db: Session):
    admin = _admin_token(db)
    other_admin = _create_user(db, "admin2@test.gallery", UserRole.ADMIN)
    payload = _create_event_payload(other_admin.id)
    resp = client.post("/api/events", json=payload, headers=_auth_headers(admin))
    assert resp.status_code == 400
    assert "must have the HOST role" in resp.json()["detail"]


def test_duplicate_slug_rejected(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    # Create the first event.
    first = client.post(
        "/api/events",
        json=_create_event_payload(host.id, name="TARAGOLD 2026"),
        headers=_auth_headers(admin),
    )
    assert first.status_code == 201
    # Second event with the same name -> same auto slug -> conflict.
    second = client.post(
        "/api/events",
        json=_create_event_payload(host.id, name="TARAGOLD 2026"),
        headers=_auth_headers(admin),
    )
    # Our service auto-suffixes to keep it unique, returning 201.
    assert second.status_code == 201
    assert second.json()["slug"] != first.json()["slug"]


def test_explicit_duplicate_slug_gets_unique_suffix(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    # Two events with the SAME explicit slug.
    r1 = client.post(
        "/api/events",
        json=_create_event_payload(host.id, name="Event One", slug="same-slug"),
        headers=_auth_headers(admin),
    )
    r2 = client.post(
        "/api/events",
        json=_create_event_payload(host.id, name="Event Two", slug="same-slug"),
        headers=_auth_headers(admin),
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["slug"] == "same-slug"
    assert r2.json()["slug"] == "same-slug-2"


# ============================================================
# ADMIN — list / view
# ============================================================

def test_admin_can_list_events(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    client.post("/api/events", json=_create_event_payload(host.id, name="Event A"),
                headers=_auth_headers(admin))
    client.post("/api/events", json=_create_event_payload(host.id, name="Event B"),
                headers=_auth_headers(admin))
    resp = client.get("/api/admin/events", headers=_auth_headers(admin))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_admin_can_view_event(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    resp = client.get(f"/api/admin/events/{created['id']}", headers=_auth_headers(admin))
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    assert resp.json()["name"] == "TARAGOLD 2026"


def test_admin_view_missing_event_404(client: TestClient, db: Session):
    admin = _admin_token(db)
    resp = client.get("/api/admin/events/does-not-exist", headers=_auth_headers(admin))
    assert resp.status_code == 404


# ============================================================
# ADMIN — update
# ============================================================

def test_admin_can_update_event(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    resp = client.patch(
        f"/api/admin/events/{created['id']}",
        json={"name": "Renamed Event", "theme": "blue"},
        headers=_auth_headers(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Event"
    assert resp.json()["theme"] == "blue"


def test_admin_can_update_host_id(client: TestClient, db: Session):
    admin = _admin_token(db)
    host1 = _host_token(db, "host1@test.gallery")
    host2 = _host_token(db, "host2@test.gallery")
    created = client.post("/api/events", json=_create_event_payload(host1.id),
                          headers=_auth_headers(admin)).json()
    resp = client.patch(
        f"/api/admin/events/{created['id']}",
        json={"host_id": host2.id},
        headers=_auth_headers(admin),
    )
    assert resp.status_code == 200
    assert resp.json()["host_id"] == host2.id


def test_admin_update_invalid_status_transition_rejected(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    # ENDED -> LIVE is NOT allowed.
    client.patch(f"/api/admin/events/{created['id']}", json={"status": "ENDED"},
                 headers=_auth_headers(admin))
    resp = client.patch(f"/api/admin/events/{created['id']}", json={"status": "LIVE"},
                        headers=_auth_headers(admin))
    assert resp.status_code == 400


# ============================================================
# ADMIN — archive
# ============================================================

def test_admin_can_archive_event(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    resp = client.post(f"/api/admin/events/{created['id']}/archive",
                       headers=_auth_headers(admin))
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARCHIVED"
    assert resp.json()["archived_at"] is not None


def test_archived_event_not_physically_deleted(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    client.post(f"/api/admin/events/{created['id']}/archive", headers=_auth_headers(admin))
    # Event still exists in the DB (just archived).
    resp = client.get(f"/api/admin/events/{created['id']}", headers=_auth_headers(admin))
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARCHIVED"


# ============================================================
# HOST — list / view / update
# ============================================================

def test_host_can_list_own_events(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    client.post("/api/events", json=_create_event_payload(host.id, name="My Event"),
                headers=_auth_headers(admin))
    resp = client.get("/api/host/events", headers=_auth_headers(host))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "My Event"


def test_host_can_view_own_event(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    resp = client.get(f"/api/host/events/{created['id']}", headers=_auth_headers(host))
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_host_can_update_own_event(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    resp = client.patch(
        f"/api/host/events/{created['id']}",
        json={"name": "Updated by Host", "theme": "rose"},
        headers=_auth_headers(host),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated by Host"
    assert resp.json()["theme"] == "rose"


def test_host_cannot_change_ownership_or_status(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    other_host = _host_token(db, "other@test.gallery")
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    # Host tries to reassign ownership + change status.
    resp = client.patch(
        f"/api/host/events/{created['id']}",
        json={"host_id": other_host.id, "status": "ENDED", "name": "Still Mine"},
        headers=_auth_headers(host),
    )
    assert resp.status_code == 200
    body = resp.json()
    # Ownership + status unchanged (host cannot touch them).
    assert body["host_id"] == host.id
    assert body["status"] == "LIVE"
    # Name was updated.
    assert body["name"] == "Still Mine"


# ============================================================
# AUTHORIZATION
# ============================================================

def test_host_cannot_access_admin_event_endpoints(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    # Host hitting the admin list endpoint.
    resp = client.get("/api/admin/events", headers=_auth_headers(host))
    assert resp.status_code == 403
    # Host trying to archive via admin endpoint.
    resp = client.post(f"/api/admin/events/{created['id']}/archive",
                       headers=_auth_headers(host))
    assert resp.status_code == 403


def test_host_cannot_access_another_hosts_event(client: TestClient, db: Session):
    admin = _admin_token(db)
    host_a = _host_token(db, "hosta@test.gallery")
    host_b = _host_token(db, "hostb@test.gallery")
    created = client.post("/api/events", json=_create_event_payload(host_a.id, name="A's"),
                          headers=_auth_headers(admin)).json()
    # Host B tries to view A's event -> 404 (no existence leak).
    resp = client.get(f"/api/host/events/{created['id']}", headers=_auth_headers(host_b))
    assert resp.status_code == 404
    # Host B tries to update A's event -> 404.
    resp = client.patch(f"/api/host/events/{created['id']}",
                        json={"name": "Hijack"}, headers=_auth_headers(host_b))
    assert resp.status_code == 404


def test_admin_only_routes_reject_host(client: TestClient, db: Session):
    host = _host_token(db)
    resp = client.get("/api/admin/events", headers=_auth_headers(host))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_protected_event_routes(client: TestClient, db: Session):
    # No token.
    resp = client.get("/api/admin/events")
    assert resp.status_code == 401
    resp = client.get("/api/host/events")
    assert resp.status_code == 401
    resp = client.post("/api/events", json={})
    assert resp.status_code == 401


# ============================================================
# PUBLIC — event lookup
# ============================================================

def test_public_event_lookup_works_without_auth(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    resp = client.get(f"/api/events/{created['slug']}/public")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "TARAGOLD 2026"
    assert body["slug"] == "taragold-2026"
    assert body["status"] == "LIVE"


def test_public_endpoint_returns_only_safe_fields(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    resp = client.get(f"/api/events/{created['slug']}/public")
    body = resp.json()
    # Sensitive/internal fields must NOT be present.
    assert "host_id" not in body
    assert "host" not in body
    assert "created_at" not in body
    assert "updated_at" not in body
    assert "archived_at" not in body
    assert "password_hash" not in body
    # Expected public fields are present.
    assert {"name", "slug", "subtitle", "theme", "event_date", "status"} <= set(body.keys())


def test_public_unknown_slug_returns_404(client: TestClient):
    resp = client.get("/api/events/nonexistent-slug/public")
    assert resp.status_code == 404


# ============================================================
# PERSISTENCE
# ============================================================

def test_event_survives_db_session_reload(client: TestClient, db: Session):
    # Create via the service (real DB write + commit).
    admin = _admin_token(db)
    host = _host_token(db)
    created = event_service.create_event(
        db,
        __import__("app.schemas.event", fromlist=["EventCreate"]).EventCreate(
            name="Persistent Event",
            host_id=host.id,
            event_date=date(2026, 5, 1),
        ),
    )
    event_id = created.id
    # Fresh query in a NEW session context (simulate a new request).
    reloaded = db.get(Event, event_id)
    assert reloaded is not None
    assert reloaded.name == "Persistent Event"
    assert reloaded.slug == "persistent-event"


def test_event_survives_api_request_lifecycle(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    # The event is still fetchable in a separate request.
    resp = client.get(f"/api/host/events/{created['id']}", headers=_auth_headers(host))
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


# ============================================================
# ARCHIVE — details
# ============================================================

def test_archived_at_populated(client: TestClient, db: Session):
    admin = _admin_token(db)
    host = _host_token(db)
    created = client.post("/api/events", json=_create_event_payload(host.id),
                          headers=_auth_headers(admin)).json()
    assert created["archived_at"] is None  # not archived yet
    archived = client.post(f"/api/admin/events/{created['id']}/archive",
                           headers=_auth_headers(admin)).json()
    assert archived["archived_at"] is not None
    assert archived["status"] == "ARCHIVED"
