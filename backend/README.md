# ============================================================
# Lentis Gallery — Backend README
# ------------------------------------------------------------
# This is the entry-point document for the Lentis Gallery backend.
# It explains what we've built in Phase 1 and how to run it.
# ============================================================

# Lentis Gallery — Backend

The production backend for Lentis Gallery, built with **FastAPI**,
**PostgreSQL**, **SQLAlchemy**, and **Alembic**.

## Phase 1 — Foundation (complete)

Files created in this phase:

```
backend/
├── requirements.txt          # Python dependencies
├── .env.example              # Config template (copy to .env)
├── alembic.ini               # Alembic migration config
├── alembic/
│   ├── env.py                # Ties Alembic to our app + DB
│   ├── script.py.mako        # Migration template
│   └── versions/             # Migration scripts (added each phase)
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI app entry point
    ├── core/
    │   ├── __init__.py
    │   └── config.py         # Typed settings from .env
    ├── db/
    │   ├── __init__.py
    │   ├── base.py           # SQLAlchemy Base (all models inherit)
    │   └── session.py        # Engine + DB session dependency
    └── api/
        ├── __init__.py
        └── routes/
            ├── __init__.py
            └── health.py     # GET /api/health endpoint
```

## What you learn in Phase 1

- **FastAPI** turns Python functions into HTTP endpoints.
- **Uvicorn** runs the FastAPI app as a server.
- **Pydantic / Pydantic-Settings** validate data and load `.env`.
- **SQLAlchemy ORM** maps Python classes to PostgreSQL tables.
- **Alembic** version-controls database schema changes.
- **`.env`** keeps secrets out of Git (`.env.example` is the template).

## How to run

### 1. Create your environment file

```bash
Copy-Item .env.example .env   # Windows PowerShell
# then edit .env with real values
```

### 2. Install dependencies (already done)

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Start PostgreSQL

You need PostgreSQL running. Options:
- Install PostgreSQL locally (default: `postgres:postgres@localhost:5432`).
- Or run it in Docker: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres`.

Then create the database:
```sql
CREATE DATABASE lentis_gallery;
```

### 4. Run the backend

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

### 5. Verify

Open http://localhost:8000/api/health → `{"status":"ok","database":"connected"}`
Open http://localhost:8000/docs → interactive API docs

## Phase 6 — Media Processing (complete)

Phase 6 adds a production-oriented async media-processing pipeline.
After a guest uploads an original, a background worker derives
optimized + thumbnail/poster variants. The original is NEVER touched.

### The pipeline

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

### What was built

- `app/processors/image.py` — Pillow: optimized image + thumbnail.
  Never upscales, preserves aspect ratio, corrects EXIF orientation,
  keeps transparency for PNG/WebP, strips metadata, refuses
  decompression bombs beyond `MAX_IMAGE_PIXELS`.
- `app/processors/video.py` — FFmpeg: optimized H.264/AAC MP4
  (`-crf` from `VIDEO_CRF`, `-preset` from `VIDEO_PRESET`,
  `+faststart`) + a poster frame. Poster failure is non-fatal.
- `app/services/media_processing.py` — orchestrates: download original
  → temp file → run processor → upload variants → update DB. Retry
  with `PROCESSING_MAX_RETRIES`; on exhaustion marks `FAILED` with a
  safe error string. The original + Media row are always preserved.
- `app/workers/media_worker.py` — the RQ worker job entrypoint.
- `app/api/routes/media.py` — new `GET /api/events/{slug}/media/{id}/status`.
- `StorageService.download()` — lets the worker read the original.
- Alembic migration `e5f6a7b8c9e0` adds the Phase 6 columns.
- `tests/test_media_processing.py` — comprehensive Phase 6 tests.

### Processing states

`QUEUED` → `PROCESSING` → `READY` (or `FAILED` after max retries).

### How to run Phase 6 locally

You need **three** terminals (this is the simplest reliable setup for
a single developer):

```bash
# Terminal 1 — Redis (needed for the job queue)
redis-server

# Terminal 2 — FastAPI
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload

# Terminal 3 — the RQ worker (does the heavy image/video work)
cd backend
.venv\Scripts\activate
rq worker media-processing --url redis://localhost:6379/0
```

### Install FFmpeg (Windows)

FFmpeg is a system binary (not a Python package). Download a static
build, e.g. from <https://www.gyan.dev/ffmpeg/builds/> (the "release
essentials" zip), extract it, and add the `bin` folder to your PATH.
Verify with:

```bash
ffmpeg -version
```

FFmpeg is only required for VIDEO processing. The test suite detects
it and skips the video integration tests (with an explicit reason) if
it isn't installed.

### Verify processing

1. Upload a photo via `POST /api/events/{slug}/media`.
2. Poll `GET /api/events/{slug}/media/{id}/status` — it should start
   as `QUEUED`, then become `READY` once the worker finishes.
3. Check the response for `optimized: true` and `thumbnail: true`.

### Storage keys (never user filenames)

```
events/{event_id}/media/{media_id}/original
events/{event_id}/media/{media_id}/optimized
events/{event_id}/media/{media_id}/thumbnail
events/{event_id}/media/{media_id}/poster   (video only)
```

### Configuration added

`PROCESSING_MAX_RETRIES`, `IMAGE_OPTIMIZED_MAX_DIMENSION`,
`MAX_IMAGE_PIXELS`, `IMAGE_THUMBNAIL_MAX_DIMENSION`, `IMAGE_QUALITY`,
`VIDEO_CRF`, `VIDEO_PRESET`, `MAX_VIDEO_DURATION_SECONDS`,
`WORKER_CONCURRENCY`, `PROCESSING_TEMP_DIR`, `REDIS_URL`,
`PROCESSING_QUEUE`. See `.env.example`.

## Next phases

We built the foundation. Next: **Phase 2 — Authentication** (users,
Argon2id password hashing, login/logout, roles, authorization).
