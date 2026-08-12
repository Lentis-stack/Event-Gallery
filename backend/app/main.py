# ============================================================
# Lentis Gallery — FastAPI Application Entry Point
# ------------------------------------------------------------
# This is the "main" file — the one that starts the whole backend.
#
# When you run:
#     uvicorn app.main:app --reload
# uvicorn looks in the "app" package, finds "main.py", and grabs
# the "app" object defined here. That object is our FastAPI app.
#
# WHAT THIS FILE DOES:
#   1. Creates the FastAPI app.
#   2. Adds CORS middleware (which domains may call us).
#   3. Creates database tables (Phase 1 shortcut — see note below).
#   4. Defines a /health endpoint so we can verify everything works.
# ============================================================

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin_events import router as admin_events_router
from app.api.routes.auth import router as auth_router
from app.api.routes.events import router as events_router
from app.api.routes.guests import router as guests_router
from app.api.routes.health import router as health_router
from app.api.routes.host_events import router as host_events_router
from app.api.routes.media import router as media_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# ------------------------------------------------------------
# Lifespan (startup / shutdown)
# ------------------------------------------------------------
# FastAPI has a "lifespan" — code that runs ONCE when the server
# starts and ONCE when it shuts down.
#
# WHY use lifespan for create_all instead of doing it at import
# time? Because importing the app module should be safe even if
# the database is temporarily down (e.g. in unit tests or tools).
# By doing DB work inside the lifespan, the module can be imported
# freely; the DB is only touched when the server actually starts.
# ------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: try to create tables if they don't already exist.
    # NOTE: Phase 1 simplification — production relies on Alembic
    # migrations instead. Alembic is set up and used from Phase 2
    # onward, but this convenience lets the app boot quickly.
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: nothing to clean up yet.
    pass


# ------------------------------------------------------------
# Create the FastAPI app.
#   title: shown in the auto-generated API docs at /docs.
#   lifespan: runs create_all on startup.
# ------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    description=(
        "Lentis Gallery backend API. Phase 1: foundation, config, "
        "database connection, and health endpoint. More routes "
        "arrive in later phases."
    ),
)

# ------------------------------------------------------------
# CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------
# The frontend runs on http://localhost:5173 and the backend on
# http://localhost:8000 — different "origins". Browsers block
# cross-origin requests by default. CORS middleware tells the
# browser "it's OK for the frontend origin to call this API".
#
# allow_credentials=True enables cookies (used for auth later).
# allow_methods/headers define what is permitted.
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# Routers
# ------------------------------------------------------------
# Register API route modules. Each router is a group of related
# endpoints. For Phase 1 we only have the health router.
app.include_router(health_router, prefix="/api", tags=["system"])
# Phase 2: authentication routes (login, refresh, logout, me, users).
app.include_router(auth_router)
# Phase 3: event management routes (admin + host + public).
app.include_router(events_router)
app.include_router(admin_events_router)
app.include_router(host_events_router)
# Phase 4: guest registration + event-scoped guest sessions.
app.include_router(guests_router)
# Phase 5: media upload + guest/host/admin media access.
app.include_router(media_router)


# ------------------------------------------------------------
# Optional root endpoint for a friendly message at the base URL.
# ------------------------------------------------------------
@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "message": "Lentis Gallery API is running.",
        "docs": "/docs",
        "health": "/api/health",
    }
