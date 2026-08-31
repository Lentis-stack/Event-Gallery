"""Add camera slideshow page enum and landing_message to events

Revision ID: k3l4m5n6o7p8
Revises: j2k3l4m5n6o7
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "k3l4m5n6o7p8"
down_revision = "j2k3l4m5n6o7"
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    insp = inspect(conn)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def _enum_value_exists(conn, enum_name: str, value: str) -> bool:
    result = conn.execute(
        sa.text(f"SELECT 1 FROM pg_enum WHERE enumlabel = :val AND enumtypid = (SELECT oid FROM pg_type WHERE typname = :name)"),
        {"val": value, "name": enum_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add CAMERA to existing media_page enum
    if not _enum_value_exists(conn, "media_page", "CAMERA"):
        op.execute("ALTER TYPE media_page ADD VALUE 'CAMERA'")

    # 2. Add landing_message column to events table
    if not _column_exists(conn, "events", "landing_message"):
        op.add_column("events", sa.Column("landing_message", sa.String(2000), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "landing_message")
    # Note: cannot remove enum values from PostgreSQL enum type
