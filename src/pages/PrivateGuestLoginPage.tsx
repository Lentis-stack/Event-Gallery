// ============================================================
// Lentis Gallery — Private Guest Login Page
// ============================================================
// For PRIVATE events, guests must authenticate with name + password
// before accessing the camera. This page handles that flow.
// ============================================================

import { useState, useEffect } from 'react';
import { useNavigate, Link, useParams } from 'react-router-dom';
import FilmShell from '../components/FilmShell';
import ImageSlideshow from '../components/ImageSlideshow';
import EventBranding from '../components/EventBranding';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';
import { getPublicEventMedia, privateGuestLogin } from '../services/api';
import type { PublicMediaResponse } from '../services/api';

export default function PrivateGuestLoginPage() {
  const navigate = useNavigate();
  const { slug } = useParams<{ slug: string }>();
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [guestMedia, setGuestMedia] = useState<PublicMediaResponse | null>(null);

  // Session persistence: if guest already has a session, skip to camera
  useEffect(() => {
    const existingName = sessionStorage.getItem('guestName');
    const existingToken = sessionStorage.getItem('guestToken');
    if (existingName && existingToken && slug) {
      navigate(`/e/${slug}/camera`, { replace: true });
    }
  }, [slug, navigate]);

  useEffect(() => {
    if (!slug) return;
    getPublicEventMedia(slug).then(setGuestMedia).catch(() => {});
  }, [slug]);

  const guestSlides = guestMedia?.guest_slideshow || [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!slug || !name.trim() || !password) return;

    setSubmitting(true);
    setError('');

    try {
      const result = await privateGuestLogin(slug, name.trim(), password);

      // Store session
      sessionStorage.setItem('guestName', name.trim());
      sessionStorage.setItem('guestToken', result.session_token);

      navigate(`/e/${slug}/camera`, { replace: true });
    } catch (err: any) {
      setError(err.message || 'Invalid name or password.');
      setSubmitting(false);
    }
  };

  return (
    <PageTransition>
      <FilmShell>
        <div className="guest-page" style={{ position: 'relative', minHeight: '100vh', overflow: 'hidden' }}>
          {/* Guest slideshow background */}
          {guestSlides.length > 0 && (
            <div style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
              <ImageSlideshow images={guestSlides} />
            </div>
          )}

          <div style={{ position: 'absolute', inset: 0, zIndex: 1, background: 'linear-gradient(180deg, rgba(0,0,0,0.4) 0%, rgba(0,0,0,0.65) 50%, rgba(0,0,0,0.5) 100%)', pointerEvents: 'none' }} />

          <header className="page-top" style={{ position: 'relative', zIndex: 2 }}>
            <Link to={slug ? `/e/${slug}` : '/'} className="back-link" aria-label="Back to event">
              ← Back
            </Link>
          </header>

          <div className="page-center" style={{ position: 'relative', zIndex: 2 }}>
            <EventBranding showPlatform={false} as="h2" className="page-center__branding" />

            <div className="page-center__intro">
              <p>Private Event</p>
              <p className="page-center__muted">Enter your name and event password to participate.</p>
            </div>

            <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: '340px' }}>
              <div className="admin-create__field" style={{ marginBottom: '1rem' }}>
                <label className="guest-form__label" htmlFor="guest-name">Guest Name</label>
                <input
                  id="guest-name"
                  className="guest-form__input"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  required
                  autoComplete="name"
                />
              </div>

              <div className="admin-create__field" style={{ marginBottom: '1rem' }}>
                <label className="guest-form__label" htmlFor="guest-password">Event Password</label>
                <input
                  id="guest-password"
                  className="guest-form__input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Event password"
                  required
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <p style={{ color: '#c98a8a', fontSize: '0.85rem', marginBottom: '0.75rem', textAlign: 'center' }}>
                  {error}
                </p>
              )}

              <button
                type="submit"
                className="btn-primary"
                disabled={submitting || !name.trim() || !password}
                style={{ width: '100%' }}
              >
                {submitting ? 'Signing in…' : 'Enter Event'}
              </button>
            </form>
          </div>

          <div style={{ position: 'relative', zIndex: 2 }}>
            <SiteFooter />
          </div>
        </div>
      </FilmShell>
    </PageTransition>
  );
}
