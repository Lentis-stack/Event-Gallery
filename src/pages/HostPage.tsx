// ============================================================
// Lentis Gallery — Host Login Page
// ============================================================
// Login for the Event Host Console. Uses real backend
// authentication (JWT via POST /api/auth/login).
//
// SECURITY:
//   - Calls the real backend /api/auth/login endpoint.
//   - Access token stored in memory (not localStorage).
//   - Refresh token stored in HttpOnly cookie by the backend.
//   - On success, redirects to /host/console.
//   - On failure, shows the error from the backend.
// ============================================================

import { useState } from "react";
import type { FormEvent } from "react";
import { motion } from "framer-motion";
import { useNavigate, Link } from "react-router-dom";
import FilmShell from "../components/FilmShell";
import PageTransition from "../components/PageTransition";
import SiteFooter from "../components/SiteFooter";
import { getActiveEventConfig } from "../services/eventBridge";
import { login } from "../services/auth";

export default function HostPage() {
  const navigate = useNavigate();
  const eventConfig = getActiveEventConfig();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  /**
   * Handle form submission: call the real backend login API.
   * If successful, the auth service stores the JWT token
   * and we redirect to the host console.
   */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Please enter your email.");
      return;
    }
    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setSubmitting(true);

    try {
      // Call the real backend authentication endpoint.
      const user = await login(email.trim(), password);

      // Verify the user has HOST or ADMIN role.
      if (user.role !== "HOST" && user.role !== "ADMIN") {
        setError("This account does not have host access.");
        return;
      }

      // Success - navigate to the host console.
      navigate("/host/console");
    } catch (err: any) {
      setError(err.message || "Login failed. Please try again.");
      setSubmitting(false);
    }
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
              transition={{ duration: 1.2, ease: "easeOut" }}
            >
              Host Access
            </motion.h2>
            <motion.p
              className="host-page__subtitle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1.2, ease: "easeOut", delay: 0.2 }}
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
              <label className="guest-form__label" htmlFor="host-email">
                Email
              </label>
              <input
                id="host-email"
                className="guest-form__input"
                type="email"
                name="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                autoComplete="email"
                disabled={submitting}
              />

              <label className="guest-form__label" htmlFor="host-password">
                Password
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
                aria-describedby={error ? "host-error" : undefined}
                aria-invalid={error ? true : undefined}
              />
              {error && (
                <p className="guest-form__error" id="host-error" role="alert">
                  {error}
                </p>
              )}
              <motion.button
                type="submit"
                className="btn-primary guest-form__submit"
                disabled={submitting}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 260, damping: 20 }}
              >
                {submitting ? "Signing in..." : "Sign In"}
              </motion.button>
            </motion.form>

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
