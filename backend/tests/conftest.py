# ============================================================
# Lentis Gallery — Pytest Configuration & Fixtures
# ------------------------------------------------------------
# This file sets up a SAFE, ISOLATED test database for the test
# suite. It uses an in-memory SQLite database that is created
# fresh for every test session and destroyed when tests finish.
#
# IMPORTANT:
#   - This SQLite database is used ONLY for automated tests.
#   - Production and normal development use PostgreSQL (see
#     DATABASE_URL in .env). We never point tests at production.
#   - Using an isolated in-memory DB is a standard, safe testing
#     strategy: tests run fast, leave no trace, and can never
#     touch real data.
#
# HOW IT WORKS:
#   pytest automatically loads this file (conftest.py) before
#   running any test. We override the app's database dependency
#   (get_db) to use the in-memory DB instead of PostgreSQL, and
#   create all tables at session start.
# ============================================================

import os

# Force the test DB BEFORE importing app modules that read config.
os.environ["DATABASE_URL"] = "sqlite:///./test_lentis.db"
os.environ["ENVIRONMENT"] = "development"  # allow insecure test secret
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-tests-only-1234567890"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Engine bound to an in-memory SQLite DB. StaticPool keeps a single
# shared connection so the DB persists across the test session.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    """Override the app's get_db dependency to use the test DB."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Replace the real dependency with the test one.
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the whole test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Provides a fresh database session for a test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """Yields a FastAPI TestClient for making API requests."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_tables():
    """Clear all rows AND rate limits between tests so tests are independent."""
    from app.core.rate_limit import reset_all_rate_limits
    reset_all_rate_limits()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    reset_all_rate_limits()
