// ============================================================
// Lentis Gallery — Reusable Image Slideshow with Cinematic Crossfade
// ============================================================
// Handles 0, 1, 2, or multiple images.
// Uses Framer Motion for slow fade transitions + Ken Burns effect.
// Single image: static, no animation.
// Multiple images: crossfade with opacity transitions.
// Can be used standalone (auto-advance) or controlled (activeIndex prop).
// ============================================================

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface ImageSlideshowProps {
  images: Array<{ src: string; alt: string; id: string }>;
  /** Time each image stays visible (ms). Default 6000. */
  slideDuration?: number;
  /** Crossfade duration (ms). Default 2000. */
  transitionDuration?: number;
  /** CSS class for the outer container. Default 'slideshow'. */
  className?: string;
  /** Controlled: externally managed active index. When provided, auto-advance is disabled. */
  activeIndex?: number;
}

export default function ImageSlideshow({
  images,
  slideDuration = 6000,
  transitionDuration = 2000,
  className = 'slideshow',
  activeIndex: controlledIndex,
}: ImageSlideshowProps) {
  const [internalIndex, setInternalIndex] = useState(0);

  // Use controlled index if provided, otherwise use internal
  const activeIndex = controlledIndex !== undefined ? controlledIndex : internalIndex;

  // Preload all images on mount to prevent dark flashes during crossfade
  useEffect(() => {
    images.forEach((img) => {
      const preload = new Image();
      preload.src = img.src;
    });
  }, [images]);

  // Auto-advance (only when uncontrolled)
  useEffect(() => {
    if (controlledIndex !== undefined) return; // Don't auto-advance when controlled
    if (images.length <= 1) return;
    const id = window.setInterval(() => {
      setInternalIndex((prev) => (prev + 1) % images.length);
    }, slideDuration);
    return () => window.clearInterval(id);
  }, [images.length, slideDuration, controlledIndex]);

  if (images.length === 0) return null;

  // Single image: show static (no animation)
  if (images.length === 1) {
    const img = images[0];
    return (
      <div className={className} aria-hidden="true">
        <div className="slideshow__slide" style={{ opacity: 1 }}>
          <div className="slideshow__kenburns">
            <img src={img.src} alt={img.alt} />
          </div>
        </div>
      </div>
    );
  }

  // Multiple images: crossfade with Ken Burns
  return (
    <div className={className} aria-hidden="true">
      {images.map((image, index) => {
        const isActive = index === activeIndex;
        const isPast = index === (activeIndex - 1 + images.length) % images.length;

        // Only render active slide + previous slide (for crossfade)
        if (!isActive && !isPast) return null;

        return (
          <motion.div
            key={image.id}
            className="slideshow__slide"
            initial={{ opacity: 0 }}
            animate={{ opacity: isActive ? 1 : 0 }}
            transition={{
              duration: transitionDuration / 1000,
              ease: 'easeInOut',
            }}
          >
            <motion.div
              className="slideshow__kenburns"
              initial={{ scale: 1 }}
              animate={{ scale: isActive ? 1.06 : 1 }}
              transition={{
                duration: slideDuration / 1000,
                ease: 'linear',
              }}
            >
              <img src={image.src} alt={image.alt} />
            </motion.div>
          </motion.div>
        );
      })}
    </div>
  );
}
