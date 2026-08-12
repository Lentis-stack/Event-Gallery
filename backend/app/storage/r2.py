# ============================================================
# Lentis Gallery — Cloudflare R2 Storage Provider
# ------------------------------------------------------------
# This is the PRODUCTION storage provider. It talks to Cloudflare
# R2 over its S3-compatible API using boto3 (the AWS SDK).
#
# R2 IS S3-COMPATIBLE:
#   Cloudflare R2 speaks the same S3 protocol that AWS S3 uses.
#   That means we can use boto3 to upload/delete objects just like
#   we would with S3, but the data actually lives in Cloudflare's
#   network. The config (endpoint, access key, secret key) tells
#   boto3 which S3-compatible service to talk to.
#
# WHY PRIVATE BUCKET?
#   The bucket is PRIVATE by default. Nobody can read an object
#   without a credential or a signed URL. We NEVER make it public.
#   In Phase 6 we generate short-lived signed URLs so the frontend
#   can fetch media without exposing our secret keys.
#
# SECURITY:
#   - Credentials come ONLY from environment/config (never code).
#   - We never return credentials or raw bucket URLs to the frontend.
# ============================================================

import logging
from typing import Any

from app.core.config import settings
from app.storage.base import StorageError

logger = logging.getLogger(__name__)

# boto3 is imported lazily inside methods so that the module can be
# imported even if boto3 isn't installed (e.g. in minimal test envs
# that only use the local provider). This keeps the storage package
# importable everywhere.
def _get_client() -> Any:
    """Create (and cache) a boto3 S3 client pointed at R2."""
    import boto3  # type: ignore

    if not (settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_ENDPOINT):
        raise StorageError(
            "R2 credentials are not configured. Set R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY, and R2_ENDPOINT in .env."
        )

    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",  # R2 uses this sentinel
    )


class R2StorageProvider:
    """Production object-storage provider backed by Cloudflare R2."""

    def __init__(self) -> None:
        self._bucket = settings.R2_BUCKET_NAME

    # ------------------------------------------------------------
    # StorageProvider contract
    # ------------------------------------------------------------

    def save_object(self, key: str, data: bytes, content_type: str) -> None:
        """
        Upload `data` to R2 at `key` with the given MIME type.
        Raises StorageError if the upload fails.
        """
        try:
            client = _get_client()
            client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            logger.info("R2 object saved key=%s", key)
        except Exception as exc:  # noqa: BLE001 — surface any provider error
            logger.error("R2 save failed key=%s: %s", key, exc)
            raise StorageError("Failed to store media in object storage.") from exc

    def download_object(self, key: str) -> bytes:
        """
        Read the object at `key` from R2 and return its raw bytes.
        Raises StorageError if the object is missing or unreadable.
        Phase 6 uses this so the processing worker can read the
        original bytes back out of object storage.
        """
        try:
            client = _get_client()
            resp = client.get_object(Bucket=self._bucket, Key=key)
            data = resp["Body"].read()
            logger.info("R2 object downloaded key=%s", key)
            return data
        except Exception as exc:  # noqa: BLE001
            logger.error("R2 download failed key=%s: %s", key, exc)
            raise StorageError("Failed to read media from object storage.") from exc

    def delete_object(self, key: str) -> None:
        """
        Delete the object at `key` from R2. Deleting a non-existent
        key is treated as success (idempotent). Raises StorageError
        only on a real failure.
        """
        try:
            client = _get_client()
            client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("R2 object deleted key=%s", key)
        except Exception as exc:  # noqa: BLE001
            logger.error("R2 delete failed key=%s: %s", key, exc)
            raise StorageError("Failed to delete media from object storage.") from exc
