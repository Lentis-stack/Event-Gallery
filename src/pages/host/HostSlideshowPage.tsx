// ============================================================
// Lentis Gallery — Host Live Media Player
// ------------------------------------------------------------
// Cinematic auto-advancing media player for the Host Console's
// Live page. Displays approved guest photos and videos.
//
// Player logic:
//   IMAGE  → display for IMAGE_DURATION → fade → next
//   VIDEO  → autoplay muted → onEnded → fade → next
//
// Only uses approved + visible guest media from the public
// gallery endpoint.
// ============================================================

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import HostLayout from '../../components/host/HostLayout';
import { getAssignedEvent } from '../../services/mockHostService';
import { getPublicGallery } from '../../services/api';
import type { Event } from '../../types/event';

// ── Types ──────────────────────────────────────────────────

interface LiveMedia {
  id: string;
  src: string;       // thumbnail / fallback
  full_src: string;  // full-size optimized URL
  alt: string;
  media_type: string; // 'PHOTO' | 'VIDEO'
}

type PlaybackState = 'idle' | 'playing' | 'paused';

// ── Constants ──────────────────────────────────────────────

const IMAGE_DURATION = 7000;  // ms each image stays visible
const FADE_DURATION = 1.2;    // seconds for crossfade
const VIDEO_END_DELAY = 600;  // ms pause after video ends before next

const EMPTY_EVENT: Event = {
  id: '', slug: '', name: 'Loading...', subtitle: '',
  hostName: '', hostEmail: '', eventDate: '', status: 'draft',
  theme: 'gold', slides: [], totalUploads: 0, photoCount: 0,
  videoCount: 0, contributingGuests: 0, storageUsedMb: 0,
  guestLink: '', archived: false,
};

// ── Component ──────────────────────────────────────────────

