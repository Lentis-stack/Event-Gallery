# ============================================================
# Lentis Gallery — Migration: Create users + refresh_tokens
# ------------------------------------------------------------
# Revision ID: a1b2c3d4e5f6
# Revises: (none — first migration)
#
# This migration creates the two tables needed for Phase 2
# authentication:
#   - users: the platform accounts (ADMIN / HOST roles)
#   - refresh_tokens: server-side refresh-token sessions
#
# WHY separate user_role as a PostgreSQL ENUM?
#   An enum prevents arbitrary/invalid role strings at the
#   database level, matching the Python UserRole enum.
# ============================================================

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop leftover objects from any previous partial runs.
    op.execute("DROP TABLE IF EXISTS refresh_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TYPE IF EXISTS user_role")

    # Create the user_role enum type.
    op.execute("CREATE TYPE user_role AS ENUM ('ADMIN', 'HOST')")

    # --- users table ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Text(),
            nullable=False,
            server_default="HOST",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Email must be unique (one account per email) + indexed.
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- refresh_tokens table ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    # Indexes: finding a token by hash (login/refresh lookups) and
    # listing sessions for a user.
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade() -> None:
    # Rollback: drop tables and the enum type, in reverse order.
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    # Drop the enum type.
    op.execute("DROP TYPE IF EXISTS user_role")
