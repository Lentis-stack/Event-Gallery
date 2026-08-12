import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { eventConfig, SLIDE_DURATION, TRANSITION_DURATION } from '../config/event';
import type { EventImage } from '../config/event';

interface CinematicSlideshowProps {
  images?: EventImage[];
}

/**
 * Full-screen cinematic slideshow with Ken Burns crossfade.
 * Each image gently scales 1 -> 1.06 while displayed, then crossfades
 * into the next image which continues its own slow drift.
 */
export default function CinematicSlideshow({ images = eventConfig.images }: CinematicSlideshowProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  // Advance the active slide on a fixed interval.
  useEffect(() => {
    if (images.length === 0) return;
    const id = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % images.length);
    }, SLIDE_DURATION);
    return () => window.clearInterval(id);
  }, [images.length]);

  if (images.length === 0) {
    return null;
  }

  return (
    <div className="slideshow" aria-hidden="true">
      {images.map((image, index) => {
        // The slide is "active" when it's the current one.
        const isActive = index === activeIndex;
        // The previous slide stays mounted during the crossfade,
        // so we render active and the one before it.
        const prevIndex = (activeIndex - 1 + images.length) % images.length;
        const isVisible = isActive || index === prevIndex;

        if (!isVisible) return null;

        return (
          <motion.div
            key={image.src}
            className="slideshow__slide"
            initial={{ opacity: 0 }}
            animate={{ opacity: isActive ? 1 : 0 }}
            transition={{ duration: TRANSITION_DURATION / 1000, ease: 'easeInOut' }}
          >
            <motion.div
              className="slideshow__kenburns"
              initial={{ scale: 1 }}
              animate={{ scale: isActive ? 1.06 : 1 }}
              transition={{ duration: SLIDE_DURATION / 1000, ease: 'linear' }}
            >
              <img src={image.src} alt={image.alt} />
            </motion.div>
          </motion.div>
        );
      })}
    </div>
  );
}