export default function HostSlideshowPage() {
  const [event, setEvent] = useState<Event>(EMPTY_EVENT);
  const [media, setMedia] = useState<LiveMedia[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playbackState, setPlaybackState] = useState<PlaybackState>('playing');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const imageTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const videoEndTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);

  const total = media.length;
  const currentMedia = total > 0 ? media[currentIndex] : null;
  const isVideo = currentMedia?.media_type === 'VIDEO';

  // ── Load data ──────────────────────────────────────────

  useEffect(() => {
    mountedRef.current = true;
    getAssignedEvent().then((ev) => {
      if (!mountedRef.current) return;
      setEvent(ev);
      if (ev.slug) {
        setIsLoading(true);
        getPublicGallery(ev.slug, null, 200)
          .then((res) => {
            if (!mountedRef.current) return;
            const items: LiveMedia[] = res.items.map((m) => ({
              id: m.id,
              src: m.src,
              full_src: m.full_src || m.src,
              alt: m.alt || 'Guest memory',
              media_type: m.media_type || 'PHOTO',
            }));
            setMedia(items);
            setCurrentIndex(0);
            setIsLoading(false);
            setHasError(false);
          })
          .catch(() => {
            if (!mountedRef.current) return;
            setMedia([]);
            setIsLoading(false);
            setHasError(true);
          });
      }
    });
    return () => { mountedRef.current = false; };
  }, []);

  // ── Navigation ─────────────────────────────────────────

  const goNext = useCallback(() => {
    if (total === 0) return;
    setCurrentIndex((i) => (i + 1) % total);
  }, [total]);

  const goPrev = useCallback(() => {
    if (total === 0) return;
    setCurrentIndex((i) => (i - 1 + total) % total);
  }, [total]);

  // ── Image auto-advance timer ───────────────────────────

  const clearTimers = useCallback(() => {
    if (imageTimerRef.current) {
      clearTimeout(imageTimerRef.current);
      imageTimerRef.current = undefined;
    }
    if (videoEndTimerRef.current) {
      clearTimeout(videoEndTimerRef.current);
      videoEndTimerRef.current = undefined;
    }
  }, []);

  useEffect(() => {
    clearTimers();

    if (playbackState !== 'playing' || total === 0) return;
    if (!currentMedia) return;

    if (currentMedia.media_type !== 'VIDEO') {
      // Image: set a timer to advance
      imageTimerRef.current = setTimeout(goNext, IMAGE_DURATION);
    }
    // Video: advancement is handled by onEnded

    return () => clearTimers();
  }, [currentIndex, playbackState, currentMedia, total, goNext, clearTimers]);

  // ── Video control ──────────────────────────────────────

  useEffect(() => {
    const vid = videoRef.current;
    if (!vid) return;

    if (playbackState === 'playing' && isVideo) {
      vid.play().catch(() => {
        // Autoplay blocked — stay on current frame, user can press play
      });
    } else if (playbackState === 'paused') {
      vid.pause();
    }
  }, [playbackState, isVideo, currentIndex]);

  // ── Video onEnded handler ──────────────────────────────

  const handleVideoEnded = useCallback(() => {
    if (!mountedRef.current) return;
    videoEndTimerRef.current = setTimeout(() => {
      if (mountedRef.current) goNext();
    }, VIDEO_END_DELAY);
  }, [goNext]);

  // ── Video error handler ────────────────────────────────

  const handleVideoError = useCallback(() => {
    if (!mountedRef.current) return;
    // Don't freeze — skip to next after a short delay
    videoEndTimerRef.current = setTimeout(() => {
      if (mountedRef.current) goNext();
    }, 1500);
  }, [goNext]);

  // ── Image load error handler ───────────────────────────

  const handleImageError = useCallback(() => {
    // Don't freeze — skip to next
    if (playbackState === 'playing') {
      imageTimerRef.current = setTimeout(goNext, 2000);
    }
  }, [playbackState, goNext]);

  // ── Keyboard controls ──────────────────────────────────

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goNext();
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === ' ') {
        e.preventDefault();
        setPlaybackState((s) => s === 'playing' ? 'paused' : 'playing');
      }
      if (e.key === 'f' || e.key === 'F') toggleFullscreen();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goNext, goPrev]);

  // ── Fullscreen ─────────────────────────────────────────

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  }, []);

  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  // ── Controls ───────────────────────────────────────────

  const handlePrev = useCallback(() => {
    if (isVideo && videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
    clearTimers();
    goPrev();
  }, [isVideo, goPrev, clearTimers]);

  const handleNext = useCallback(() => {
    if (isVideo && videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
    clearTimers();
    goNext();
  }, [isVideo, goNext, clearTimers]);

  const togglePlayPause = useCallback(() => {
    setPlaybackState((s) => s === 'playing' ? 'paused' : 'playing');
  }, []);

  // ── Render ─────────────────────────────────────────────

  return (
    <HostLayout event={event} hideFooter={isFullscreen}>
      <div className="live-player">
        {/* Header */}
        <header className="live-player__header">
          <div>
            <p className="live-player__eyebrow">Live Memories</p>
            <h1 className="live-player__title">{event.name}</h1>
          </div>
          {total > 0 && (
            <div className="live-player__counter" aria-live="polite">
              {currentIndex + 1} / {total}
            </div>
          )}
        </header>

        {/* Media Frame */}
        <div className="live-player__frame-wrapper">
          <div className="live-player__frame">
            {/* Loading state */}
            {isLoading && (
              <div className="live-player__state">
                <div className="live-player__spinner" />
                <p>Loading guest memories…</p>
              </div>
            )}

            {/* Empty state */}
            {!isLoading && total === 0 && !hasError && (
              <div className="live-player__state">
                <p className="live-player__state-icon">📸</p>
                <p className="live-player__state-title">No approved guest memories yet</p>
                <p className="live-player__state-sub">
                  Guest uploads will appear here automatically<br />once approved.
                </p>
              </div>
            )}

            {/* Error state */}
            {!isLoading && hasError && (
              <div className="live-player__state">
                <p className="live-player__state-icon">⚠️</p>
                <p className="live-player__state-title">Unable to load media</p>
                <button
                  type="button"
                  className="live-player__btn"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </button>
              </div>
            )}

            {/* Active media */}
            {!isLoading && currentMedia && (
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentMedia.id}
                  className="live-player__media-container"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: FADE_DURATION, ease: 'easeInOut' }}
                >
                  {isVideo ? (
                    <video
                      ref={videoRef}
                      src={currentMedia.full_src}
                      className="live-player__media"
                      autoPlay
                      muted
                      playsInline
                      onEnded={handleVideoEnded}
                      onError={handleVideoError}
                      preload="auto"
                    />
                  ) : (
                    <img
                      src={currentMedia.full_src}
                      alt={currentMedia.alt}
                      className="live-player__media"
                      onError={handleImageError}
                      draggable={false}
                    />
                  )}
                </motion.div>
              </AnimatePresence>
            )}
          </div>

          {/* Playback progress bar for videos */}
          {isVideo && videoRef.current && playbackState === 'playing' && (
            <VideoProgressBar videoRef={videoRef} />
          )}
        </div>

        {/* Controls */}
        {total > 0 && (
          <div className="live-player__controls">
            <button
              type="button"
              className="live-player__btn"
              onClick={handlePrev}
              aria-label="Previous slide"
            >
              ← Prev
            </button>
            <button
              type="button"
              className="live-player__btn"
              onClick={togglePlayPause}
              aria-pressed={playbackState === 'playing'}
            >
              {playbackState === 'playing' ? '⏸ Pause' : '▶ Play'}
            </button>
            <button
              type="button"
              className="live-player__btn"
              onClick={handleNext}
              aria-label="Next slide"
            >
              Next →
            </button>
            <button
              type="button"
              className="live-player__btn"
              onClick={toggleFullscreen}
              aria-pressed={isFullscreen}
            >
              {isFullscreen ? '.Exit Fullscreen' : '⛶ Fullscreen'}
            </button>
          </div>
        )}

        <p className="live-player__hint">
          ← → navigate · Space play/pause · F fullscreen
        </p>
      </div>
    </HostLayout>
  );
}

// ── Video Progress Bar ──────────────────────────────────────

function VideoProgressBar({ videoRef }: { videoRef: React.RefObject<HTMLVideoElement | null> }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const vid = videoRef.current;
    if (!vid) return;

    let raf: number;
    const update = () => {
      if (vid.duration && vid.duration > 0) {
        setProgress((vid.currentTime / vid.duration) * 100);
      }
      raf = requestAnimationFrame(update);
    };
    raf = requestAnimationFrame(update);
    return () => cancelAnimationFrame(raf);
  }, [videoRef]);

  return (
    <div className="live-player__progress">
      <div
        className="live-player__progress-bar"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
