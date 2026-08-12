# ============================================================
# Lentis Gallery — Database Session
# ------------------------------------------------------------
# This module creates the connection to PostgreSQL and provides
# a "session" that our endpoints use to talk to the database.
#
# KEY IDEA — ENGINE vs SESSION:
#   - ENGINE: the low-level connection pool to PostgreSQL.
#     It manages the actual network connections. We create ONE
#     engine for the whole app and reuse it.
#   - SESSION: a unit of work. Each request gets its own session.
#     We add/query objects through the session, then "commit".
#     The session wraps work in a TRANSACTION automatically.
#
# get_db() is a FastAPI DEPENDENCY. Every endpoint that needs the
# database declares `db: Session = Depends(get_db)`. FastAPI then:
#   1. Opens a session when the request comes in.
#   2. Passes it to the endpoint.
#   3. Closes it when the request finishes (even on errors).
# This is clean and prevents connection leaks.
# ============================================================

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Create the engine. `pool_pre_ping=True` checks an existing
# connection is still alive before reusing it (avoids stale
# connection errors after the DB restarts).
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# sessionmaker is a factory that creates new Session objects.
# We configure it once with our engine.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # manual commit — we control when data is saved
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # Always close the session, success or failure.
        db.close()
