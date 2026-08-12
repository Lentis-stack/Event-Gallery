# ============================================================
# Lentis Gallery — Health Endpoint
# ------------------------------------------------------------
# A "health check" is a tiny endpoint that tells you whether the
# backend is alive and that its dependencies (like the database)
# are reachable. Monitoring tools and CI use it to know if the
# service is healthy.
#
# This is the backend's "hello world" — it proves the whole
# chain works: FastAPI is running, config loaded, and PostgreSQL
# is reachable.
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

# APIRouter groups related endpoints. We register this router in
# main.py with a prefix of "/api", so this endpoint ends up at:
#     GET /api/health
router = APIRouter()


@router.get("/health", name="health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict:
    """
    Health check.

    Returns the application status and verifies the database
    connection by running a real (tiny) SQL query.
    """
    # Run a real database query: "SELECT 1" is a standard way to
    # confirm the database is reachable. If PostgreSQL is down,
    # this raises an error and FastAPI returns a 500.
    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "app": "Lentis Gallery API",
        "database": "connected",
    }
