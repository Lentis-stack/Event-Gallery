import { motion } from 'framer-motion';
import { eventConfig } from '../config/event';

interface EventBrandingProps {
  /** If true, shows the platform wordmark above the event name. */
  showPlatform?: boolean;
  /** Which heading level to use for the event name. */
  as?: 'h1' | 'h2';
  className?: string;
}

/**
 * Consistent event identity block used across pages.
 * Hierarchy: platform (subtle) -> EVENT NAME (hero) -> subtitle.
 */
export default function EventBranding({
  showPlatform = true,
  as = 'h1',
  className = '',
}: EventBrandingProps) {
  const MotionHeading = as === 'h1' ? motion.h1 : motion.h2;
  return (
    <div className={`event-branding ${className}`.trim()}>
      {showPlatform && (
        <motion.p
          className="event-branding__platform"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, ease: 'easeOut' }}
        >
          {eventConfig.platformName}
        </motion.p>
      )}
      <MotionHeading
        className="event-branding__name"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.2, ease: 'easeOut', delay: 0.15 }}
      >
        {eventConfig.name}
      </MotionHeading>
      <motion.p
        className="event-branding__subtitle"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.2, ease: 'easeOut', delay: 0.4 }}
      >
        {eventConfig.subtitle}
      </motion.p>
    </div>
  );
}
