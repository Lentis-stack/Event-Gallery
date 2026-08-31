"""Add event access mode and invited guests for private events.

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa

revision = "n6o7p8q9r0s1"
down_revision = "m5n6o7p8q9r0"


def upgrade() -> None:
    # 1. Create the event_access_mode enum type.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type t WHERE t.typname = 'event_access_mode') THEN
                CREATE TYPE event_access_mode AS ENUM ('PUBLIC', 'PRIVATE');
            END IF;
        END
        $$
    """)

    # 2. Add access_mode column to events table (default PUBLIC).
    op.execute("""
        ALTER TABLE events ADD COLUMN access_mode event_access_mode NOT NULL DEFAULT 'PUBLIC'
    """)

    # 3. Create the event_invited_guests table.
    op.create_table(
        "event_invited_guests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("INVITED", "ACTIVE", "REMOVED", name="invited_guest_status"),
            nullable=False,
            server_default="INVITED",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_event_invited_guests_event_id", "event_invited_guests", ["event_id"])


def downgrade() -> None:
    op.drop_table("event_invited_guests")
    op.execute("DROP TYPE IF EXISTS invited_guest_status")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS access_mode")
    op.execute("DROP TYPE IF EXISTS event_access_mode")
