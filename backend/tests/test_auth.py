# ============================================================
# Lentis Gallery — Authentication & Authorization Tests
# ------------------------------------------------------------
# Tests the REAL auth system end-to-end:
#   - user model creation
#   - password hashing (Argon2id)
#   - login (success + failure)
#   - access tokens (valid/expired/invalid)
#   - /api/auth/me
#   - role-based authorization (ADMIN vs HOST)
#   - disable-user blocking
#   - logout
#   - refresh token rotation/revocation
#   - login rate limiting
#   - request validation
#
# These use the isolated in-memory test DB from conftest.py.
# ============================================================

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, UserRole
from app.schemas.auth import UserOut


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _create_user(db: Session, email: str, password: str = "StrongPass123!", role: UserRole = UserRole.HOST, is_active: bool = True) -> User:
    """Create a user directly in the test DB (bypasses the API)."""
    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient, email: str, password: str):
    """Attempt a login and return the response."""
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _register_admin(db: Session) -> User:
    """Create an admin user for tests."""
    return _create_user(db, "admin@lentis.gallery", "AdminPass123!", UserRole.ADMIN)


# ============================================================
# 1. User model creation
# ============================================================

def test_user_model_creation(db: Session):
    user = _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    assert user.id
    assert user.email == "host@lentis.gallery"
    assert user.role == UserRole.HOST
    assert user.is_active is True


# ============================================================
# 2. Password hashing
# ============================================================

def test_password_hashing_argon2id():
    hashed = hash_password("MySecretPass1")
    # Argon2id hashes start with "$argon2id$".
    assert hashed.startswith("$argon2id$")
    assert hashed != "MySecretPass1"


# ============================================================
# 3. Password verification
# ============================================================

def test_password_verification_success():
    hashed = hash_password("MySecretPass1")
    assert verify_password("MySecretPass1", hashed) is True


def test_password_verification_failure():
    hashed = hash_password("MySecretPass1")
    assert verify_password("WrongPass1", hashed) is False


# ============================================================
# 4. Password is NOT stored plaintext
# ============================================================

def test_password_not_stored_plaintext(db: Session):
    user = _create_user(db, "plain@lentis.gallery", "PlainPass123!", UserRole.HOST)
    assert user.password_hash != "PlainPass123!"
    assert "PlainPass123!" not in user.password_hash


# ============================================================
# 5-8. Login behavior
# ============================================================

def test_login_success(client: TestClient, db: Session):
    _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    resp = _login(client, "host@lentis.gallery", "HostPass123!")
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]["token_type"] == "bearer"
    assert body["access_token"]["access_token"]
    # Safe user fields only — no password/hash.
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert body["user"]["email"] == "host@lentis.gallery"


def test_login_incorrect_password(client: TestClient, db: Session):
    _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    resp = _login(client, "host@lentis.gallery", "WrongPassword!")
    assert resp.status_code == 401
    # Generic message — no account enumeration.
    assert resp.json()["detail"] == "Invalid email or password."


def test_login_unknown_email(client: TestClient):
    resp = _login(client, "nobody@lentis.gallery", "Whatever123!")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


def test_login_email_case_insensitive(client: TestClient, db: Session):
    _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    resp = _login(client, "HOST@LENTIS.GALLERY", "HostPass123!")
    assert resp.status_code == 200


# ============================================================
# 9-11. Access token generation / validation / expiry
# ============================================================

def test_access_token_generation():
    token = create_access_token("user-123", "HOST")
    assert isinstance(token, str) and len(token) > 20


def test_me_with_valid_access_token(client: TestClient, db: Session):
    user = _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    token = create_access_token(user.id, user.role.value)
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "host@lentis.gallery"


def test_me_with_invalid_access_token(client: TestClient):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401


def test_me_with_expired_access_token(client: TestClient, db: Session):
    user = _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    # Create a token with an already-expired expiry.
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings
    expired_payload = {
        "sub": user.id,
        "role": user.role.value,
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "jti": "expired-test",
    }
    expired = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


# ============================================================
# 12-13. /me authenticated / unauthenticated
# ============================================================

def test_me_unauthenticated(client: TestClient):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_authenticated(client: TestClient, db: Session):
    user = _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    token = create_access_token(user.id, user.role.value)
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


# ============================================================
# 14-17. Authorization (ADMIN vs HOST)
# ============================================================

