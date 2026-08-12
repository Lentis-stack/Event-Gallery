import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import FilmShell from '../components/FilmShell';
import EventBranding from '../components/EventBranding';
import GuestNameForm from '../components/GuestNameForm';
import PageTransition from '../components/PageTransition';
import SiteFooter from '../components/SiteFooter';

/**
 * Guest entry page — continuation of the welcome experience.
 * Guest enters their name, which is stored in sessionStorage (Phase 1).
 */
export default function GuestPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = (name: string) => {
    setSubmitting(true);
    // Phase 1: temporary client-side storage. Real session/auth comes later.
    sessionStorage.setItem('guestName', name);
    navigate('/guest/camera');
  };

  return (
    <PageTransition>
      <FilmShell>
        <div className="guest-page">
          <header className="page-top">
            <Link to="/" className="back-link" aria-label="Back to welcome">
              ← Back
            </Link>
          </header>

          <div className="page-center">
            <EventBranding showPlatform={false} as="h2" className="page-center__branding" />
            <div className="page-center__intro">
              <p>Welcome to the celebration</p>
              <p className="page-center__muted">We'd love to know who's sharing these memories.</p>
            </div>
            <GuestNameForm onSubmit={handleSubmit} disabled={submitting} />
          </div>
          <SiteFooter />
        </div>
      </FilmShell>
    </PageTransition>
  );
}
