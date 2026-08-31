"""Add performance indexes for media processing, gallery listing, and role-based queries.

Revision ID: h0i1j2k3l4m5
Revises: g7h8i9j0k1l2
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = "h0i1j2k3l4m5"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def _index_exists(conn, table_name: str, index_name: str) -> bool:
    """Check if an index already exists on the table."""
    insp = inspect(conn)
    indexes = insp.get_indexes(table_name)
    return any(ix["name"] == index_name for ix in indexes)


def upgrade() -> None:
    conn = op.get_bind()

    # Index for processing worker queries (find QUEUED items)
    if not _index_exists(conn, "media", "ix_media_processing_status"):
        op.create_index(
            "ix_media_processing_status",
            "media",
            ["processing_status"],
            unique=False,
        )

    # Composite index for role-based media queries (hero/slideshow/gallery)
    if not _index_exists(conn, "media", "ix_media_event_role_status"):
        op.create_index(
            "ix_media_event_role_status",
            "media",
            ["event_id", "media_role", "status"],
            unique=False,
        )

    # Composite index for gallery listing (event + status + created_at ordering)
    if not _index_exists(conn, "media", "ix_media_event_status_created"):
        op.create_index(
            "ix_media_event_status_created",
            "media",
            ["event_id", "status", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_media_event_status_created", table_name="media")
    op.drop_index("ix_media_event_role_status", table_name="media")
    op.drop_index("ix_media_processing_status", table_name="media")
