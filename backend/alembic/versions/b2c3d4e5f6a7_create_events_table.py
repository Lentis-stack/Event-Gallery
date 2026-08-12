# ============================================================
# Lentis Gallery — Migration: Create events table
# ------------------------------------------------------------
# Revision ID: b2c3d4e5f6a7
# Revises: a1b2c3d4e5f6  (chained after the auth migration)
#
# This migration creates the "events" table for Phase 3 event
# management. It does NOT modify the existing users or
# refresh_tokens tables from Phase 2.
#
# The events table stores event METADATA only. Actual media
# (photos/videos) will live in object storage in a later phase;
# this table never stores bytes.
# ============================================================

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the event_status enum type (LIVE / ENDED / ARCHIVED).
    event_status = sa.Enum("LIVE", "ENDED", "ARCHIVED", name="event_status")
    event_status.create(op.get_bind(), checkfirst=True)

    # Create the theme_choice enum type (gold / blue / rose / emerald).
    theme_choice = sa.Enum("gold", "blue", "rose", "emerald", name="theme_choice")
    theme_choice.create(op.get_bind(), checkfirst=True)

    # --- events table ---
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        # Unique slug — the database itself prevents duplicates.
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=500), nullable=True),
        # FK -> users.id. RESTRICT means we cannot delete a user who
        # still owns events (safer than silently deleting their events).
        sa.Column("host_id", sa.String(length=36), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("LIVE", "ENDED", "ARCHIVED", name="event_status"),
            nullable=False,
            server_default="LIVE",
        ),
        sa.Column(
            "theme",
            sa.Enum("gold", "blue", "rose", "emerald", name="theme_choice"),
            nullable=False,
            server_default="gold",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["host_id"], ["users.id"], ondelete="RESTRICT"),
    )

    # Indexes for the queries we run most:
    #   - slug is unique (public lookup by slug)
    #   - host_id (list a host's events)
    #   - status (filter by status)
    #   - created_at (order events newest-first)
    op.create_index("ix_events_slug", "events", ["slug"], unique=True)
    op.create_index("ix_events_host_id", "events", ["host_id"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_created_at", "events", ["created_at"])


def downgrade() -> None:
    # Rollback: drop indexes + table + enums, in reverse order.
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_host_id", table_name="events")
    op.drop_index("ix_events_slug", table_name="events")
    op.drop_table("events")
    # Drop the enum types.
    sa.Enum("gold", "blue", "rose", "emerald", name="theme_choice").drop(
        op.get_bind(), checkfirst=True
    )
    sa.Enum("LIVE", "ENDED", "ARCHIVED", name="event_status").drop(
        op.get_bind(), checkfirst=True
    )
