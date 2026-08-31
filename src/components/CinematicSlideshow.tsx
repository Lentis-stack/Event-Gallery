import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getActiveEventConfig } from '../services/eventBridge';
import { SLIDE_DURATION, TRANSITION_DURATION } from '../config/event';
import type { EventImage } from '../config/event';

interface CinematicSlideshowProps {
  images?: EventImage[];
}

/**
 * Full-screen cinematic slideshow with Ken Burns crossfade.
 * Preloads ALL images on mount so transitions never flash dark.
 * Each image gently scales 1 -> 1.06 while displayed, then
 * crossfades into the next image which continues its own slow drift.
 */
const _defaultConfig = getActiveEventConfig();

export default function CinematicSlideshow({ images = _defaultConfig.images }: CinematicSlideshowProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  // --- Preload all images on mount ----------------------------
  // Without this, the first time a slide activates the browser
  // has to fetch the image, causing a dark flash during crossfade.
  useEffect(() => {
    images.forEach((img) => {
      const preload = new Image();
      preload.src = img.src;
    });
  }, [images]);

  // --- Advance slide on a fixed interval ----------------------
  useEffect(() => {
    if (images.length <= 1) return;
    const id = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % images.length);
    }, SLIDE_DURATION);
    return () => window.clearInterval(id);
  }, [images.length]);

  if (images.length === 0) {
    return null;
  }

  // If there's only one image, show it static (no transition).
  if (images.length === 1) {
    const img = images[0];
    return (
      <div className='slideshow' aria-hidden='true'>
        <div className='slideshow__slide' style={{ opacity: 1 }}>
          <div className='slideshow__kenburns'>
            <img src={img.src} alt={img.alt} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className='slideshow' aria-hidden='true'>
      {images.map((image, index) => {
        const isActive = index === activeIndex;
        const isPast = index === (activeIndex - 1 + images.length) % images.length;

        // Render active slide + the previous slide (for crossfade).
        // Once the previous slide has fully faded out, React unmounts it.
        if (!isActive && !isPast) return null;

        return (
          <motion.div
            key={image.src}
            className='slideshow__slide'
            // Start invisible; only the active slide animates to 1.
            initial={{ opacity: 0 }}
            animate={{ opacity: isActive ? 1 : 0 }}
            transition={{
              duration: TRANSITION_DURATION / 1000,
              ease: 'easeInOut',
            }}
          >
            <motion.div
              className='slideshow__kenburns'
              initial={{ scale: 1 }}
              animate={{ scale: isActive ? 1.06 : 1 }}
              transition={{
                duration: SLIDE_DURATION / 1000,
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
