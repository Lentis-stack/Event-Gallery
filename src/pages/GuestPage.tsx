// ============================================================
// Lentis Gallery — Guest Page (/e/:slug/guest or /guest)
// ============================================================
// Guest name entry page. Registers with the backend to get a
// guest session token, then navigates to the camera/upload page.
// Shows guest slideshow images as background.
// ============================================================

import { useState, useEffect } from 'react';
import { useNavigate, Link, useParams } from 'react-router-dom';
import FilmShell from '../components/FilmShell';
import ImageSlideshow from '../components/ImageSlideshow';
import EventBranding from '../components/EventBranding';
import GuestNameForm from '../components/GuestNameForm';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';
import { getPublicEventMedia, getPublicEvent, type PublicMediaResponse } from '../services/api';

export default function GuestPage() {
  const navigate = useNavigate();
  const { slug } = useParams<{ slug: string }>();
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

  // Check if this is a PRIVATE event → redirect to private login
  useEffect(() => {
    if (!slug) return;
    getPublicEvent(slug)
      .then((event) => {
        if (event.access_mode === 'PRIVATE') {
          navigate(`/e/${slug}/guest-login`, { replace: true });
        }
      })
      .catch(() => {});
  }, [slug, navigate]);

  useEffect(() => {
    if (!slug) return;
    getPublicEventMedia(slug).then(setGuestMedia).catch(() => {});
  }, [slug]);

  const guestSlides = guestMedia?.guest_slideshow || [];

  const handleSubmit = async (name: string) => {
    if (!slug) {
      setError('Event not found. Please use the event link.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const res = await fetch(`/api/events/${slug}/guests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to register. Please try again.');
      }

      const data = await res.json();
      const token = data.session?.session_token;

      if (!token) {
        throw new Error('Invalid response from server. Please try again.');
      }

      sessionStorage.setItem('guestName', name.trim());
      sessionStorage.setItem('guestToken', token);

      navigate(`/e/${slug}/camera`, { replace: true });
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
      setSubmitting(false);
    }
  };

  return (
    <PageTransition>
      <FilmShell>
        <div className="guest-page" style={{ position: 'relative', minHeight: '100vh', overflow: 'hidden' }}>
          {/* Guest slideshow background with cinematic crossfade */}
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
              <p>Welcome to the celebration</p>
              <p className="page-center__muted">We'd love to know who's sharing these memories.</p>
            </div>
            <GuestNameForm onSubmit={handleSubmit} disabled={submitting} />
            {error && (
              <p style={{ color: '#c98a8a', fontSize: '0.85rem', marginTop: '0.75rem', textAlign: 'center' }}>
                {error}
              </p>
            )}
          </div>
          <div style={{ position: 'relative', zIndex: 2 }}>
            <SiteFooter />
          </div>
        </div>
      </FilmShell>
    </PageTransition>
  );
}
