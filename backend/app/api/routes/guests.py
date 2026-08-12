# ============================================================
# Lentis Gallery — Guest Routes
# ------------------------------------------------------------
# The guest API. Guests are NOT platform users — they carry an
# event-scoped session token, not an account.
#
# ENDPOINTS:
#   POST /api/events/{slug}/guests
#       Register a guest (name only) for a LIVE event. Returns a
#       fresh session token in the response body.
#
#   GET /api/events/{slug}/guests/me
#       Validate a session token and return the guest's own info.
#       Requires the token in the X-Guest-Token header.
#
#   POST /api/events/{slug}/guests/session/revoke
#       Revoke the current session (logout). Requires the token.
#
# HOW THE TOKEN TRAVELS:
#   The registration response returns the raw token in the body.
#   The frontend stores it (in memory or sessionStorage) and sends
#   it on subsequent requests via the X-Guest-Token header. It is
#   NOT a cookie because guests are low-risk and the token is
#   short-lived (default 6h). (Revisit cookies if we need stricter
#   XSS protection down the road.)
# ============================================================

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.guest import (
    GuestMeResponse,
    GuestOut,
    GuestRegister,
    GuestRegisterResponse,
    GuestSessionInfo,
)
from app.services import guests as guest_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["guests"])

# Header guests use to present their session token.
GUEST_TOKEN_HEADER = "X-Guest-Token"


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    """Extract client IP + User-Agent for audit (never logged raw by us)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


# ============================================================
# POST /api/events/{slug}/guests  (PUBLIC)
# ============================================================

@router.post(
    "/api/events/{slug}/guests",
    response_model=GuestRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register as a guest (no account needed)",
    description=(
        "Creates a guest for a LIVE event and returns a fresh, "
        "event-scoped session token. Only the guest's name is "
        "required. Returns 404 if the event slug is unknown, 400 "
        "if the event is not accepting guests, and 422 if the name "
        "is invalid."
    ),
)
def register_guest(
    slug: str,
    body: GuestRegister,
    request: Request,
    db: Session = Depends(get_db),
) -> GuestRegisterResponse:
    ip, ua = _client_meta(request)
    guest, session, raw_token = guest_service.register_guest(
        db, slug, body, ip, ua
    )

    return GuestRegisterResponse(
        guest=GuestOut.model_validate(guest),
        session=GuestSessionInfo(
            session_id=session.id,
            session_token=raw_token,
            expires_at=session.expires_at,
        ),
    )


# ============================================================
# GET /api/events/{slug}/guests/me  (session token required)
# ============================================================

@router.get(
    "/api/events/{slug}/guests/me",
    response_model=GuestMeResponse,
    summary="Get current guest info",
    description=(
        "Validates the guest session token (via X-Guest-Token header) "
        "and returns the guest's own info. Returns 401 if the token "
        "is invalid, expired, revoked, or belongs to a different event."
    ),
)
def get_my_guest(
    slug: str,
    request: Request,
    x_guest_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> GuestMeResponse:
    _require_token(x_guest_token)
    guest, session = guest_service.get_my_guest(db, slug, x_guest_token)
    return GuestMeResponse(
        guest=GuestOut.model_validate(guest),
        session_status=session.status.value,
    )


# ============================================================
# POST /api/events/{slug}/guests/session/revoke  (session token)
# ============================================================

@router.post(
    "/api/events/{slug}/guests/session/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current guest session",
    description=(
        "Immediately invalidates the presented guest session token. "
        "Requires the token in the X-Guest-Token header."
    ),
)
def revoke_guest_session(
    slug: str,
    request: Request,
    x_guest_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Response:
    _require_token(x_guest_token)
    guest_service.revoke_guest_session(db, slug, x_guest_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_token(token: str | None) -> None:
    """Raise 401 if no guest token was supplied."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest session token is required.",
        )
