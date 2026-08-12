# ============================================================
# Lentis Gallery — Media Processing Worker (Phase 6)
# ------------------------------------------------------------
# This is the RQ worker job. RQ imports this function by its string
# path ('app.workers.media_worker.process_media_job') and runs it in
# a SEPARATE process from the FastAPI server.
#
# The worker:
#   1. Opens its own DB session (it lives outside any HTTP request,
#      so it cannot use the request-scoped get_db dependency).
#   2. Calls media_processing.process_media().
#
# On success the media becomes READY. On failure the processing
# service either re-queues for another attempt or marks FAILED —
# the worker itself does not need to manage retries.
#
# START THE WORKER (separate terminal from the API):
#   cd backend
#   rq worker media-processing --url redis://localhost:6379/0
# ============================================================

import logging

from app.db.session import SessionLocal
from app.services import media_processing

logger = logging.getLogger(__name__)


def process_media_job(media_id: str) -> None:
    """
    RQ job entrypoint. `media_id` is the record to process. Runs the
    full pipeline (download original -> process -> upload variants ->
    update DB). Any exception is caught and safely recorded by the
    processing service; the ORIGINAL is never deleted.
    """
    db = SessionLocal()
    try:
        media = media_processing.process_media(db, media_id)
        logger.info("Worker finished processing media %s (status=%s)",
                    media_id, media.processing_status.value)
    except Exception as exc:  # noqa: BLE001 — worker must not crash
        # The processing service already recorded the failure and set
        # a safe DB state. We log for the operator.
        logger.error("Worker failed for media %s: %s", media_id, exc)
        # Re-raise so RQ marks the job as failed (its own bookkeeping).
        # The DB state is already correct (QUEUED for retry / FAILED).
        raise
    finally:
        db.close()
