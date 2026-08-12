# ============================================================
# Lentis Gallery — Refresh Token Model
# ------------------------------------------------------------
# Stores refresh-token SESSIONS server-side.
#
# SECURITY DESIGN:
#   - We store the SHA-256 HASH of the refresh token, never the
#     raw token. If the DB leaks, attackers cannot use the tokens.
#   - Each refresh token belongs to a user, has an expiry, and a
#     "revoked" flag.
#   - Token ROTATION: when a token is used to refresh, we mark the
#     old one revoked and issue a NEW one. If a stolen token is
#     replayed, it is already revoked → the refresh fails.
#
# The raw token is returned to the client (in a cookie) and only
# its hash is stored. To validate, we hash the presented token and
# look for a matching, non-revoked, unexpired row.
# ============================================================

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


def generate_uuid() -> str:
    return str(uuid.uuid4())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Which user this session belongs to.
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # SHA-256 hash of the refresh token (NOT the raw token).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # When this session expires.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Revoked flag (for logout / rotation).
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # When it was created / revoked (timestamps, timezone-aware).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional: IP + user agent for audit (not logged raw, just stored).
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<RefreshToken user_id={self.user_id} revoked={self.revoked}>"
