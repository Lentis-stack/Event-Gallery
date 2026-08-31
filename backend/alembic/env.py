# ============================================================
# Lentis Gallery — Alembic Environment (env.py)
# ------------------------------------------------------------
# This file ties Alembic to our application. Alembic normally
# knows nothing about our project, so env.py tells it:
#   1. Where our SQLAlchemy model metadata lives (so Alembic can
#      "see" our tables and generate migrations for them).
#   2. The database URL (read from our .env via app config).
#
# The `target_metadata` below is crucial: it points to our
# Base.metadata. When we run `alembic revision --autogenerate`,
# Alembic compares the current DB schema to the metadata defined
# by our Python models and writes a migration script for the
# difference.
# ============================================================

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import our settings and the Base class so Alembic knows the
# database location and can see our table definitions.
from app.core.config import settings
from app.db.base import Base

# ------------------------------------------------------------------
# IMPORTANT: Import model modules so their tables are registered on
# Base.metadata. Alembic uses this metadata to autogenerate
# migrations. As we add models in later phases, import them here.
# ------------------------------------------------------------------
import app.models.event  # noqa: F401
import app.models.event_guest  # noqa: F401
import app.models.guest  # noqa: F401
import app.models.media  # noqa: F401
import app.models.refresh_token  # noqa: F401
import app.models.user  # noqa: F401

# This is the Alembic Config object, which provides access to
# the values in alembic.ini.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our models' metadata.
# IMPORTANT: We must import our model modules here so their tables
# are registered on Base.metadata. As we add models in later
# phases, we import them here (e.g. `import app.models.user`).
target_metadata = Base.metadata


def get_url() -> str:
    """Return the database URL from our app settings."""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to the DB)."""
    # Put the real URL into the config so the engine uses it.
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
