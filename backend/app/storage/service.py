# ============================================================
# Lentis Gallery — Storage Service (entry point)
# ------------------------------------------------------------
# This is the SINGLE place the rest of the app talks to for object
# storage. It reads the configured provider ('r2' or 'local') and
# exposes a simple, provider-agnostic API.
#
# WHY A SEPARATE SERVICE on top of the provider?
#   - The media_service should say "storage.upload(...)" and not
#     care whether that means R2 or a local folder.
#   - If we switch providers, only this file changes.
#   - We keep a single cached instance so we don't create a new
#     boto3 client / base path on every request.
# ============================================================

import logging

from app.core.config import settings
from app.storage.base import StorageError, StorageProvider
from app.storage.local import LocalStorageProvider
from app.storage.r2 import R2StorageProvider

logger = logging.getLogger(__name__)


def _build_provider() -> StorageProvider:
    """Instantiate the provider selected by STORAGE_PROVIDER."""
    provider_name = (settings.STORAGE_PROVIDER or "local").strip().lower()
    if provider_name == "r2":
        logger.info("Using Cloudflare R2 storage provider.")
        return R2StorageProvider()
    if provider_name == "local":
        logger.info("Using LOCAL storage provider (development only).")
        return LocalStorageProvider()
    raise ValueError(
        f"Unknown STORAGE_PROVIDER '{provider_name}'. Use 'r2' or 'local'."
    )


class StorageService:
    """Thin, provider-agnostic object-storage facade."""

    def __init__(self, provider: StorageProvider | None = None) -> None:
        # Allow injecting a provider (used by tests). Otherwise build
        # from config.
        self._provider = provider if provider is not None else _build_provider()

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        """Store an object. Raises StorageError on failure."""
        self._provider.save_object(key, data, content_type)

    def delete(self, key: str) -> None:
        """Delete an object. Raises StorageError on failure."""
        self._provider.delete_object(key)

    def download(self, key: str) -> bytes:
        """
        Read and return the raw bytes of the object at `key`.
        Raises StorageError if the object is missing or unreadable.

        PHASE 6: The background processing worker calls this to read
        the preserved ORIGINAL bytes back out of object storage so
        Pillow/FFmpeg can derive the optimized/thumbnail/poster
        variants. Being provider-agnostic, this works identically for
        R2 (production) and the local provider (dev/tests).
        """
        return self._provider.download_object(key)


# A convenience for callers that don't need dependency injection.
# We build it lazily so tests can override the provider if they want.
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Return the shared StorageService instance (cached)."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
