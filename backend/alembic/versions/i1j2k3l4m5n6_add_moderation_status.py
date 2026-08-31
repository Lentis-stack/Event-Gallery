"""Add moderation status columns to media table.

Revision ID: i1j2k3l4m5n6
Revises: h0i1j2k3l4m5
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "i1j2k3l4m5n6"
down_revision = "h0i1j2k3l4m5"
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    insp = inspect(conn)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "media", "moderation_status"):
        moderation_enum = sa.Enum("VISIBLE", "HIDDEN", name="moderation_status")
        moderation_enum.create(conn, checkfirst=True)
        op.add_column(
            "media",
            sa.Column("moderation_status", moderation_enum, nullable=False, server_default="VISIBLE"),
        )

    if not _column_exists(conn, "media", "moderated_at"):
        op.add_column(
            "media",
            sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists(conn, "media", "moderated_by"):
        op.add_column(
            "media",
            sa.Column("moderated_by", sa.String(36), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("media", "moderated_by")
    op.drop_column("media", "moderated_at")
    op.drop_column("media", "moderation_status")
    sa.Enum(name="moderation_status").drop(op.get_bind(), checkfirst=True)
