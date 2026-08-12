import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface PageTransitionProps {
  children: ReactNode;
}

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Cinematic page entrance/exit wrapper — "film scene" feel.
 *
 * ENTRANCE:
 *   - Outer layer fades in from a slightly darkened, scaled state.
 *   - Inner content rises gently with a soft blur->sharp for a
 *     premium "lens into focus" sensation.
 *
 * EXIT:
 *   - Inner content fades out and drifts up.
 *   - Outer layer dims + scales slightly, like pulling back from a
 *     scene.
 *
 * The light blur is removed as the element comes into focus,
 * which reads as a cinematic rack-focus. Reduced-motion users get
 * a plain opacity fade (handled by the global CSS media query).
 */
export default function PageTransition({ children }: PageTransitionProps) {
  return (
    <motion.div
      className="page-transition"
      initial={{ opacity: 0, scale: 1.02, filter: 'blur(6px)' }}
      animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, scale: 0.99, filter: 'blur(4px)' }}
      transition={{ duration: 1.2, ease: EASE }}
    >
      <motion.div
        className="page-transition__inner"
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -16 }}
        transition={{ duration: 1.1, ease: EASE, delay: 0.18 }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}
