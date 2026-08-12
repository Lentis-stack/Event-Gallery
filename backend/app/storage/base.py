# ============================================================
# Lentis Gallery — Storage Provider Interface (base)
# ------------------------------------------------------------
# This defines the CONTRACT every storage provider must satisfy.
# It's a Python "Protocol" (a structural interface) — any class
# with the same method signatures can act as a storage provider.
#
# WHY A PROTOCOL (not an abstract base class)?
#   - It lets us depend on the INTERFACE, not a concrete class.
#   - Both the R2 provider and the local provider implement these
#     few methods identically from the caller's point of view.
#   - If we later add S3/Backblaze, they just implement the same
#     contract and nothing else in the app changes.
#
# THE OPERATIONS IN PHASE 5:
#   - save_object(key, bytes, content_type)   -> store a file
#   - delete_object(key)                      -> remove a file
#
# PHASE 6 ADDS:
#   - download_object(key) -> read a file's bytes (the processing
#     worker needs this to read the original from storage).
# ============================================================

from typing import Protocol


class StorageProvider(Protocol):
    """Interface every object-storage provider implements."""

    def save_object(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """
        Store `data` at the object key `key` with the given MIME
        content type. Raises StorageError on failure.
        """
        ...

    def delete_object(self, key: str) -> None:
        """
        Remove the object at `key`. Raises StorageError if the
        delete fails (but deleting a non-existent key is a no-op).
        """
        ...

    def download_object(self, key: str) -> bytes:
        """
        Fetch and return the raw bytes of the object at `key`.
        Raises StorageError if the object is missing or unreadable.
        Phase 6 adds this so the processing worker can read the
        original bytes from storage.
        """
        ...


class StorageError(Exception):
    """Raised when an object-storage operation fails."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message
