# ============================================================
# Lentis Gallery - FastAPI Application Entry Point
# ============================================================
# SECURITY HARDENING:
#   1. CORS: Only specific origins, methods, and headers.
#   2. CSP + security headers on every response.
#   3. /docs and /redoc disabled by default (opt-in via ENABLE_DOCS).
#   4. DEBUG disabled in production.
#   5. Audit logging for destructive actions.
#   6. Request body size limits.
#   7. Schema managed by Alembic (no create_all).
# ============================================================

import logging
import time
import json
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.api.routes.admin_events import router as admin_events_router
from app.api.routes.admin_event_guests import router as admin_event_guests_router
from app.api.routes.auth import router as auth_router
from app.api.routes.events import router as events_router
from app.api.routes.guests import router as guests_router
from app.api.routes.health import router as health_router
from app.api.routes.host_events import router as host_events_router
from app.api.routes.media import router as media_router
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Lifespan (startup / shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # SEC-014: Schema is managed by Alembic migrations only.
    # Do NOT use create_all() — it silently creates tables and
    # can mask migration drift. Run 'alembic upgrade head' instead.
    logger.info("Lentis Gallery API starting (env=%s)", settings.ENVIRONMENT)
    yield
    logger.info("Lentis Gallery API shutting down.")


# ============================================================
# Security Headers Middleware
# ============================================================
# Adds protective headers to EVERY response.
# Prevents: XSS, clickjacking, MIME sniffing, referrer leakage.
# ============================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # NOTE: nginx already provides CSP, X-Content-Type-Options,
        # X-Frame-Options, and other security headers on HTML and API
        # responses. We only add headers that nginx doesn't provide,
        # and ONLY send HSTS when the upstream connection is HTTPS
        # (i.e. Cloudflare → nginx sent X-Forwarded-Proto: https).
        # Sending HSTS on plain HTTP causes browsers to force-redirect
        # to HTTPS, breaking local development and HTTP deployments.

        # Only send HSTS when the request arrived over HTTPS
        # (X-Forwarded-Proto is set by nginx/Cloudflare)
        forwarded_proto = request.headers.get("x-forwarded-proto", "http")
        if settings.ENVIRONMENT == "production" and forwarded_proto == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        if "server" in response.headers:
            del response.headers["server"]
        return response


# ============================================================
# Structured Request Logging Middleware
# ============================================================
# Logs ALL requests with structured JSON for production log aggregation.
# Includes: method, path, status, duration, user type, client IP.
# Excludes: passwords, JWTs, tokens, file contents.
# ============================================================
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    # Paths to exclude from logging (health checks are noisy)
    SKIP_LOGGING = {"/api/health", "/api/health/ready"}

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 1)

        path = request.url.path
        if path in self.SKIP_LOGGING:
            return response

        # Determine user type without exposing tokens
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            user_type = "authenticated"
        elif request.headers.get("x-guest-token"):
            user_type = "guest"
        else:
            user_type = "public"

        log_entry = {
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "user_type": user_type,
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "-")[:100],
        }

        # Audit log mutating requests at INFO level
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            logger.info("AUDIT %s", json.dumps(log_entry))
        # Log errors and slow requests
        elif response.status_code >= 400:
            logger.warning("REQUEST %s", json.dumps(log_entry))
        elif duration_ms > 5000:
            logger.warning("SLOW %s", json.dumps(log_entry))
        # Everything else at DEBUG
        else:
            logger.debug("REQUEST %s", json.dumps(log_entry))

        return response


# ============================================================
# Create the FastAPI app
# ============================================================
is_production = settings.ENVIRONMENT == "production"

# SEC-009: API docs are disabled by default. Set ENABLE_DOCS=true to enable.
docs_enabled = settings.ENABLE_DOCS and not is_production

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    description="Lentis Gallery backend API.",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
)


# ============================================================
# Middleware stack (order matters — last added = first executed)
# ============================================================

# GZip compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=500)

# Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)

# Structured request logging (audit trail + performance)
app.add_middleware(RequestLoggingMiddleware)

# SEC-010: CORS — restricts which origins, methods, and headers are allowed.
# Origins are validated by the config validator (no wildcards in production).
cors_origins = [
    o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Guest-Token", "Accept"],
)

# SEC-020: Request body size limit — reject oversized requests early.
# This middleware runs BEFORE the request body is read into memory.
@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large."},
        )
    return await call_next(request)


# ============================================================
# Routers
# ============================================================
app.include_router(health_router, prefix="/api", tags=["system"])
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(admin_events_router)
app.include_router(admin_event_guests_router)
app.include_router(host_events_router)
app.include_router(guests_router)
app.include_router(media_router)


# ============================================================
# Root endpoint
# ============================================================
@app.get("/", tags=["system"])
def root() -> dict:
    result = {"message": "Lentis Gallery API is running.", "health": "/api/health"}
    if not is_production:
        result["docs"] = "/docs"
    return result
