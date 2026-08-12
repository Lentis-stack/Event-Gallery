# ============================================================
# Lentis Gallery — User Model
# ------------------------------------------------------------
# This is the SQLAlchemy ORM class for the "users" table.
#
# WHAT IS AN ORM MODEL?
#   A Python class that maps to a database table. SQLAlchemy uses
#   this class to know the table's columns, types, and constraints.
#   When we create a User() object and add it to the session, it
#   becomes a row in the "users" table.
#
# SECURITY NOTES:
#   - We NEVER store the plaintext password. Only password_hash.
#   - role uses a Python Enum, NOT arbitrary strings.
#   - email is normalized + unique (one account per email).
#   - is_active lets us disable an account without deleting it.
#   - Timestamps are timezone-aware.
# ============================================================

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, enum.Enum):
    """Platform roles. Using an enum prevents typos/magic strings."""
    ADMIN = "ADMIN"
    HOST = "HOST"


def utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    """Return a string UUID for the primary key. We use UUIDs so IDs
    are not predictable/guessable (unlike sequential integers)."""
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    # Primary key — a random UUID string.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Email — normalized + unique + indexed. One account per email.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Argon2id password hash. NEVER store plaintext.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role — ADMIN or HOST (enum stored as a string).
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.HOST
    )

    # Active flag — lets us disable accounts without deleting.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps (timezone-aware).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    # Last successful login (updated on login).
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
