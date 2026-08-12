// ============================================================
// Lentis Gallery — Event Types
// ------------------------------------------------------------
// Shared types for events across the Host Console and Admin
// Console. The Event Host manages ONE assigned event; the
// Lentis Admin manages MULTIPLE events.
//
// FUTURE: These types will be defined by the Python backend
// API and fetched over HTTP. For Phase 1 they are used by
// frontend-only mock data services.
// ============================================================

/** Event lifecycle status. */
export type EventStatus = 'draft' | 'live' | 'ended';

/** Simple theme choices for an event (brand colour accent). */
export type ThemeChoice = 'gold' | 'blue' | 'rose' | 'emerald';

/** A single slideshow / hero image for an event. */
export interface EventSlide {
  src: string;
  alt: string;
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
  /** Name of the assigned host. */
  hostName: string;
  /** ISO date string for the event. */
  eventDate: string;
  /** Current lifecycle status. */
  status: EventStatus;
  /** Theme / brand colour choice. */
  theme: ThemeChoice;
  /** Slideshow images used on the welcome page & live slideshow. */
  slides: EventSlide[];
  /** Total guest uploads (mock figure). */
  totalUploads: number;
  /** Photos count (mock). */
  photoCount: number;
  /** Videos count (mock). */
  videoCount: number;
  /** Guests who contributed (mock). */
  contributingGuests: number;
  /** Storage used in MB (mock/estimate). */
  storageUsedMb: number;
  /** Public guest link. */
  guestLink: string;
  /** Whether the event is archived (admin only). */
  archived: boolean;
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
