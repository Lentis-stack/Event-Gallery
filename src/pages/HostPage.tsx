import { useState } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, Link } from 'react-router-dom';
import FilmShell from '../components/FilmShell';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';
import { eventConfig } from '../config/event';
import { demoAccess } from '../config/demoAccess';

/**
 * Host login page — Phase 1 placeholder.
 *
 * SECURITY NOTE: This is a temporary frontend-only mock for the Phase 1
 * experience. It is NOT secure authentication. Real host authentication
 * will be handled by the backend in a later phase.
 */

export default function HostPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setSubmitting(true);

// --- TEMPORARY MOCK AUTH (Phase 1) -------------------------
    // Replace this whole block with real backend authentication later.
    if (password === demoAccess.hostPassword) {
      sessionStorage.setItem('hostAuthed', 'true');
      navigate('/host/console');
    } else {
      setSubmitting(false);
      setError('Incorrect password. Please try again.');
    }
    // ------------------------------------------------------------
  };

  return (
    <PageTransition>
      <FilmShell>
        <div className="host-page">
          <header className="page-top">
            <Link to="/" className="back-link" aria-label="Back to welcome">
              ← Back
            </Link>
          </header>

          <div className="page-center">
            <div className="host-page__lock" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="1.2">
                <rect x="5" y="11" width="14" height="9" rx="2" />
                <path d="M8 11V8a4 4 0 0 1 8 0v3" />
              </svg>
            </div>

            <motion.h2
              className="host-page__title"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
            >
              Host Access
            </motion.h2>
            <motion.p
              className="host-page__subtitle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
            >
              {eventConfig.name} — private console
            </motion.p>

            <motion.form
              className="host-form"
              onSubmit={handleSubmit}
              noValidate
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
            >
              <label className="guest-form__label" htmlFor="host-password">
                Enter your event password
              </label>
              <input
                id="host-password"
                className="guest-form__input"
                type="password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="current-password"
                disabled={submitting}
                aria-describedby={error ? 'host-password-error' : undefined}
                aria-invalid={error ? true : undefined}
              />
              {error && (
                <p className="guest-form__error" id="host-password-error" role="alert">
                  {error}
                </p>
              )}
              <motion.button
                type="submit"
                className="btn-primary guest-form__submit"
                disabled={submitting}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 260, damping: 20 }}
              >
                Sign In
              </motion.button>
            </motion.form>

            <p className="host-page__note">
              Temporary demo. Production authentication arrives with the backend.
            </p>

<Link to="/admin/login" className="host-page__admin-link">
              Lentis Admin Console →
            </Link>
          </div>
          <SiteFooter />
        </div>
      </FilmShell>
    </PageTransition>
  );
}
