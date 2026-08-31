"""Add media source, page, and HOST_SLIDESHOW role

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "j2k3l4m5n6o7"
down_revision = "i1j2k3l4m5n6"
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    insp = inspect(conn)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def _enum_value_exists(conn, enum_name: str, value: str) -> bool:
    """Check if a value exists in a PostgreSQL enum type."""
    result = conn.execute(
        sa.text(f"SELECT 1 FROM pg_enum WHERE enumlabel = :val AND enumtypid = (SELECT oid FROM pg_type WHERE typname = :name)"),
        {"val": value, "name": enum_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add HOST_SLIDESHOW to existing media_role enum
    if not _enum_value_exists(conn, "media_role", "HOST_SLIDESHOW"):
        op.execute("ALTER TYPE media_role ADD VALUE 'HOST_SLIDESHOW'")

    # 2. Create media_source enum
    source_enum = sa.Enum("ADMIN", "GUEST", name="media_source")
    source_enum.create(conn, checkfirst=True)

    # 3. Add source column
    if not _column_exists(conn, "media", "source"):
        op.add_column(
            "media",
            sa.Column("source", source_enum, nullable=False, server_default="ADMIN"),
        )

    # 4. Create media_page enum
    page_enum = sa.Enum("LANDING", "GUEST", "HOST", name="media_page")
    page_enum.create(conn, checkfirst=True)

    # 5. Add page column (nullable — gallery media has no page)
    if not _column_exists(conn, "media", "page"):
        op.add_column(
            "media",
            sa.Column("page", page_enum, nullable=True, server_default=None),
        )

    # 6. Add composite index for source+page queries
    op.create_index(
        "ix_media_event_source_role",
        "media",
        ["event_id", "source", "media_role"],
    )
    op.create_index(
        "ix_media_event_page_role",
        "media",
        ["event_id", "page", "media_role"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_event_page_role", table_name="media")
    op.drop_index("ix_media_event_source_role", table_name="media")
    op.drop_column("media", "page")
    sa.Enum(name="media_page").drop(op.get_bind(), checkfirst=True)
    op.drop_column("media", "source")
    sa.Enum(name="media_source").drop(op.get_bind(), checkfirst=True)
    # Note: cannot remove enum values from PostgreSQL enum type
