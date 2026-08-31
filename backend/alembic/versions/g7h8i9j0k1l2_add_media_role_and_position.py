"""Add media_role and position columns to media table

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa

revision = "g7h8i9j0k1l2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the media_role enum type
    media_role_enum = sa.Enum("HERO", "SLIDESHOW", "GALLERY", name="media_role")
    media_role_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "media",
        sa.Column(
            "media_role",
            sa.Enum("HERO", "SLIDESHOW", "GALLERY", name="media_role"),
            nullable=False,
            server_default="GALLERY",
        ),
    )
    op.add_column(
        "media",
        sa.Column("position", sa.Integer(), nullable=True),
    )
    # Index for querying slideshow media by role + position
    op.create_index(
        "ix_media_event_role_position",
        "media",
        ["event_id", "media_role", "position"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_event_role_position", table_name="media")
    op.drop_column("media", "position")
    op.drop_column("media", "media_role")
    sa.Enum(name="media_role").drop(op.get_bind(), checkfirst=True)
