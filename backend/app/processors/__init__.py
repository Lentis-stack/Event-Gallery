# ============================================================
# Lentis Gallery — Media Processors Package (Phase 6)
# ------------------------------------------------------------
# Each processor takes a PRESERVED ORIGINAL (a temp file on disk)
# and derives small, high-quality variants:
#
#   ImageProcessor  -> optimized image + thumbnail
#   VideoProcessor  -> optimized H.264/MP4 + poster frame
#
# The ORIGINAL is never modified. Processors write their outputs to
# temporary files; the caller (media_processing service) uploads
# those files to object storage and then deletes every temp file.
#
# Workers choose the correct processor based on Media.media_type.
# ============================================================
