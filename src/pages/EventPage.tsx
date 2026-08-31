// ============================================================
// Lentis Gallery — Public Event Page (/e/:slug)
// ============================================================
// Phase 13.7: Professional loading screen, first image preloading,
// host access button, custom landing message.
// Phase 13.8: Gallery removed from public landing page.

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import FilmShell from '../components/FilmShell';
import ImageSlideshow from '../components/ImageSlideshow';
import SiteFooter from '../components/SiteFooter';
import PageTransition from '../components/PageTransition';
import {
  getPublicEvent,
  getPublicEventMedia,
  type PublicEvent,
  type PublicMediaResponse,
} from '../services/api';
import { eventConfig } from '../config/event';

type LoadingState = 'loading' | 'preloading' | 'found' | 'not_found' | 'error';

export default function EventPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');
  const [event, setEvent] = useState<PublicEvent | null>(null);
  const [media, setMedia] = useState<PublicMediaResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!slug) { setLoadingState('not_found'); return; }
    let cancelled = false;
    async function load() {
      setLoadingState('loading');
      try {
        const [ev, md] = await Promise.all([getPublicEvent(slug!), getPublicEventMedia(slug!)]);
        if (cancelled) return;
        setEvent(ev);
        setMedia(md);
        setLoadingState('preloading');
      } catch (err: any) {
        if (cancelled) return;
        if (err.message?.includes('404') || err.message?.includes('not found')) {
          setLoadingState('not_found');
        } else {
          setErrorMessage(err.message || 'Failed to load event.');
          setLoadingState('error');
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [slug]);

  useEffect(() => {
    if (loadingState !== 'preloading' || !media) return;
    const backgroundImages = [...(media.hero || []), ...(media.slideshow || [])];
    if (backgroundImages.length === 0) {
      setLoadingState('found');
      return;
    }
    let cancelled = false;
    const firstImg = new Image();
    firstImg.onload = () => {
      if (!cancelled) setLoadingState('found');
    };
    firstImg.onerror = () => {
      if (!cancelled) setLoadingState('found');
    };
    firstImg.src = backgroundImages[0].src;
    return () => { cancelled = true; };
  }, [loadingState, media]);

  if (loadingState === 'loading' || loadingState === 'preloading') {
    return (
      <PageTransition>
        <div className="event-loading">
          <div className="event-loading__content">
            <motion.img
              src="/assets/event/LentisLogo.png"
              alt="Lentis Gallery"
              className="event-loading__logo"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
            <motion.p
              className="event-loading__text"
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              Loading your event…
            </motion.p>
          </div>
        </div>
      </PageTransition>
    );
  }

  if (loadingState === 'not_found') {
    return (
      <PageTransition>
        <FilmShell>
          <div className="welcome">
            <div className="page-center">
              <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1.2 }} style={{ textAlign: 'center' }}>
                <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1.5rem, 4vw, 2.5rem)', color: 'var(--color-gold, #c8a96a)', marginBottom: '1rem', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
                  Event Not Found
                </h1>
                <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.95rem', maxWidth: '400px', margin: '0 auto', lineHeight: 1.6 }}>
                  The event you're looking for doesn't exist or has been removed.
                </p>
              </motion.div>
            </div>
          </div>
        </FilmShell>
      </PageTransition>
    );
  }

  if (loadingState === 'error') {
    return (
      <PageTransition>
        <FilmShell>
          <div className="welcome">
            <div className="page-center">
              <h1 style={{ fontFamily: 'var(--font-display)', color: 'var(--color-gold, #c8a96a)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Unable to Load Event
              </h1>
              <p style={{ color: '#c98a8a' }}>{errorMessage}</p>
            </div>
          </div>
        </FilmShell>
      </PageTransition>
    );
  }

  if (!event || !media) return null;

  const backgroundImages = [...(media.hero || []), ...(media.slideshow || [])];

  return (
    <PageTransition>
      <FilmShell>
        <div className="welcome">
          <ImageSlideshow images={backgroundImages} />
          <div className="welcome__overlay" aria-hidden="true" />

          <header className="welcome__top">
            <span className="welcome__eyebrow">
              {event.event_type || 'Event'}{event.location ? ` · ${event.location}` : ''}
            </span>
            <Link to={`/e/${slug}/host`} className="welcome__host-btn" aria-label="Host access">
              HOST
            </Link>
          </header>

          <div className="welcome__center">
            <div className="event-branding">
              <motion.p className="event-branding__platform" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1 }}>
                {eventConfig.platformName}
              </motion.p>
              <motion.h1 className="event-branding__name" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1.2, delay: 0.15 }}>
                {event.name}
              </motion.h1>
              <motion.p className="event-branding__subtitle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.2, delay: 0.4 }}>
                {event.subtitle || ''}
              </motion.p>
            </div>
          </div>

          <div className="welcome__bottom">
            <motion.p className="welcome__hint" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
              {event.description || eventConfig.welcomeMessage || 'Welcome to this special event.'}
            </motion.p>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }} style={{ marginTop: '1.5rem' }}>
              <button className="btn-primary" onClick={() => {
                if (event?.access_mode === 'PRIVATE') {
                  navigate(`/e/${slug}/guest-login`);
                } else {
                  navigate(`/e/${slug}/guest`);
                }
              }}>
                {event?.access_mode === 'PRIVATE' ? 'Enter Event' : 'Share Your Memories'}
              </button>
            </motion.div>
          </div>

          {event.landing_message && (
            <div className="welcome__landing-message-wrap">
              <motion.div
                className="welcome__landing-message"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.0 }}
              >
                <p>{event.landing_message}</p>
              </motion.div>
            </div>
          )}

          <SiteFooter />
        </div>
      </FilmShell>
    </PageTransition>
  );
}
