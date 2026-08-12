# ============================================================
# Lentis Gallery — Workers Package (Phase 6)
# ------------------------------------------------------------
# The "worker" is a separate process that RQ uses to run background
# jobs. It picks media ids off the Redis queue and calls the media
# processing service. This keeps heavy Pillow/FFmpeg work OUT of the
# FastAPI request path.
#
# The worker is started separately from the API (see README):
#   rq worker media-processing --url redis://localhost:6379/0
#
# The enqueue function references the job by its importable path
# ('app.workers.media_worker.process_media_job'), so RQ can import
# and run it inside the worker process.
# ============================================================