def test_admin_can_create_user(client: TestClient, db: Session):
    admin = _register_admin(db)
    token = create_access_token(admin.id, admin.role.value)
    resp = client.post(
        "/api/auth/users",
        json={"email": "newhost@lentis.gallery", "password": "NewHostPass123!", "role": "HOST"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "HOST"


def test_host_blocked_from_admin_endpoint(client: TestClient, db: Session):
    host = _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    token = create_access_token(host.id, host.role.value)
    resp = client.post(
        "/api/auth/users",
        json={"email": "another@lentis.gallery", "password": "AnotherPass123!", "role": "HOST"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_unauthenticated_rejected_from_admin_endpoint(client: TestClient):
    resp = client.post(
        "/api/auth/users",
        json={"email": "x@lentis.gallery", "password": "XPass12345!", "role": "HOST"},
    )
    assert resp.status_code == 401


def test_disabled_user_cannot_authenticate(client: TestClient, db: Session):
    _create_user(db, "disabled@lentis.gallery", "DisabledPass123!", UserRole.HOST, is_active=False)
    resp = _login(client, "disabled@lentis.gallery", "DisabledPass123!")
    assert resp.status_code == 401


def test_disabled_user_blocked_with_valid_token(client: TestClient, db: Session):
    user = _create_user(db, "disabled2@lentis.gallery", "DisabledPass123!", UserRole.HOST, is_active=False)
    token = create_access_token(user.id, user.role.value)
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ============================================================
# 18. Logout
# ============================================================

def test_logout_revokes_refresh_token(client: TestClient, db: Session):
    _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    login = _login(client, "host@lentis.gallery", "HostPass123!")
    assert login.status_code == 200
    refresh_cookie = login.cookies.get("lentis_refresh")
    assert refresh_cookie

    # Logout.
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204

    # The refresh token is now revoked — refresh should fail.
    client.cookies.set("lentis_refresh", refresh_cookie)
    resp = client.post("/api/auth/refresh")
    assert resp.status_code == 401


# ============================================================
# 19-20. Refresh token + rotation
# ============================================================

def test_refresh_token_rotates(client: TestClient, db: Session):
    _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    login = _login(client, "host@lentis.gallery", "HostPass123!")
    old_cookie = login.cookies.get("lentis_refresh")

    # Use the refresh token to get a new access token.
    client.cookies.set("lentis_refresh", old_cookie)
    refresh = client.post("/api/auth/refresh")
    assert refresh.status_code == 200
    new_cookie = refresh.cookies.get("lentis_refresh")
    assert new_cookie and new_cookie != old_cookie  # rotated

    # Old (rotated) token should now be invalid.
    client.cookies.set("lentis_refresh", old_cookie)
    resp = client.post("/api/auth/refresh")
    assert resp.status_code == 401


def test_refresh_without_token(client: TestClient):
    resp = client.post("/api/auth/refresh")
    assert resp.status_code == 401


# ============================================================
# 21. Rate limiting (brute-force protection)
# ============================================================

def test_login_rate_limiting_locks_out(client: TestClient, db: Session):
    # Reset limiter state to avoid interference between tests.
    from app.core import rate_limit
    rate_limit._failures.clear()
    rate_limit._lockouts.clear()

    _create_user(db, "host@lentis.gallery", "HostPass123!", UserRole.HOST)
    # Exceed the max attempts (LOGIN_MAX_ATTEMPTS=5).
    for _ in range(5):
        resp = _login(client, "host@lentis.gallery", "WrongPass123!")
        assert resp.status_code == 401

    # Next attempt is locked out → 429.
    resp = _login(client, "host@lentis.gallery", "HostPass123!")
    assert resp.status_code == 429


# ============================================================
# 22. Invalid request validation
# ============================================================

def test_login_validation_invalid_email(client: TestClient):
    resp = client.post("/api/auth/login", json={"email": "not-an-email", "password": "Pass12345!"})
    assert resp.status_code == 422


def test_login_validation_missing_fields(client: TestClient):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 422


# ============================================================
# Extra: weak password rejected at user creation
# ============================================================

def test_create_user_weak_password_rejected(client: TestClient, db: Session):
    admin = _register_admin(db)
    token = create_access_token(admin.id, admin.role.value)
    # "password123" passes the schema min-length (8) but fails the
    # service-level common-password check → 400.
    resp = client.post(
        "/api/auth/users",
        json={"email": "weak@lentis.gallery", "password": "password123", "role": "HOST"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ============================================================
# Extra: duplicate email rejected
# ============================================================

def test_create_user_duplicate_email(client: TestClient, db: Session):
    admin = _register_admin(db)
    _create_user(db, "dup@lentis.gallery", "DupPass123!", UserRole.HOST)
    token = create_access_token(admin.id, admin.role.value)
    resp = client.post(
        "/api/auth/users",
        json={"email": "dup@lentis.gallery", "password": "AnotherPass123!", "role": "HOST"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
