# ============================================================
# Lentis Gallery — Production Configuration Validation Tests
# ============================================================
# Tests that verify the application rejects insecure configuration
# when ENVIRONMENT=production.
# ============================================================

import os
import pytest


def _make_settings(**overrides):
    """Create a fresh Settings instance with overridden env vars."""
    # Clear any cached settings
    import importlib
    import app.core.config
    importlib.reload(app.core.config)

    # Set env vars before importing
    env_backup = {}
    for key, value in overrides.items():
        env_backup[key] = os.environ.get(key)
        os.environ[key] = str(value)

    try:
        # Force reload of settings module
        importlib.reload(app.core.config)
        return app.core.config.settings
    finally:
        # Restore env vars
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TestProductionJWTValidation:
    """SEC-001: JWT secret must be secure in production."""

    def test_production_rejects_default_jwt_secret(self):
        """Production must fail with default JWT_SECRET_KEY."""
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            _make_settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="change-me-jwt-secret",
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )

    def test_production_rejects_short_jwt_secret(self):
        """Production must fail with short JWT_SECRET_KEY."""
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            _make_settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="short",
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )

    def test_production_rejects_empty_jwt_secret(self):
        """Production must fail with empty JWT_SECRET_KEY."""
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            _make_settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="",
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )

    def test_production_accepts_strong_jwt_secret(self):
        """Production must accept a strong JWT_SECRET_KEY."""
        settings = _make_settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a-very-strong-secret-key-that-is-at-least-32-chars",
            SECRET_KEY="a-very-strong-secret-key-that-is-at-least-32-chars",
            DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db?sslmode=require",
            REDIS_URL="redis://prod-redis:6379/0",
            FRONTEND_URL="https://lentis.gallery",
        )
        assert settings.JWT_SECRET_KEY == "a-very-strong-secret-key-that-is-at-least-32-chars"


class TestProductionSecretKeyValidation:
    """SEC-002: SECRET_KEY must be secure in production."""

    def test_production_rejects_default_secret_key(self):
        """Production must fail with default SECRET_KEY."""
        with pytest.raises(ValueError, match="SECRET_KEY"):
            _make_settings(
                ENVIRONMENT="production",
                SECRET_KEY="change-me",
                JWT_SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )


class TestProductionDatabaseValidation:
    """SEC-003: DATABASE_URL must be explicit in production."""

    def test_production_rejects_default_database_url(self):
        """Production must fail with default DATABASE_URL."""
        with pytest.raises(ValueError, match="DATABASE_URL"):
            _make_settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="a" * 32,
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/lentis_gallery",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )

    def test_production_rejects_empty_database_url(self):
        """Production must fail with empty DATABASE_URL."""
        with pytest.raises(ValueError, match="DATABASE_URL"):
            _make_settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="a" * 32,
                SECRET_KEY="a" * 32,
                DATABASE_URL="",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )


class TestProductionRedisValidation:
    """SEC-004: REDIS_URL must be explicit in production."""

    def test_production_rejects_default_redis_url(self):
        """Production must fail with default REDIS_URL."""
        with pytest.raises(ValueError, match="REDIS_URL"):
            _make_settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="a" * 32,
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://localhost:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )


class TestProductionCORSValidation:
    """SEC-010: CORS must not allow wildcards in production."""

    def test_production_rejects_wildcard_cors(self):
        """Production must fail with FRONTEND_URL=*."""
        with pytest.raises(ValueError, match="wildcard"):
            _make_settings(
                ENVIRONMENT="production",
                JWT_SECRET_KEY="a" * 32,
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="*",
            )


class TestProductionStorageValidation:
    """Storage provider must be valid."""

    def test_rejects_invalid_storage_provider(self):
        """Must reject unknown storage providers."""
        with pytest.raises(ValueError, match="STORAGE_PROVIDER"):
            _make_settings(
                STORAGE_PROVIDER="s3",
                JWT_SECRET_KEY="a" * 32,
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )


class TestProductionR2Validation:
    """R2 credentials must be present when using R2 storage."""

    def test_production_r2_requires_credentials(self):
        """Production with STORAGE_PROVIDER=r2 must have all R2 config."""
        with pytest.raises(ValueError, match="R2"):
            _make_settings(
                ENVIRONMENT="production",
                STORAGE_PROVIDER="r2",
                R2_ACCESS_KEY_ID="",
                R2_SECRET_ACCESS_KEY="",
                R2_ENDPOINT="",
                JWT_SECRET_KEY="a" * 32,
                SECRET_KEY="a" * 32,
                DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db",
                REDIS_URL="redis://prod-redis:6379/0",
                FRONTEND_URL="https://lentis.gallery",
            )


class TestDevelopmentStillWorks:
    """Development mode should accept defaults."""

    def test_development_accepts_defaults(self):
        """Development mode should work with default values."""
        settings = _make_settings(
            ENVIRONMENT="development",
            JWT_SECRET_KEY="change-me-jwt-secret",
        )
        # In development, insecure defaults are allowed (with warnings)
        assert settings.ENVIRONMENT == "development"
        assert settings.STORAGE_PROVIDER in ("local", "r2")
