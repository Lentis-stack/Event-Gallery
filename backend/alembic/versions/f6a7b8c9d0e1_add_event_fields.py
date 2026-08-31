"""Add event_type, location, description, storage fields to events

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9e0
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("event_type", sa.String(100), nullable=True))
    op.add_column("events", sa.Column("location", sa.String(255), nullable=True))
    op.add_column("events", sa.Column("description", sa.String(2000), nullable=True))
    op.add_column("events", sa.Column("storage_limit_gb", sa.Integer(), server_default="50", nullable=False))
    op.add_column("events", sa.Column("storage_used_bytes", sa.BigInteger(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("events", "storage_used_bytes")
    op.drop_column("events", "storage_limit_gb")
    op.drop_column("events", "description")
    op.drop_column("events", "location")
    op.drop_column("events", "event_type")
