# ============================================================
# Lentis Gallery — Phase 1 Test: Root & Health Basic
# ------------------------------------------------------------
# Uses FastAPI's TestClient (which wraps httpx) to call our app
# WITHOUT starting a real server. This lets us verify the API
# structure works even before PostgreSQL is running.
#
# NOTE:
#   - The root endpoint "/" does NOT touch the database, so we can
#     test it freely.
#   - The "/api/health" endpoint DOES query the database. It will
#     only succeed once PostgreSQL is running. We include a test
#     that asserts it returns the expected shape when connected.
# ============================================================

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """The root endpoint should tell us the app is running."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Lentis Gallery API is running."
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"


def test_openapi_is_available():
    """The auto-generated API docs spec should load."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "Lentis Gallery API"


# NOTE: We intentionally do NOT test /api/health here because it
# requires a live PostgreSQL connection. Once PostgreSQL is running
# (Phase 1 step 3 in the README), this endpoint returns:
#   {"status": "ok", "database": "connected"}
# We will add a DB-dependent health test in a later phase when the
# test database is wired up.

