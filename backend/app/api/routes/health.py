# ============================================================
# Lentis Gallery — Health Endpoints
# ============================================================
# Two health endpoints:
#
#   GET /api/health       — LIVENESS
#     Is the application process running?
#     Used by Docker HEALTHCHECK and load balancers.
#     Only checks that the process is alive.
#     Does NOT check dependencies.
#
#   GET /api/health/ready — READINESS
#     Can the application serve requests?
#     Checks: PostgreSQL reachable, Redis reachable, config valid.
#     Used by orchestrators to decide if the service should
#     receive traffic.
#
# Both responses are safe to expose publicly.
# Neither exposes credentials or internal details.
# ============================================================

import time
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Track startup time for uptime reporting
_start_time = time.time()


# ============================================================
# GET /api/health — Liveness check
# ============================================================
# Fast, no dependency checks.
# Docker uses this to decide if the container should restart.

@router.get("/health", name="health", tags=["system"])
def health() -> dict:
    """Liveness check: is the application process running?"""
    return {
        "status": "ok",
        "app": "Lentis Gallery API",
        "uptime_seconds": round(time.time() - _start_time),
    }


# ============================================================
# GET /api/health/ready — Readiness check
# ============================================================
# Slower — verifies all dependencies are reachable.
# Docker uses this via depends_on: condition: service_healthy.

@router.get("/health/ready", name="health_ready", tags=["system"])
def health_ready(db: Session = Depends(get_db)) -> dict:
    """
    Readiness check: can the application serve requests?

    Verifies:
    - PostgreSQL is reachable
    - Redis is reachable
    """
    checks = {}
    overall = "ok"

    # --- PostgreSQL ---
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "connected"
    except Exception as e:
        logger.warning("Readiness check: PostgreSQL unreachable: %s", type(e).__name__)
        checks["postgres"] = "disconnected"
        overall = "degraded"

    # --- Redis ---
    try:
        from app.core.config import settings
        import redis as redis_lib

        # Parse Redis URL and connect
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        r.ping()
        r.close()
        checks["redis"] = "connected"
    except Exception as e:
        logger.warning("Readiness check: Redis unreachable: %s", type(e).__name__)
        checks["redis"] = "disconnected"
        overall = "degraded"

    status_code = 200 if overall == "ok" else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "app": "Lentis Gallery API",
            "dependencies": checks,
            "uptime_seconds": round(time.time() - _start_time),
        },
    )
