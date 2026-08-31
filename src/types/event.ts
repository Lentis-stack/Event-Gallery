// ============================================================
// Lentis Gallery — Event Types
// ============================================================
// Shared types for events across the Host Console and Admin
// Console. The Event Host manages ONE assigned event; the
// Lentis Admin manages MULTIPLE events.
// ============================================================

/** Event lifecycle status. */
export type EventStatus = 'draft' | 'not_started' | 'live' | 'ended' | 'archived';

/** Simple theme choices for an event (brand colour accent). */
export type ThemeChoice = 'gold' | 'blue' | 'rose' | 'emerald';

/** Media role types for event visual media. */
export type MediaRole = 'HERO' | 'SLIDESHOW' | 'GALLERY' | 'HOST_SLIDESHOW';

/** Media page placement for slideshow media. */
export type MediaPage = 'LANDING' | 'GUEST' | 'HOST' | 'CAMERA';

/** A single slideshow / hero image for an event. */
export interface EventSlide {
  src: string;
  alt: string;
  id?: string;
  mediaRole?: MediaRole;
  page?: MediaPage;
  mediaId?: string;
}

/**
 * A Lentis Gallery event.
 */
export interface Event {
  id: string;
  /** Platform-wide unique slug, used in the guest link. */
  slug: string;
  /** Formal event name, e.g. "TARAGOLD 2026". */
  name: string;
  /** Short emotional one-line description. */
  subtitle: string;
  /** Event type (wedding, birthday, summit, etc.) */
  eventType?: string;
  /** Event location */
  location?: string;
  /** Full event description */
  description?: string;
  /** Custom landing page message below Share Your Memories */
  landingMessage?: string;
  /** Name of the assigned host. */
  hostName: string;
  /** Email of the assigned host (used for login). */
  hostEmail: string;
  /** Password for the host (stored in localStorage for admin management). */
  hostPassword?: string;
  /** ISO date string for the event. */
  eventDate: string;
  /** Optional time for the event (HH:MM format). */
  eventTime?: string;
  /** Current lifecycle status. */
  status: EventStatus;
  /** Theme / brand colour choice. */
  theme: ThemeChoice;
  /** Slideshow images used on the welcome page & live slideshow. */
  slides: EventSlide[];
  /** Slideshow images for the host console background. */
  hostSlides?: EventSlide[];
  /** Per-page slideshow overrides. Keys: "landing" | "guest" | "camera". */
  pageSlideshows?: Record<string, EventSlide[]>;
  /** Total guest uploads. */
  totalUploads: number;
  /** Photos count. */
  photoCount: number;
  /** Videos count. */
  videoCount: number;
  /** Guests who contributed. */
  contributingGuests: number;
  /** Storage used in MB. */
  storageUsedMb: number;
  /** Public guest link. */
  guestLink: string;
  /** Whether the event is archived (admin only). */
  archived: boolean;
  /** Event access mode: PUBLIC or PRIVATE. */
  accessMode?: 'PUBLIC' | 'PRIVATE';
  /** Hero image for the event landing page. */
  heroSlide?: EventSlide;
  /** Landing page slideshow images. */
  landingSlides?: EventSlide[];
  /** Guest page slideshow images. */
  guestSlides?: EventSlide[];
  /** Camera page slideshow images. */
  cameraSlides?: EventSlide[];
}

/** The static platform event (from config/event.ts) used for the guest flow. */
export interface StaticEventConfig {
  platformName: string;
  name: string;
  subtitle: string;
  images: EventSlide[];
  provider?: {
    name: string;
    message: string;
    phone?: string;
    email?: string;
    instagram?: string;
  };
}
