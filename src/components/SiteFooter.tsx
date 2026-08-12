// ============================================================
// Lentis Gallery — SiteFooter
// ------------------------------------------------------------
// THE canonical public/provider footer. Shown on guest-flow and
// host pages only — the AdminLayout architecture makes it
// impossible for admin pages to render this component.
//
// Premium, cinematic 4-column layout:
//   COLUMN 1  LENTIS GALLERY / provider brand + description
//   COLUMN 2  Explore            (Gallery, Memories, Guest, Event)
//   COLUMN 3  Information        (About, Contact, Privacy, Terms)
//   COLUMN 4  Stay Connected     (newsletter email + subscribe)
// Then a separated bottom bar with copyright + social icons.
//
// All provider data is read from the central event config
// (src/config/event.ts) — nothing is hardcoded here.
//
// NEWSLETTER NOTE:
//   The subscribe form is VISUALLY functional but FRONTEND-ONLY.
//   There is no backend newsletter service yet, so after
//   submitting we show a friendly confirmation but do NOT pretend
//   a real subscription was created. When a newsletter backend is
//   added, wire this form to it.
// ============================================================

import { eventConfig } from '../config/event';
import type { EventProvider } from '../config/event';



interface SiteFooterProps {
  /** Optional extra class for layout adjustments. */
  className?: string;
  /** When true, the footer is hidden (e.g. fullscreen slideshow). */
  hidden?: boolean;
}

// --- Inline brand-consistent social icons -------------------
function InstagramIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.2" cy="6.8" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M18.9 2H22l-6.8 7.8L23.3 22h-6.3l-4.9-6.4L6.4 22H3.2l7.3-8.4L1.5 2h6.5l4.4 5.9L18.9 2zm-1.1 18h1.7L7.1 3.9H5.3L17.8 20z" />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3z" />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22" />
    </svg>
  );
}

function LinkedinIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

/**
 * Premium, compact horizontal footer.
 * Styled as a wide rectangular glass panel at the bottom of the page.
 */
export default function SiteFooter({ className = '', hidden = false }: SiteFooterProps) {
  const provider: EventProvider | undefined = eventConfig.provider;

  if (hidden || !provider || !provider.name) return null;

  const year = new Date().getFullYear();

  // --- Social links mapping ------------------------------------
  const socials: { label: string; href: string; icon: React.ReactNode }[] = [];
  
  if (provider.github) {
    const handle = provider.github.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : `https://github.com/${handle}`;
    socials.push({ label: 'GitHub', href, icon: <GithubIcon /> });
  }
  if (provider.instagram) {
    const handle = provider.instagram.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : `https://instagram.com/${handle}`;
    socials.push({ label: 'Instagram', href, icon: <InstagramIcon /> });
  }
  if (provider.facebook) {
    const handle = provider.facebook.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : `https://facebook.com/${handle}`;
    socials.push({ label: 'Facebook', href, icon: <FacebookIcon /> });
  }
  if (provider.twitter) {
    const handle = provider.twitter.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : `https://x.com/${handle}`;
    socials.push({ label: 'Twitter', href, icon: <XIcon /> });
  }
  if (provider.linkedin) {
    const handle = provider.linkedin.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : `https://linkedin.com/in/${handle}`;
    socials.push({ label: 'LinkedIn', href, icon: <LinkedinIcon /> });
  }

  return (
    <footer className={`site-footer ${className}`.trim()}>
      <div className="site-footer__panel">
        <div className="site-footer__row">
          {/* LEFT: Brand & Tagline */}
          <div className="site-footer__section site-footer__section--brand">
            <h2 className="site-footer__brand-name">{provider.name}</h2>
            <p className="site-footer__brand-msg">{provider.message}</p>
            <p className="site-footer__copy">© {year} {provider.name}</p>
          </div>

          {/* MIDDLE: Contact */}
          <div className="site-footer__section site-footer__section--contact">
            {provider.email && (
              <a href={`mailto:${provider.email}`} className="site-footer__contact-link">
                {provider.email}
              </a>
            )}
            {provider.phone && (
              <a href={`tel:${provider.phone.split(',')[0].trim()}`} className="site-footer__contact-link">
                {provider.phone.split(',')[0].trim()}
              </a>
            )}
          </div>

          {/* RIGHT: Socials */}
          <div className="site-footer__section site-footer__section--socials">
            <div className="site-footer__social-grid">
              {socials.map((s) => (
                <a
                  key={s.label}
                  href={s.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="site-footer__social-btn"
                  aria-label={s.label}
                >
                  {s.icon}
                  <span className="site-footer__social-label">{s.label}</span>
                </a>
              ))}
            </div>
          </div>
        </div>

        {/* Supporting Tagline area */}
        <div className="site-footer__tagline">
          <span>preserving memories • RSVP & Upload</span>
        </div>
      </div>
    </footer>
  );
}

