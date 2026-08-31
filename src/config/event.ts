// ============================================================
// Lentis Gallery — Central Event Configuration
// ------------------------------------------------------------
// Every page pulls the event identity from this single source.
// Later this will be loaded from the backend per-event.
// ============================================================

export interface EventImage {
  src: string;
  alt: string;
}

export interface EventProvider {
  /** Path to the brand logo image (rendered in the footer). */
  logo?: string;
  /** Business or personal brand name shown in the footer. */
  name: string;
  /** Short call-to-action inviting guests to reach out. */
  message: string;
  /** Optional phone number (shown as a tel: link). */
  phone?: string;
  /** Optional email (shown as a mailto: link). */
  email?: string;
  /** Optional Instagram handle/URL (shown as an external link). */
  instagram?: string;
    /** Optional Twitter/X handle/URL (shown as an external link). */
  twitter?: string;
  /** Optional Facebook page/URL (shown as an external link). */
  facebook?: string;
  /** Optional GitHub profile/URL (shown as an external link). */
  github?: string;
  /** Optional LinkedIn profile/URL (shown as an external link). */
  linkedin?: string;
}

export interface EventConfig {
  /** Platform branding, always subtle and premium. */
  platformName: string;
  /** The event's formal name shown as the cinematic hero. */
  name: string;
  /** Short, emotional one-line description. */
  subtitle: string;
  /** Customizable welcome message shown on the Welcome page. */
  welcomeMessage?: string;
  /** Full-screen cinematic slideshow images. */

  images: EventImage[];
  /** Optional provider / contact info shown in the guest footer. */
  provider?: EventProvider;
  /** Assigned event host display name. */
  hostName: string;
  /** Host email for login. */
  hostEmail?: string;
  /** ISO date string for the event. */
  eventDate: string;
  /** Lifecycle status. */
  status: 'draft' | 'live' | 'ended';
  /** Brand accent theme. */
  theme: 'gold' | 'blue' | 'rose' | 'emerald';
  /** Public guest link. */
  guestLink: string;
}

export const eventConfig: EventConfig = {
  platformName: 'LENTIS GALLERY',
    name: 'TARAGOLD 2026',
  subtitle: 'A celebration of love, memories & moments.',
  welcomeMessage: 'Thank you for being part of our special day. Capture the moments that matter and share them with us.',
  hostName: 'Saheed',

  eventDate: '2026-08-15',
  status: 'live',
  theme: 'gold',
  guestLink: 'https://lentis.gallery/taragold-2026',
  // Provider contact details shown in the SiteFooter on every page.
  // Edit these values to update the footer across the whole app.
    provider: {
    logo: '/assets/event/LentisLogo.png',
    name: 'LENTIS TECH',
    message: 'Contact • Socials • Tech',
    phone: '+234 9115074050',
    email: 'saheed.ibraheem@yahoo.com',
    instagram: 'Lentis_Soft.Eng',
    twitter: 'Lentis_Soft.Eng',
    facebook: 'Lentis_Soft.Eng',
    github: 'saheedibraheem',
    linkedin: 'saheedibraheem',
  },

  images: [
    {
      src: '/assets/event/Slideshow1.jpg',
      alt: 'TARAGOLD 2026 celebration',
    },
    {
      src: '/assets/event/Slideshow2.jpg',
      alt: 'Guests celebrating at TARAGOLD 2026',
    },
    {
      src: '/assets/event/Slideshow3.jpg',
      alt: 'A beautiful moment from TARAGOLD 2026',
    },
    {
      src: '/assets/event/Slideshow4.jpg',
      alt: 'A memorable moment from TARAGOLD 2026',
    },
  ],
};

// ============================================================
// Motion system — single source of truth for timing & easing.
// ============================================================

export const SLIDE_DURATION = 6000; // ms each image stays visible
export const TRANSITION_DURATION = 1600; // ms crossfade / Ken Burns
