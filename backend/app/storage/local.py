# ============================================================
# Lentis Gallery — Local Filesystem Storage Provider
# ------------------------------------------------------------
# DEVELOPMENT / TEST ONLY.
#
# This provider writes object bytes to a folder on the local disk
# instead of Cloudflare R2. It exists so you can run the entire
# backend (and the test suite) WITHOUT setting up R2 credentials or
# installing extra infrastructure.
#
# WARNING:
#   - NEVER use this for production. The app server's local disk is
#     not durable or scalable (a real object store is).
#   - It is selected by STORAGE_PROVIDER=local (the default) and is
#     what the test suite uses.
#
# It implements the SAME StorageProvider contract as the R2
# provider, so the rest of the app cannot tell the difference.
# ============================================================

import logging
import os
from pathlib import Path

from app.core.config import settings
from app.storage.base import StorageError

logger = logging.getLogger(__name__)


class LocalStorageProvider:
    """Development-only provider that stores objects on the local disk."""

    def __init__(self) -> None:
        # Resolve the base dir once. Objects are stored under it,
        # mirroring the object key (which itself contains slashes
        # like events/{id}/media/{id}/original).
        self._base = Path(settings.LOCAL_STORAGE_PATH).resolve()

    def _resolve(self, key: str) -> Path:
        """
        Turn an object key into a safe absolute path under the base
        directory. This is a DEFENSE AGAINST PATH TRAVERSAL: we
        join the key onto the base and then verify the result is
        still inside the base. If a malicious key ever tried to
        escape (e.g. with '..'), we refuse.
        """
        # Normalize and reject any key that tries to climb up.
        candidate = (self._base / key).resolve()
        if not str(candidate).startswith(str(self._base)):
            raise StorageError("Invalid storage key: path traversal blocked.")
        return candidate

    # ------------------------------------------------------------
    # StorageProvider contract
    # ------------------------------------------------------------

    def save_object(self, key: str, data: bytes, content_type: str) -> None:
        """Write `data` to a local file at `key`. (content_type is
        not persisted in Phase 5's local provider; it exists to match
        the interface.)"""
        try:
            path = self._resolve(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            logger.info("Local object saved key=%s", key)
        except StorageError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Local save failed key=%s: %s", key, exc)
            raise StorageError("Failed to store media locally.") from exc

    def download_object(self, key: str) -> bytes:
        """Read and return the raw bytes of the local file at `key`.
        Raises StorageError if the file is missing or unreadable.
        Phase 6 uses this so the processing worker can read the
        original bytes back out of storage."""
        try:
            path = self._resolve(key)
            if not path.exists():
                raise StorageError(f"Object not found: {key}")
            data = path.read_bytes()
            logger.info("Local object downloaded key=%s", key)
            return data
        except StorageError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Local download failed key=%s: %s", key, exc)
            raise StorageError("Failed to read media locally.") from exc

    def delete_object(self, key: str) -> None:
        """Remove the local file at `key`. Missing file = no-op."""
        try:
            path = self._resolve(key)
            if path.exists():
                path.unlink()
                logger.info("Local object deleted key=%s", key)
        except StorageError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Local delete failed key=%s: %s", key, exc)
            raise StorageError("Failed to delete media locally.") from exc
