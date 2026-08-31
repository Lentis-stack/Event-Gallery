"""Add HIDDEN to media_status enum.

Revision ID: m5n6o7p8q9r0
Revises: l4m5n6o7p8q9
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

revision = "m5n6o7p8q9r0"
down_revision = "l4m5n6o7p8q9"


def upgrade() -> None:
    # Add HIDDEN to the existing media_status enum (if not already present).
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid
                           WHERE t.typname = 'media_status' AND e.enumlabel = 'HIDDEN') THEN
                ALTER TYPE media_status ADD VALUE 'HIDDEN';
            END IF;
        END
        $$
    """)


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum.
    # A full downgrade would require recreating the enum type.
    pass
