// ============================================================
// Lentis Gallery — Host Live Slideshow Page
// ------------------------------------------------------------
// Full-screen live slideshow for the event, using the event's
// slideshow images. Includes:
//   - Manual prev / next controls
//   - Autoplay toggle
//   - Fullscreen toggle
//   - Slide counter
//
// Uses the cinematic Ken Burns slideshow component for the
// visual language.
// ============================================================

import { useCallback, useEffect, useState } from 'react';
import HostLayout from '../../components/host/HostLayout';
import { getAssignedEvent } from '../../services/mockHostService';
import { SLIDE_DURATION } from '../../config/event';

export default function HostSlideshowPage() {
  const [event] = useState(() => getAssignedEvent());
  const slides = event.slides;

  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const total = slides.length;

  const goNext = useCallback(() => {
    setIndex((i) => (i + 1) % total);
  }, [total]);

  const goPrev = useCallback(() => {
    setIndex((i) => (i - 1 + total) % total);
  }, [total]);

  // Autoplay
  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(goNext, SLIDE_DURATION);
    return () => window.clearTimeout(timer);
  }, [playing, index, goNext]);

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  // Keyboard controls
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goNext();
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === ' ') {
        e.preventDefault();
        setPlaying((p) => !p);
      }
      if (e.key === 'f' || e.key === 'F') toggleFullscreen();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goNext, goPrev]);

  const current = slides[index];

  return (
    // hideFooter keeps the footer off-screen while Fullscreen is active so it
    // does not distract from the live event display.
    <HostLayout event={event} hideFooter={isFullscreen}>
      <div className="host-slideshow">
        <header className="host-slideshow__header">
          <div>
            <p className="host-slideshow__eyebrow">Live Slideshow</p>
            <h1 className="host-slideshow__title">{event.name}</h1>
          </div>
          <div className="host-slideshow__counter" aria-live="polite">
            {index + 1} / {total}
          </div>
        </header>

        <div className="host-slideshow__stage">
          <div className="host-slideshow__slide">
            {current && (
              <img src={current.src} alt={current.alt} />
            )}
          </div>

          <div className="host-slideshow__controls">
            <button
              type="button"
              className="host-slideshow__btn"
              onClick={goPrev}
              aria-label="Previous slide"
            >
              ← Prev
            </button>

            <button
              type="button"
              className="host-slideshow__btn"
              onClick={() => setPlaying((p) => !p)}
              aria-pressed={playing}
            >
              {playing ? 'Pause' : 'Play'}
            </button>

            <button
              type="button"
              className="host-slideshow__btn"
              onClick={goNext}
              aria-label="Next slide"
            >
              Next →
            </button>

            <button
              type="button"
              className="host-slideshow__btn"
              onClick={toggleFullscreen}
              aria-pressed={isFullscreen}
            >
              {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            </button>
          </div>

          <p className="host-slideshow__hint">
            Use ← → to navigate, Space to play/pause, F for fullscreen.
          </p>
        </div>
      </div>
    </HostLayout>
  );
}
