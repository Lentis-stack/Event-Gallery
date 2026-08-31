# ============================================================
# Lentis Gallery — Application Settings
# ------------------------------------------------------------
# This module loads ALL configuration from environment variables
# and/or the .env file into typed Python settings.
#
# WHY A SEPARATE CONFIG MODULE?
#   - Central place to read config once.
#   - Typed (we know DATABASE_URL is a string, DEBUG a bool).
#   - Secrets live in .env (not in code, not in Git).
#
# HOW IT WORKS:
#   pydantic-settings reads the .env file and environment
#   variables, then maps them onto the class attributes below.
#   If a variable is missing and has no default, the app fails
#   fast at startup instead of crashing mysteriously later.
#
# PHASE 2 ADDITIONS:
#   - JWT_SECRET_KEY (signs access tokens)
#   - Access/refresh token lifetimes
#   - Login rate-limiting / lockout settings
#   - A validator that FAILS SAFELY in production if the JWT
#     secret is missing or obviously insecure.
# ============================================================

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # --- Application ---
    APP_NAME: str = "Lentis Gallery API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- Security ---
    # OVERRIDE via .env in real use. This default is deliberately
    # insecure so the app fails safe in production if not set.
    SECRET_KEY: str = "change-me"

    # --- JWT (Phase 2) ---
    # The cryptographic secret used to SIGN access tokens.
    # MUST come from .env in any real environment.
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"

    # --- Token lifetimes ---
    # Access tokens are SHORT-LIVED (minutes). If stolen, the
    # damage window is small. Refresh tokens live longer (days)
    # so the user isn't asked to log in constantly.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Login rate limiting / lockout (Phase 2) ---
    # Max failed login attempts allowed per IP within the window.
    LOGIN_MAX_ATTEMPTS: int = 5
    # Length of the sliding window, in seconds.
    LOGIN_WINDOW_SECONDS: int = 300
    # After too many failures, how long the IP is locked out (s).
    LOGIN_LOCKOUT_SECONDS: int = 900

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lentis_gallery"

    # --- CORS ---
    # Comma-separated list of allowed frontend origins.
    # Production MUST set this to the real domain(s).
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # --- API Documentation (SEC-009) ---
    # Must be explicitly set to "true" to enable /docs and /redoc.
    # Production defaults to disabled to prevent API schema discovery.
    ENABLE_DOCS: bool = False

    # --- Guest sessions (Phase 4) ---
    GUEST_SESSION_EXPIRE_HOURS: int = 6

    # --- Rate Limiting (SEC-005/006/008) ---
    # Per IP per hour: guest registrations.
    RATE_LIMIT_GUEST_REGISTRATION: int = 10
    # Per IP per hour: media uploads.
    RATE_LIMIT_MEDIA_UPLOAD: int = 60
    # Per event per IP per hour: media uploads.
    RATE_LIMIT_EVENT_MEDIA_UPLOAD: int = 30

    # --- Media limits (Phase 5) ---
    MAX_PHOTOS_PER_EVENT: int = 10000
    MAX_VIDEOS_PER_EVENT: int = 5000
    # Maximum SINGLE-FILE size for images and videos (MB).
    MAX_IMAGE_SIZE_MB: int = 30
    # 500 MB supports short 4K clips.
    MAX_VIDEO_SIZE_MB: int = 500
    # Total media storage budget per event (GB).
    MAX_EVENT_STORAGE_GB: int = 600

    # --- Request body limits (SEC-020) ---
    # Maximum request body size in bytes (600 MB covers the largest video + overhead).
    MAX_REQUEST_BODY_BYTES: int = 600 * 1024 * 1024

    # --- Storage provider selector ---
    STORAGE_PROVIDER: str = "local"

    # --- Object storage (Cloudflare R2) config ---
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "lentis-media"
    R2_ENDPOINT: str = ""

    # --- Local-filesystem storage (dev/test only) ---
    LOCAL_STORAGE_PATH: str = "./storage"

    # --- Media processing ---
    PROCESSING_MAX_RETRIES: int = 3
    IMAGE_OPTIMIZED_MAX_DIMENSION: int = 2560
    MAX_IMAGE_PIXELS: int = 25_000_000
    IMAGE_THUMBNAIL_MAX_DIMENSION: int = 600
    IMAGE_QUALITY: int = 88
    VIDEO_CRF: int = 23
    VIDEO_PRESET: str = "medium"
    MAX_VIDEO_DURATION_SECONDS: int = 1800
    WORKER_CONCURRENCY: int = 2
    PROCESSING_TEMP_DIR: str = ""

    # --- Background job queue ---
    REDIS_URL: str = "redis://localhost:6379/0"
    PROCESSING_QUEUE: str = "media-processing"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------------------------------------------------
    # Model-level validation (runs after all field validators)
    # ---------------------------------------------------------
    def model_post_init(self, __context) -> None:
        """Cross-field validation that runs after all field validators."""
        env = self.ENVIRONMENT
        if env == "production":
            # SEC: Validate R2 config when using R2 storage
            if self.STORAGE_PROVIDER == "r2":
                missing = []
                if not self.R2_ACCESS_KEY_ID:
                    missing.append("R2_ACCESS_KEY_ID")
                if not self.R2_SECRET_ACCESS_KEY:
                    missing.append("R2_SECRET_ACCESS_KEY")
                if not self.R2_ENDPOINT:
                    missing.append("R2_ENDPOINT")
                if not self.R2_BUCKET_NAME:
                    missing.append("R2_BUCKET_NAME")
                if missing:
                    raise ValueError(
                        f"FATAL: STORAGE_PROVIDER=r2 but missing R2 config: {', '.join(missing)}. "
                        "Set all R2_* environment variables for production."
                    )

    # ---------------------------------------------------------
    # FAIL-SAFE VALIDATION (SEC-001/002/003/004/010)
    # ---------------------------------------------------------
    # In production we refuse to start with any insecure defaults.
    # In development we WARN loudly but allow the app to start.
    # ---------------------------------------------------------
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        insecure_defaults = ("change-me", "change-me-jwt-secret", "")
        env = info.data.get("ENVIRONMENT", "development")
        is_insecure = not v or v in insecure_defaults or len(v) < 32
        if env == "production":
            if is_insecure:
                raise ValueError(
                    "FATAL: JWT_SECRET_KEY must be a strong, unique secret (>=32 chars) in production. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
                )
        elif is_insecure:
            import warnings
            warnings.warn(
                "INSECURE: JWT_SECRET_KEY is using a default value. "
                "Set a unique, strong secret (>=32 chars) in your .env file.",
                stacklevel=2,
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and (not v or v == "change-me" or len(v) < 32):
            raise ValueError(
                "FATAL: SECRET_KEY must be a strong, unique secret (>=32 chars) in production."
            )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production":
            insecure_defaults = (
                "postgresql+psycopg://postgres:postgres@localhost:5432/lentis_gallery",
                "",
            )
            if v in insecure_defaults:
                raise ValueError(
                    "FATAL: DATABASE_URL must be set to a production database URL. "
                    "The default localhost/credentials are not allowed in production."
                )
            # Warn if no SSL
            if "?sslmode=" not in v and "sslmode" not in v:
                import warnings
                warnings.warn(
                    "RECOMMENDED: Add ?sslmode=require to your DATABASE_URL for encrypted connections.",
                    stacklevel=2,
                )
        return v

    @field_validator("FRONTEND_URL")
    @classmethod
    def validate_frontend_url(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production":
            origins = [o.strip() for o in v.split(",") if o.strip()]
            for origin in origins:
                if origin == "*":
                    raise ValueError(
                        "FATAL: FRONTEND_URL must not contain wildcard '*' in production."
                    )
                if not origin.startswith("https://"):
                    import warnings
                    warnings.warn(
                        f"WARNING: CORS origin '{origin}' does not use HTTPS. "
                        "Production should use HTTPS for all allowed origins.",
                        stacklevel=2,
                    )
        return v

    @field_validator("STORAGE_PROVIDER")
    @classmethod
    def validate_storage_provider(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if v not in ("local", "r2"):
            raise ValueError(
                f"STORAGE_PROVIDER must be 'local' or 'r2', got '{v}'."
            )
        if env == "production" and v == "local":
            import warnings
            warnings.warn(
                "WARNING: STORAGE_PROVIDER=local is not recommended for production. "
                "Use 'r2' for Cloudflare R2 object storage.",
                stacklevel=2,
            )
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production":
            if not v or v == "redis://localhost:6379/0":
                raise ValueError(
                    "FATAL: REDIS_URL must be set to a production Redis instance. "
                    "The default localhost URL is not allowed in production."
                )
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug(cls, v: bool, info) -> bool:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and v:
            import warnings
            warnings.warn(
                "WARNING: DEBUG=true in production. Set DEBUG=false for production.",
                stacklevel=2,
            )
        return v


# Create a single shared instance. Everywhere else in the app we
# do `from app.core.config import settings` to get the same values.
settings = Settings()
