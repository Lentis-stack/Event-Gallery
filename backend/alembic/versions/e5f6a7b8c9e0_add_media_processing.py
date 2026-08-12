# ============================================================
# Lentis Gallery — Migration: Add media processing fields
# ------------------------------------------------------------
# Revision ID: e5f6a7b8c9e0
# Revises: d4e5f6a7b8c9  (chained after the media table migration)
#
# Phase 6. Adds the async media-processing state + derived-variant
# metadata columns to the existing 'media' table.
#
# IMPORTANT:
#   - We do NOT edit the earlier media migration (d4e5f6a7b8c9).
#   - We only ADD new nullable columns here, so existing rows keep
#     their originals and simply start in QUEUED state.
#   - The processing_status enum is created alongside a NOT NULL
#     column with a server default of 'QUEUED' so existing rows are
#     backfilled safely.
#
# upgrade()  : adds the Phase 6 columns + the enum type.
# downgrade(): drops them (and the enum) in reverse order.
# ============================================================

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9e0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The processing_status enum type (QUEUED/PROCESSING/READY/FAILED).
    processing_status = sa.Enum(
        "QUEUED", "PROCESSING", "READY", "FAILED", name="processing_status"
    )
    processing_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "media",
        sa.Column(
            "processing_status",
            sa.Enum(
                "QUEUED", "PROCESSING", "READY", "FAILED", name="processing_status"
            ),
            nullable=False,
            server_default="QUEUED",
        ),
    )
    # A SAFE internal error string on failure (never a stack trace).
    op.add_column(
        "media",
        sa.Column("processing_error", sa.String(length=500), nullable=False, server_default=""),
    )
    # How many processing attempts have been made (retry system).
    op.add_column(
        "media",
        sa.Column("processing_attempts", sa.BigInteger(), nullable=False, server_default="0"),
    )
    # When processing reached READY or FAILED (nullable).
    op.add_column(
        "media",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Object-storage keys for the derived variants (nullable until created).
    op.add_column("media", sa.Column("optimized_key", sa.String(length=500), nullable=True))
    op.add_column("media", sa.Column("thumbnail_key", sa.String(length=500), nullable=True))
    op.add_column("media", sa.Column("poster_key", sa.String(length=500), nullable=True))

    # Sizes of the derived variants (bytes).
    op.add_column("media", sa.Column("optimized_size", sa.BigInteger(), nullable=True))
    op.add_column("media", sa.Column("thumbnail_size", sa.BigInteger(), nullable=True))
    op.add_column("media", sa.Column("poster_size", sa.BigInteger(), nullable=True))

    # MIME types of the derived variants.
    op.add_column("media", sa.Column("optimized_mime_type", sa.String(length=120), nullable=True))
    op.add_column("media", sa.Column("thumbnail_mime_type", sa.String(length=120), nullable=True))

    # Media intrinsic metadata (filled by processing).
    op.add_column("media", sa.Column("width", sa.BigInteger(), nullable=True))
    op.add_column("media", sa.Column("height", sa.BigInteger(), nullable=True))
    op.add_column("media", sa.Column("thumbnail_width", sa.BigInteger(), nullable=True))
    op.add_column("media", sa.Column("thumbnail_height", sa.BigInteger(), nullable=True))
    # For videos: duration in seconds.
    op.add_column("media", sa.Column("duration_seconds", sa.Float(), nullable=True))

    # Useful index for listing/filtering by processing state.
    op.create_index("ix_media_processing_status", "media", ["processing_status"])


def downgrade() -> None:
    op.drop_index("ix_media_processing_status", table_name="media")
    op.drop_column("media", "duration_seconds")
    op.drop_column("media", "thumbnail_height")
    op.drop_column("media", "thumbnail_width")
    op.drop_column("media", "height")
    op.drop_column("media", "width")
    op.drop_column("media", "thumbnail_mime_type")
    op.drop_column("media", "optimized_mime_type")
    op.drop_column("media", "poster_size")
    op.drop_column("media", "thumbnail_size")
    op.drop_column("media", "optimized_size")
    op.drop_column("media", "poster_key")
    op.drop_column("media", "thumbnail_key")
    op.drop_column("media", "optimized_key")
    op.drop_column("media", "processed_at")
    op.drop_column("media", "processing_attempts")
    op.drop_column("media", "processing_error")
    op.drop_column("media", "processing_status")
    sa.Enum(
        "QUEUED", "PROCESSING", "READY", "FAILED", name="processing_status"
    ).drop(op.get_bind(), checkfirst=True)
