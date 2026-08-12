import { useState } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'framer-motion';

interface GuestNameFormProps {
  onSubmit: (name: string) => void;
  disabled?: boolean;
}

const MAX_NAME_LENGTH = 60;
const NAME_HAS_LETTER = /\p{L}/u;

/**
 * Minimal, elegant guest name entry with validation.
 * Empty / whitespace-only names are rejected; the value is trimmed.
 */
export default function GuestNameForm({ onSubmit, disabled }: GuestNameFormProps) {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);

const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim().replace(/\s+/g, ' ');

    if (!trimmed) {
      setError('Please enter your name to continue.');
      return;
    }

    if (trimmed.length > MAX_NAME_LENGTH || !NAME_HAS_LETTER.test(trimmed)) {
      setError('Please enter a valid name.');
      return;
    }

    setError(null);
    onSubmit(trimmed);
  };

  return (
    <motion.form
      className="guest-form"
      onSubmit={handleSubmit}
      noValidate
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.5 }}
    >
      <label className="guest-form__label" htmlFor="guest-name">
        What's your name?
      </label>
      <input
        id="guest-name"
        className="guest-form__input"
        type="text"
        name="guestName"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Enter your name"
        maxLength={MAX_NAME_LENGTH}
        autoComplete="name"
        disabled={disabled}
        aria-describedby={error ? 'guest-name-error' : undefined}
        aria-invalid={error ? true : undefined}
      />
      {error && (
        <p className="guest-form__error" id="guest-name-error" role="alert">
          {error}
        </p>
      )}
      <motion.button
        type="submit"
        className="btn-primary guest-form__submit"
        disabled={disabled}
        whileHover={{ y: -2 }}
        whileTap={{ scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 260, damping: 20 }}
      >
        Continue
      </motion.button>
    </motion.form>
  );
}
