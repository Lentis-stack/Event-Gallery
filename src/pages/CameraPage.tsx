// ============================================================
// Lentis Gallery — Camera Page (/e/:slug/camera)
// ============================================================
// Guest camera page. Camera opens immediately after name entry.
// Photos and videos auto-upload. Guest can view their personal gallery.
// Supports device media upload with queue, offline awareness, retry.
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import FilmShell from '../components/FilmShell';
import ImageSlideshow from '../components/ImageSlideshow';
import EventBranding from '../components/EventBranding';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';
import CameraCapture from '../components/camera/CameraCapture';
import { useUploadQueue, type UploadQueueItem } from '../hooks/useUploadQueue';
import {
  guestUploadMedia,
  getPublicEventMedia,
  getGuestMedia,
  getMediaUrl,
  type PublicMediaResponse,
  type GuestMediaItem,
} from '../services/api';

export default function CameraPage() {
  const navigate = useNavigate();
  const { slug } = useParams<{ slug: string }>();
  const guestName = sessionStorage.getItem('guestName');
  const guestToken = sessionStorage.getItem('guestToken');

  const [cameraMedia, setCameraMedia] = useState<PublicMediaResponse | null>(null);
  const [myMedia, setMyMedia] = useState<GuestMediaItem[]>([]);
  const [showGallery, setShowGallery] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState<GuestMediaItem | null>(null);
  const [showUploadQueue, setShowUploadQueue] = useState(false);

  // Upload function
  const doUpload = useCallback(
    async (file: File) => {
      if (!slug || !guestToken) throw new Error('No session');
      await guestUploadMedia(slug, guestToken, file);
    },
    [slug, guestToken]
  );

  const reloadMedia = useCallback(() => {
    loadMyMedia();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const uploadQueue = useUploadQueue({ onUpload: doUpload, onComplete: reloadMedia });

  // Redirect if no guest session
  useEffect(() => {
    if (!guestName || !guestToken || !slug) {
      navigate(slug ? `/e/${slug}` : '/', { replace: true });
    }
  }, [guestName, guestToken, slug, navigate]);

  // Load camera slideshow media
  useEffect(() => {
    if (!slug) return;
    getPublicEventMedia(slug).then(setCameraMedia).catch(() => {});
  }, [slug]);

  // Load personal media
  const loadMyMedia = useCallback(async () => {
    if (!slug || !guestToken) return;
    try {
      const res = await getGuestMedia(slug, guestToken);
      setMyMedia(res.items);
    } catch {
      // Silently fail
    }
  }, [slug, guestToken]);

  useEffect(() => {
    loadMyMedia();
  }, [loadMyMedia]);

  const cameraSlides = cameraMedia?.camera_slideshow || [];

  // Auto-upload on camera capture — goes through the queue
  const handleCapture = useCallback(
    (file: File) => {
      uploadQueue.enqueue([file]);
    },
    [uploadQueue]
  );

  // Device media upload — multi-file
  const handleDeviceUpload = useCallback(
    (files: File[]) => {
      // Validate file sizes (50MB max per file)
      const maxSize = 50 * 1024 * 1024;
      const valid = files.filter((f) => f.size <= maxSize);
      if (valid.length < files.length) {
        // Some files were too large — handled by queue status
      }
      if (valid.length > 0) {
        uploadQueue.enqueue(valid);
        setShowUploadQueue(true);
      }
    },
    [uploadQueue]
  );

  // Active upload items (queued + uploading)
  const activeUploads = uploadQueue.items.filter(
    (i) => i.status === 'queued' || i.status === 'uploading'
  );

  return (
    <PageTransition>
      <FilmShell>
        <div className="camera-page">
          {/* Camera slideshow background */}
          {cameraSlides.length > 0 && (
            <div className="camera-page__bg">
              <ImageSlideshow images={cameraSlides} />
            </div>
          )}

          {/* Dark overlay */}
          <div className="camera-page__overlay" />

          <div className="camera-page__content">
            {/* Minimal header */}
            <header className="camera-page__header">
              <EventBranding showPlatform={false} as="h2" className="camera-page__branding" />
              <p className="camera-page__welcome">Welcome, {guestName}.</p>
            </header>

            {/* Offline banner */}
            <AnimatePresence>
              {!uploadQueue.isOnline && (
                <motion.div
                  className="camera-offline-banner"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <span className="camera-offline-banner__icon">⚠</span>
                  <span>You're offline. Uploads will resume when connection returns.</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Camera */}
            <div className="camera-page__camera">
              <CameraCapture
                onCapture={handleCapture}
                onDeviceUpload={handleDeviceUpload}
                onOpenGallery={() => setShowGallery(true)}
                mediaCount={myMedia.length}
                guestName={guestName || 'Guest'}
              />
            </div>

            {/* Upload queue indicator — shows when items are pending */}
            <AnimatePresence>
              {activeUploads.length > 0 && (
                <motion.div
                  className="camera-upload-bar"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                >
                  <button
                    type="button"
                    className="camera-upload-bar__toggle"
                    onClick={() => setShowUploadQueue(!showUploadQueue)}
                  >
                    <span className="camera-upload-bar__spinner" />
                    <span>
                      Uploading {activeUploads.length} {activeUploads.length === 1 ? 'memory' : 'memories'}…
                    </span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Upload queue detail panel */}
            <AnimatePresence>
              {showUploadQueue && uploadQueue.items.length > 0 && (
                <motion.div
                  className="camera-upload-panel"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 20 }}
                >
                  <div className="camera-upload-panel__header">
                    <span>Upload Queue</span>
                    <button
                      type="button"
                      className="camera-upload-panel__close"
                      onClick={() => setShowUploadQueue(false)}
                      aria-label="Close upload queue"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="camera-upload-panel__list">
                    {uploadQueue.items.map((item) => (
                      <UploadItem key={item.id} item={item} onRetry={uploadQueue.retry} />
                    ))}
                  </div>
                  {uploadQueue.failedCount > 0 && (
                    <button
                      type="button"
                      className="camera-upload-panel__retry-all"
                      onClick={uploadQueue.retryAll}
                    >
                      Retry All Failed
                    </button>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Toast notifications for captures */}
          <div className="camera-toast-container">
            <AnimatePresence>
              {uploadQueue.items
                .filter((t) => t.status === 'uploaded' || t.status === 'failed')
                .slice(-3)
                .map((toast) => (
                  <motion.div
                    key={toast.id}
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className={`camera-toast camera-toast--${toast.status === 'uploaded' ? 'success' : 'error'}`}
                  >
                    {toast.status === 'uploaded' ? '✓ ' : '✕ '}
                    {toast.status === 'uploaded'
                      ? `${toast.type === 'video' ? 'Video' : 'Photo'} uploaded!`
                      : toast.error || 'Upload failed'}
                  </motion.div>
                ))}
            </AnimatePresence>
          </div>

          {/* Personal Gallery Overlay */}
          <AnimatePresence>
            {showGallery && (
              <motion.div
                className="gallery-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="gallery-overlay__header">
                  <button
                    type="button"
                    className="gallery-overlay__back"
                    onClick={() => { setShowGallery(false); setSelectedMedia(null); }}
                    aria-label="Close gallery"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="15 18 9 12 15 6" />
                    </svg>
                    <span>Camera</span>
                  </button>
                  <span className="gallery-overlay__title">Your Memories</span>
                  <span className="gallery-overlay__count">{myMedia.length}</span>
                </div>

                {myMedia.length === 0 ? (
                  <div className="gallery-overlay__empty">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" opacity="0.3">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <p>No photos or videos yet.</p>
                    <p className="gallery-overlay__empty-hint">Your captures and uploads will appear here.</p>
                  </div>
                ) : (
                  <div className="gallery-overlay__grid">
                    {myMedia.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className="gallery-overlay__item"
                        onClick={() => setSelectedMedia(item)}
                        aria-label={`${item.media_type === 'VIDEO' ? 'Video' : 'Photo'} — ${item.original_filename}`}
                      >
                        {item.media_type === 'VIDEO' ? (
                          <>
                            <video
                              src={item.media_url || getMediaUrl(item.id)}
                              muted
                              preload="metadata"
                            />
                            <span className="gallery-overlay__play-icon">
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                                <polygon points="5 3 19 12 5 21 5 3" />
                              </svg>
                            </span>
                          </>
                        ) : (
                          <img
                            src={item.media_url || getMediaUrl(item.id)}
                            alt={item.original_filename}
                            loading="lazy"
                            decoding="async"
                          />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Fullscreen media viewer */}
          <AnimatePresence>
            {selectedMedia && (
              <motion.div
                className="media-viewer"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={() => setSelectedMedia(null)}
              >
                <button
                  type="button"
                  className="media-viewer__close"
                  onClick={() => setSelectedMedia(null)}
                  aria-label="Close viewer"
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
                {selectedMedia.media_type === 'VIDEO' ? (
                  <video
                    src={selectedMedia.media_url || getMediaUrl(selectedMedia.id)}
                    controls
                    autoPlay
                    playsInline
                    className="media-viewer__content"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <img
                    src={selectedMedia.media_url || getMediaUrl(selectedMedia.id)}
                    alt={selectedMedia.original_filename}
                    className="media-viewer__content"
                    onClick={(e) => e.stopPropagation()}
                  />
                )}
                <div className="media-viewer__info">
                  <span>{guestName}</span>
                  <span>{new Date(selectedMedia.created_at).toLocaleString()}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <SiteFooter hidden />
        </div>
      </FilmShell>
    </PageTransition>
  );
}

// ── Upload item sub-component ──
function UploadItem({ item, onRetry }: { item: UploadQueueItem; onRetry: (id: string) => void }) {
  return (
    <div className={`camera-upload-panel__item camera-upload-panel__item--${item.status}`}>
      <span className="camera-upload-panel__item-icon">
        {item.type === 'video' ? '🎬' : '📷'}
      </span>
      <span className="camera-upload-panel__item-name" title={item.name}>
        {item.name.length > 24 ? item.name.slice(0, 21) + '…' : item.name}
      </span>
      <span className="camera-upload-panel__item-status">
        {item.status === 'queued' && 'Waiting…'}
        {item.status === 'uploading' && <span className="camera-upload-panel__mini-spinner" />}
        {item.status === 'uploaded' && '✓'}
        {item.status === 'failed' && (
          <button
            type="button"
            className="camera-upload-panel__retry-btn"
            onClick={() => onRetry(item.id)}
            aria-label="Retry upload"
          >
            ↻
          </button>
        )}
      </span>
    </div>
  );
}
