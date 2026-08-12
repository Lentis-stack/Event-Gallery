# Phase 6 — Media Processing Plan

## Goal
Build a production-oriented async media-processing pipeline that runs AFTER
the original upload succeeds. The original is NEVER destroyed or overwritten.

## Architecture
                    GUEST UPLOAD
                         │
                         ▼
                    FASTAPI API
                         │
                         ▼
                  STORE ORIGINAL  (R2 / local)
                         │
                         ▼
                  POSTGRES METADATA (status=QUEUED)
                         │
                         ▼
                    REDIS QUEUE (RQ)
                         │
                         ▼
                   RQ WORKER (media_worker)
                    /              \
              Pillow (image)   FFmpeg (video)
                 │                 │
                 ▼                 ▼
          optimized + thumbnail  optimized + poster
                 │                 │
                 └───────┬─────────┘
                         ▼
                  R2 / local STORAGE
                         │
                         ▼
                  DB status=READY
                         │
                         ▼
                   HOST GALLERY

## Key design principles
1. Original preserved as source of truth.
2. Derived variants stored separately: optimized / thumbnail / poster.
3. Processing is ASYNC (enqueue → return; worker processes).
4. Redis + RQ (NOT Celery) — simplest reliable background queue.
5. Retry with configurable max attempts; on failure status=FAILED, original kept.
6. Storage providers get a `download_object()` method so the worker can read
   the original bytes.
7. Event isolation & authorization preserved on the processing-status endpoint.

## Files
- Modify: app/models/media.py (ProcessingStatus + variant columns)
- Modify: app/core/config.py (processing settings)
- Modify: app/storage/base.py, local.py, r2.py, service.py (download_object)
- Create: app/processors/image.py, video.py
- Create: app/services/media_processing.py
- Create: app/workers/media_worker.py
- Modify: app/services/media.py (enqueue on upload)
- Modify: app/api/routes/media.py (status endpoint)
- Create: alembic migration
- Modify: requirements.txt (Pillow, redis, rq)
- Create: tests/test_media_processing.py
- Update: TODO.md, README.md, .env.example
