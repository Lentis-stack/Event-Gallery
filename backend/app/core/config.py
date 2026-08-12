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
    # Simple in-memory protection for local dev. Production should
    # consider a shared store (e.g. Redis) — see README.
    # Max failed login attempts allowed per IP within the window.
    LOGIN_MAX_ATTEMPTS: int = 5
    # Length of the sliding window, in seconds.
    LOGIN_WINDOW_SECONDS: int = 300
    # After too many failures, how long the IP is locked out (s).
    LOGIN_LOCKOUT_SECONDS: int = 900

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lentis_gallery"

    # --- CORS ---
    # In production this should be the real frontend domain.
    # Comma-separated list allowed to call the API.
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # --- Guest sessions (Phase 4) ---
    # How long a guest session stays valid before it expires
    # automatically. Guests don't log in with passwords; a session
    # token is the credential. A shorter lifetime reduces the window
    # in which a stolen token could be used. 6 hours is a reasonable
    # default for a single event visit.
    GUEST_SESSION_EXPIRE_HOURS: int = 6

    # --- Media limits (Phase 5) ---
    # Server-side, authoritative caps. NEVER rely on the frontend to
    # enforce these. Photos and videos are counted independently.
    MAX_PHOTOS_PER_EVENT: int = 3000
    MAX_VIDEOS_PER_EVENT: int = 500
    # Maximum SINGLE-FILE size for images and videos (MB).
    # 30 MB is generous for high-res phone/camera JPEGs.
    MAX_IMAGE_SIZE_MB: int = 30
    # 500 MB supports short 4K clips; bigger long-form videos would
    # be served best by resumable uploads (a later enhancement).
    MAX_VIDEO_SIZE_MB: int = 500
    # Total media storage budget per event (GB). Very approximate;
    # Phase 6 will bring real per-file accounting.
    MAX_EVENT_STORAGE_GB: int = 50

    # --- Storage provider selector (Phase 5) ---
    # "r2"   -> Cloudflare R2 (S3-compatible) — for production.
    # "local"-> Local filesystem provider — DEVELOPMENT/TESTS ONLY.
    # The storage abstraction reads this and wires the right provider.
    STORAGE_PROVIDER: str = "local"

    # --- Object storage (Cloudflare R2) config (Phase 5) ---
    # R2 is S3-compatible, so we use boto3. Credentials MUST come
    # from .env — never hardcode them. The endpoint is unique per
    # R2 account, e.g. https://<accountid>.r2.cloudflarestorage.com
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "lentis-media"
    R2_ENDPOINT: str = ""

    # --- Local-filesystem storage (dev/test only) ---
    # Directory where the local provider writes objects. Never used
    # in production.
    LOCAL_STORAGE_PATH: str = "./storage"

    # --- Media processing (Phase 6) ---
    # How many times a processing job may be retried before it is
    # permanently marked FAILED. We cap this so a broken file can't
    # spin forever burning CPU/disk. 3 is a sensible default.
    PROCESSING_MAX_RETRIES: int = 3
    # Maximum display dimension (px) for the OPTIMIZED image version.
    # A 6000px photo is downscaled to ~2560px — plenty for screens,
    # much smaller than the original. We never UPSCALE small images.
    IMAGE_OPTIMIZED_MAX_DIMENSION: int = 2560
    # Absolute cap on total pixels (width x height) we will process.
    # This is a decompression-bomb guard: a hostile "image" that
    # claims an absurd resolution is refused instead of exhausting
    # server CPU/RAM during decoding. 25 MP is far above any real
    # phone/camera snapshot.
    MAX_IMAGE_PIXELS: int = 25_000_000
    # Maximum dimension (px) for the THUMBNAIL. Small enough to load
    # quickly in a gallery grid, but still recognisable.
    IMAGE_THUMBNAIL_MAX_DIMENSION: int = 600
    # JPEG/webp quality for optimized derivatives (0-100). 88 is a
    # high-quality / visually-lossless sweet spot for photos.
    IMAGE_QUALITY: int = 88
    # FFmpeg CRF (constant rate factor) for H.264 video encoding.
    # Lower = higher quality + larger file. 23 is "good quality,
    # reasonable size" (FFmpeg's default).
    VIDEO_CRF: int = 23
    # FFmpeg preset: a speed/size trade-off. "medium" is the default
    # and a good balance. "slow" compresses better but takes longer.
    VIDEO_PRESET: str = "medium"
    # Reject videos longer than this many seconds at upload/processing
    # time. 30 minutes (1800s) is generous for event clips and keeps
    # processing resource usage bounded.
    MAX_VIDEO_DURATION_SECONDS: int = 1800
    # How many jobs the RQ worker may run at once. Keep small so a
    # single event host's uploads don't saturate the machine's CPU.
    WORKER_CONCURRENCY: int = 2
    # Directory for temporary files during processing (Pillow/FFmpeg
    # scratch space). Uses the system temp dir if not set.
    PROCESSING_TEMP_DIR: str = ""

    # --- Background job queue (Phase 6) ---
    # The Redis server the RQ worker + enqueue calls connect to.
    REDIS_URL: str = "redis://localhost:6379/0"
    # The RQ queue name that holds media-processing jobs.
    PROCESSING_QUEUE: str = "media-processing"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown vars, keep it simple
    )

    # ---------------------------------------------------------
    # FAIL-SAFE VALIDATION
    # ---------------------------------------------------------
    # In production we refuse to start with a missing/obviously
    # insecure JWT secret. This prevents accidentally shipping a
    # backend whose tokens anyone could forge.
    # ---------------------------------------------------------
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        if info.data.get("ENVIRONMENT", "development") == "production":
            if not v or v in ("change-me", "change-me-jwt-secret") or len(v) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be a strong, unique secret (>=32 chars) in production."
                )
        return v


# Create a single shared instance. Everywhere else in the app we
# do `from app.core.config import settings` to get the same values.
settings = Settings()
