// ============================================================
// Lentis Gallery — Admin Login Page
// ============================================================
// Login for the Lentis Admin Console. Uses real backend
// authentication (JWT via POST /api/auth/login).
//
// SECURITY:
//   - Calls the real backend /api/auth/login endpoint.
//   - Access token stored in memory (not localStorage).
//   - Refresh token stored in HttpOnly cookie by the backend.
//   - On success, redirects to /admin/console.
//   - On failure, shows the error from the backend.
// ============================================================

import { useState } from "react";
import type { FormEvent } from "react";
import { motion } from "framer-motion";
import { useNavigate, Link } from "react-router-dom";
import FilmShell from "../../components/FilmShell";
import PageTransition from "../../components/PageTransition";
import { login } from "../../services/auth";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  /**
   * Handle form submission: call the real backend login API.
   * If successful, the auth service stores the JWT token
   * and we redirect to the admin console.
   */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setSubmitting(true);

    try {
      // Call the real backend authentication endpoint.
      const user = await login(email, password);

      // Verify the user has ADMIN role (defense in depth).
      if (user.role !== "ADMIN") {
        setError("This account does not have admin access.");
        setSubmitting(false);
        return;
      }

      // Success — navigate to the admin console.
      navigate("/admin/console");
    } catch (err: any) {
      // Show the error message from the backend.
      setError(err.message || "Login failed. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <PageTransition>
      <FilmShell>
        <div className="admin-login">
          {/* Subtle Lentis logo background watermark */}
          <div className="admin-console__bg">
            <img src="/assets/event/LentisLogo.png" alt="" className="admin-console__bg-logo" />
          </div>

          <header className="page-top">
            <Link to="/" className="back-link" aria-label="Back to welcome">
              ← Back
            </Link>
          </header>

          <div className="page-center">
            <motion.img
              src="/assets/event/LentisLogo.png"
              alt="Lentis Gallery"
              style={{ width: 'clamp(100px, 25vw, 160px)', height: 'auto', objectFit: 'contain', marginBottom: '1.5rem' }}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />

            <motion.h2
              className="admin-login__title"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1.2, ease: "easeOut" }}
            >
              Lentis Admin
            </motion.h2>
            <motion.p
              className="admin-login__subtitle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1.2, ease: "easeOut", delay: 0.2 }}
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
              <label className="guest-form__label" htmlFor="admin-email">
                Email
              </label>
              <input
                id="admin-email"
                className="guest-form__input"
                type="email"
                name="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@lentis.gallery"
                autoComplete="email"
                disabled={submitting}
              />

              <label className="guest-form__label" htmlFor="admin-password">
                Password
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
                aria-describedby={error ? "admin-error" : undefined}
                aria-invalid={error ? true : undefined}
              />
              {error && (
                <p className="guest-form__error" id="admin-error" role="alert">
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
          </div>
        </div>
      </FilmShell>
    </PageTransition>
  );
}
