import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface NavigationButtonsProps {
  onNavigate: (destination: 'host' | 'guest') => void;
  disabled?: boolean;
}

interface ChoiceButtonProps {
  label: string;
  description?: string;
  onClick: () => void;
  disabled?: boolean;
  children?: ReactNode;
}

function ChoiceButton({ label, description, onClick, disabled, children }: ChoiceButtonProps) {
  return (
    <motion.button
      type="button"
      className="choice-btn"
      onClick={onClick}
      disabled={disabled}
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 260, damping: 20 }}
      aria-label={label}
    >
      {children}
      <span className="choice-btn__label">{label}</span>
      {description && <span className="choice-btn__desc">{description}</span>}
    </motion.button>
  );
}

/**
 * The two primary navigation choices on the welcome page: HOST and GUEST.
 */
export default function NavigationButtons({ onNavigate, disabled }: NavigationButtonsProps) {
  return (
    <nav className="nav-buttons" aria-label="Primary navigation">
      <ChoiceButton
        label="Guest"
        description="Share your moments"
        onClick={() => onNavigate('guest')}
        disabled={disabled}
      >
        <span className="choice-btn__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.4">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c0-4 3.6-6 8-6s8 2 8 6" />
          </svg>
        </span>
      </ChoiceButton>

      <ChoiceButton
        label="Host"
        description="Manage the event"
        onClick={() => onNavigate('host')}
        disabled={disabled}
      >
        <span className="choice-btn__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.4">
            <rect x="5" y="11" width="14" height="9" rx="2" />
            <path d="M8 11V8a4 4 0 0 1 8 0v3" />
          </svg>
        </span>
      </ChoiceButton>
    </nav>
  );
}
