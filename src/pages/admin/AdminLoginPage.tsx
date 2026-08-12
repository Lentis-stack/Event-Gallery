// ============================================================
// Lentis Gallery — Admin Login Page
// ------------------------------------------------------------
// Login for the Lentis Admin Console. Uses a temporary
// frontend-only mock credential (separate from host demo).
//
// SECURITY NOTE: This is NOT secure authentication. Real admin
// auth will be handled by the backend in a later phase.
// ============================================================

import { useState } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, Link } from 'react-router-dom';
import FilmShell from '../../components/FilmShell';
import PageTransition from '../../components/PageTransition';
import { demoAccess } from '../../config/demoAccess';

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!password) {
      setError('Please enter the admin password.');
      return;
    }

    setSubmitting(true);

// --- TEMPORARY MOCK AUTH (Phase 1) -------------------------
    if (password === demoAccess.adminPassword) {
      sessionStorage.setItem('adminAuthed', 'true');
      navigate('/admin/console');
    } else {
      setSubmitting(false);
      setError('Incorrect admin password. Please try again.');
    }
    // ------------------------------------------------------------
  };

  return (
    <PageTransition>
      <FilmShell>
        <div className="admin-login">
          <header className="page-top">
            <Link to="/" className="back-link" aria-label="Back to welcome">
              ← Back
            </Link>
          </header>

          <div className="page-center">
            <div className="admin-login__mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="1.2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>

            <motion.h2
              className="admin-login__title"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
            >
              Lentis Admin
            </motion.h2>
            <motion.p
              className="admin-login__subtitle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
            >
              Platform management console
            </motion.p>

            <motion.form
              className="guest-form"
              onSubmit={handleSubmit}
              noValidate
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
            >
              <label className="guest-form__label" htmlFor="admin-password">
                Admin password
              </label>
              <input
                id="admin-password"
                className="guest-form__input"
                type="password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="current-password"
                disabled={submitting}
                aria-describedby={error ? 'admin-password-error' : undefined}
                aria-invalid={error ? true : undefined}
              />
              {error && (
                <p className="guest-form__error" id="admin-password-error" role="alert">
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

<p className="admin-login__note">
              Temporary demo. Production authentication arrives with the backend.
</p>
          </div>
        </div>
      </FilmShell>
    </PageTransition>
  );
}
