// ============================================================
// Lentis Gallery — Event-Specific Host Login Page
// ============================================================
// Host login accessed from the event landing page via HOST ACCESS.
// Route: /e/:slug/host
// After login, redirects to host console managing that specific event.
// ============================================================

import { useState, useEffect } from "react";
import type { FormEvent } from "react";
import { motion } from "framer-motion";
import { useNavigate, useParams, Link } from "react-router-dom";
import FilmShell from "../components/FilmShell";
import PageTransition from "../components/PageTransition";
import SiteFooter from "../components/SiteFooter";
import ImageSlideshow from "../components/ImageSlideshow";
import { login } from "../services/auth";
import { getPublicEvent, getPublicHostSlideshow, type PublicEvent } from "../services/api";
import { setTargetEventSlug } from "../services/mockHostService";

export default function HostEventLoginPage() {
  const navigate = useNavigate();
  const { slug } = useParams<{ slug: string }>();
  const [event, setEvent] = useState<PublicEvent | null>(null);
  const [eventError, setEventError] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [hostSlides, setHostSlides] = useState<Array<{ src: string; alt: string; id: string }>>([]);

  // Load event info to display event name
  useEffect(() => {
    if (!slug) { setEventError(true); return; }
    getPublicEvent(slug)
      .then(setEvent)
      .catch(() => setEventError(true));
    getPublicHostSlideshow(slug)
      .then(setHostSlides)
      .catch(() => setHostSlides([]));
  }, [slug]);

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
      const user = await login(email.trim(), password);

      if (user.role !== "HOST" && user.role !== "ADMIN") {
        setError("This account does not have host access.");
        return;
      }

      // Set the target event slug so the host console loads the correct event
      if (slug) {
        setTargetEventSlug(slug);
      }

      // Navigate to host console with event context
      navigate("/host/console", {
        state: { eventSlug: slug },
        replace: true,
      });
    } catch (err: any) {
      setError(err.message || "Login failed. Please try again.");
      setSubmitting(false);
    }
  };

  if (eventError) {
    return (
      <PageTransition>
        <FilmShell>
          <div className="host-page">
            <header className="page-top">
              <Link to={slug ? "/e/" + slug : "/"} className="back-link" aria-label="Back to event">
                ← Back to Event
              </Link>
            </header>
            <div className="page-center">
              <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--color-gold, #c8a96a)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Event Not Found
              </h2>
              <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.9rem' }}>
                The event you're looking for doesn't exist.
              </p>
            </div>
          </div>
        </FilmShell>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <FilmShell>
        <div className="host-page">
          {/* Host slideshow background */}
          {hostSlides.length > 0 && (
            <div className="host-page__slideshow-bg" style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
              <ImageSlideshow images={hostSlides} />
            </div>
          )}

          <header className="page-top">
            <Link to={slug ? "/e/" + slug : "/"} className="back-link" aria-label="Back to event">
              ← Back to Event
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
              {event?.name || 'Event'} — private console
            </motion.p>

            <motion.form
              className="host-form"
              onSubmit={handleSubmit}
              noValidate
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
            >
              <label className="guest-form__label" htmlFor="host-event-email">
                Email
              </label>
              <input
                id="host-event-email"
                className="guest-form__input"
                type="email"
                name="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                autoComplete="email"
                disabled={submitting}
              />

              <label className="guest-form__label" htmlFor="host-event-password">
                Password
              </label>
              <input
                id="host-event-password"
                className="guest-form__input"
                type="password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="current-password"
                disabled={submitting}
                aria-describedby={error ? "host-event-error" : undefined}
                aria-invalid={error ? true : undefined}
              />
              {error && (
                <p className="guest-form__error" id="host-event-error" role="alert">
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

            <Link to="/admin" className="host-page__admin-link">
              Lentis Admin Console →
            </Link>
          </div>
          <SiteFooter />
        </div>
      </FilmShell>
    </PageTransition>
  );
}
