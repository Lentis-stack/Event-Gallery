# ============================================================
# Lentis Gallery — Storage Package
# ------------------------------------------------------------
# This package abstracts WHERE the actual media bytes live.
#
# PostgreSQL stores METADATA (the catalogue). The actual files
# (the products in the warehouse) live in OBJECT STORAGE.
#
# WHY AN ABSTRACTION?
#   Our business logic (media_service) should not care whether the
#   bytes are going to Cloudflare R2 or a local folder. It talks to
#   a simple StorageService. Under the hood, that service picks the
#   right "provider" based on configuration:
#
#     StorageService
#          │
#          ├── R2StorageProvider   (production, S3-compatible)
#          └── LocalStorageProvider (development / tests only)
#
# This means we can swap R2 for S3, Backblaze, GCS, etc. later
# WITHOUT rewriting the media system.
# ============================================================

from app.storage.service import StorageService, get_storage_service

__all__ = [
    "StorageService",
    "get_storage_service",
]
