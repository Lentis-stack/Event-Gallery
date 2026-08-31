// ============================================================
// Lentis Gallery - SiteFooter
// ------------------------------------------------------------
// THE canonical public/provider footer. Shown on guest-flow and
// host pages only.
//
// Compact rectangular full-width fixed-bottom layout:
//   LEFT    Logo image + provider brand name + message
//   CENTER  Contact details (email, phone)
//   RIGHT   Social icon buttons
//   BOTTOM  Tagline (left) + copyright (right)
// ============================================================

import { getActiveEventConfig } from '../services/eventBridge';
import type { EventProvider } from '../config/event';

interface SiteFooterProps {
  className?: string;
  hidden?: boolean;
}

// --- Inline brand-consistent social icons -------------------
function InstagramIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.2" cy="6.8" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
      <path d="M18.9 2H22l-6.8 7.8L23.3 22h-6.3l-4.9-6.4L6.4 22H3.2l7.3-8.4L1.5 2h6.5l4.4 5.9L18.9 2zm-1.1 18h1.7L7.1 3.9H5.3L17.8 20z" />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3z" />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22" />
    </svg>
  );
}

function LinkedinIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

/**
 * Compact, full-width fixed-bottom footer.
 * Logo + brand on the left, contact in the center, socials on the right,
 * tagline + copyright along the bottom strip.
 */
export default function SiteFooter({ className = '', hidden = false }: SiteFooterProps) {
  const eventConfig = getActiveEventConfig();
  const provider: EventProvider | undefined = eventConfig.provider;

  if (hidden || !provider || !provider.name) return null;

  const year = new Date().getFullYear();

  // --- Social links mapping ------------------------------------
  const socials: { label: string; href: string; icon: React.ReactNode }[] = [];

  if (provider.github) {
    const handle = provider.github.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : 'https://github.com/' + handle;
    socials.push({ label: 'GitHub', href, icon: <GithubIcon /> });
  }
  if (provider.instagram) {
    const handle = provider.instagram.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : 'https://instagram.com/' + handle;
    socials.push({ label: 'Instagram', href, icon: <InstagramIcon /> });
  }
  if (provider.facebook) {
    const handle = provider.facebook.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : 'https://facebook.com/' + handle;
    socials.push({ label: 'Facebook', href, icon: <FacebookIcon /> });
  }
  if (provider.twitter) {
    const handle = provider.twitter.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : 'https://x.com/' + handle;
    socials.push({ label: 'Twitter', href, icon: <XIcon /> });
  }
  if (provider.linkedin) {
    const handle = provider.linkedin.replace(/^@/, '');
    const href = handle.startsWith('http') ? handle : 'https://linkedin.com/in/' + handle;
    socials.push({ label: 'LinkedIn', href, icon: <LinkedinIcon /> });
  }

  return (
    <footer className={('site-footer ' + className).trim()}>
      <div className="site-footer__panel">

        {/* --- MAIN ROW: 3 columns --- */}
        <div className="site-footer__row">

          {/* LEFT: Logo + Brand name */}
          <div className="site-footer__col site-footer__col--brand">
            {provider.logo && (
              <img
                className="site-footer__logo"
                src={provider.logo}
                alt={provider.name + ' logo'}
                width="36"
                height="36"
                loading="lazy"
              />
            )}
            <h2 className="site-footer__brand-name">{provider.name}</h2>
          </div>

          {/* CENTER: Contacts */}
          <div className="site-footer__col site-footer__col--contact">
            <h3 className="site-footer__col-heading">Contacts</h3>
            {provider.email && (
              <a href={'mailto:' + provider.email} className="site-footer__contact-link">
                {provider.email}
              </a>
            )}
            {provider.phone && (
              <>
                <a href={'tel:' + provider.phone.split(',')[0].trim()} className="site-footer__contact-link">
                  Call: {provider.phone.split(',')[0].trim()}
                </a>
                <a
                  href={'https://wa.me/' + provider.phone.replace(/[^0-9]/g, '')}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="site-footer__contact-link"
                >
                  WhatsApp: {provider.phone.split(',')[0].trim()}
                </a>
              </>
            )}
          </div>

          {/* RIGHT: Socials */}
          <div className="site-footer__col site-footer__col--socials">
            <h3 className="site-footer__col-heading">Socials</h3>
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
                </a>
              ))}
            </div>
          </div>
        </div>

        {/* --- BOTTOM: tagline + copyright --- */}
        <div className="site-footer__bottom">
          <span className="site-footer__tagline">preserving memories &bull; RSVP &amp; Upload</span>
          <span className="site-footer__copy">&copy; {year} {provider.name}</span>
        </div>
      </div>
    </footer>
  );
}
