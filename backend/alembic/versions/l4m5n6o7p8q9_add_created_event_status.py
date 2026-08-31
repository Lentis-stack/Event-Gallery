"""Add CREATED to event_status enum

Revision ID: l4m5n6o7p8q9
Revises: k3l4m5n6o7p8
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa

revision = "l4m5n6o7p8q9"
down_revision = "k3l4m5n6o7p8"
branch_labels = None
depends_on = None


def _enum_value_exists(conn, enum_name: str, value: str) -> bool:
    result = conn.execute(
        sa.text(f"SELECT 1 FROM pg_enum WHERE enumlabel = :val AND enumtypid = (SELECT oid FROM pg_type WHERE typname = :name)"),
        {"val": value, "name": enum_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    # Add CREATED to existing event_status enum
    if not _enum_value_exists(conn, "event_status", "CREATED"):
        op.execute("ALTER TYPE event_status ADD VALUE 'CREATED'")


def downgrade() -> None:
    # Note: cannot remove enum values from PostgreSQL enum type
    pass
