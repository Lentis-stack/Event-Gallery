# ============================================================
# Lentis Gallery — Migration: Create guests & guest_sessions
# ------------------------------------------------------------
# Revision ID: c3d4e5f6a7b8
# Revises: b2c3d4e5f6a7  (chained after the events migration)
#
# Phase 4. Creates two tables:
#   guests          — a person attending an event (NOT a platform
#                     User; no password, no email).
#   guest_sessions  — event-scoped access tokens (only the SHA-256
#                     hash is stored) for guests.
#
# Both tables FK back to events.id with ON DELETE CASCADE so an
# event deletion removes its guests and their sessions.
# ============================================================

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Success: create the guest_session_status enum type.
    op.execute("""DROP TYPE IF EXISTS guest_session_status; CREATE TYPE guest_session_status AS ENUM ('ACTIVE', 'REVOKED', 'EXPIRED')""")

    # --- guests table ---
    op.create_table(
        "guests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Which event this guest belongs to. CASCADE on event delete.
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_guests_event_id", "guests", ["event_id"])

    # --- guest_sessions table ---
    op.create_table(
        "guest_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("guest_id", sa.String(length=36), nullable=False),
        # Denormalized event id for fast event-scoping checks.
        sa.Column("event_id", sa.String(length=36), nullable=False),
        # SHA-256 hash of the raw token (unique to prevent collisions).
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )
    # Indexes: token_hash is unique (fast lookup by hash), and we
    # index event_id + guest_id for scoping queries.
    op.create_index("ix_guest_sessions_token_hash", "guest_sessions", ["token_hash"], unique=True)
    op.create_index("ix_guest_sessions_event_id", "guest_sessions", ["event_id"])
    op.create_index("ix_guest_sessions_guest_id", "guest_sessions", ["guest_id"])


def downgrade() -> None:
    # Rollback in reverse order.
    op.drop_index("ix_guest_sessions_guest_id", table_name="guest_sessions")
    op.drop_index("ix_guest_sessions_event_id", table_name="guest_sessions")
    op.drop_index("ix_guest_sessions_token_hash", table_name="guest_sessions")
    op.drop_table("guest_sessions")
    op.drop_index("ix_guests_event_id", table_name="guests")
    op.drop_table("guests")
    sa.Text().drop(
        op.get_bind(), checkfirst=True
    )
