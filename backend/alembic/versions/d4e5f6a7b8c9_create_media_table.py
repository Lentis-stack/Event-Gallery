# ============================================================
# Lentis Gallery — Migration: Create media table
# ------------------------------------------------------------
# Revision ID: d4e5f6a7b8c9
# Revises: c3d4e5f6a7b8  (chained after the guests migration)
#
# Phase 5. Creates the 'media' table.
#
# IMPORTANT STORAGE RULE:
#   The media table stores only METADATA about a media item. The
#   actual image/video bytes live in OBJECT STORAGE (Cloudflare R2
#   in production). PostgreSQL never stores the binaries.
#
# Foreign keys:
#   - media.event_id -> events.id   ON DELETE CASCADE
#   - media.guest_id -> guests.id   ON DELETE CASCADE
#
# If an event or guest is deleted, its media metadata rows are
# removed too (no orphans). Object-storage cleanup is handled by
# the application layer.
# ============================================================

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Success: create the enum types first.
    op.execute("""DROP TYPE IF EXISTS media_type; CREATE TYPE media_type AS ENUM ('PHOTO', 'VIDEO')""")
    op.execute("""DROP TYPE IF EXISTS media_status; CREATE TYPE media_status AS ENUM ('UPLOADED', 'PENDING')""")

    # --- media table ---
    op.create_table(
        "media",
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Which event this media belongs to. CASCADE on event delete.
        sa.Column("event_id", sa.String(length=36), nullable=False),
        # Which guest uploaded it. CASCADE on guest delete.
        sa.Column("guest_id", sa.String(length=36), nullable=False),
        # Safe display filename (never used as a storage path).
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        # The object-storage key where the bytes live.
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column(
            "media_type",
            sa.Text(),
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        # SHA-256 hex digest of the object's bytes.
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="UPLOADED",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.id"], ondelete="CASCADE"),
    )

    # Indexes for the quota + listing queries the app runs most:
    #   - count an event's photos/videos  -> (event_id, media_type)
    #   - list a guest's media            -> (event_id, guest_id)
    op.create_index("ix_media_event_id", "media", ["event_id"])
    op.create_index("ix_media_guest_id", "media", ["guest_id"])
    op.create_index("ix_media_event_type", "media", ["event_id", "media_type"])
    op.create_index("ix_media_event_guest", "media", ["event_id", "guest_id"])
    op.create_index("ix_media_created_at", "media", ["created_at"])


def downgrade() -> None:
    # Roll back in reverse order.
    op.drop_index("ix_media_created_at", table_name="media")
    op.drop_index("ix_media_event_guest", table_name="media")
    op.drop_index("ix_media_event_type", table_name="media")
    op.drop_index("ix_media_guest_id", table_name="media")
    op.drop_index("ix_media_event_id", table_name="media")
    op.drop_table("media")
    sa.Text().drop(
        op.get_bind(), checkfirst=True
    )
    sa.Text().drop(
        op.get_bind(), checkfirst=True
    )
