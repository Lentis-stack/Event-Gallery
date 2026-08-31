// ============================================================
// Lentis Gallery — Active Event Bridge
// ============================================================
// Bridges backend events to the guest-facing config format.
// Guest pages call getActiveEventConfig() instead of importing
// the hardcoded eventConfig directly.
//
// For public events (by slug), fetches from the backend API.
// NEVER falls back to demo data for real events.
// ============================================================

import { eventConfig, type EventConfig } from '../config/event';
import { getPublicEvent, getPublicEventMedia } from './api';
import { getPublicBaseUrl } from './config';

// ============================================================
// Cached event config
// ============================================================

let _cachedConfig: EventConfig | null = null;
let _cachedSlug: string | null = null;

/**
 * Get the event config for a specific slug (async, fetches from API).
 * This is the primary method for public event pages.
 */
export async function getActiveEventConfigAsync(slug?: string): Promise<EventConfig> {
  if (slug && slug !== _cachedSlug) {
    try {
      const publicEvent = await getPublicEvent(slug);
      const mediaResult = await getPublicEventMedia(slug);

      _cachedConfig = {
        platformName: eventConfig.platformName,
        name: publicEvent.name,
        subtitle: publicEvent.subtitle || '',
        welcomeMessage: eventConfig.welcomeMessage,
        images: mediaResult.images.length > 0
          ? mediaResult.images.map(img => ({ src: img.src, alt: img.alt }))
          : eventConfig.images,
        provider: eventConfig.provider,
        hostName: eventConfig.hostName,
        hostEmail: eventConfig.hostEmail,
        eventDate: publicEvent.event_date,
        status: publicEvent.status === 'LIVE' ? 'live' : publicEvent.status === 'ENDED' ? 'ended' : 'draft',
        theme: publicEvent.theme,
        guestLink: `${getPublicBaseUrl()}/e/${publicEvent.slug}`,
      };
      _cachedSlug = slug;
      return _cachedConfig;
    } catch {
      // API failed — return empty config, NOT demo data
      return {
        platformName: eventConfig.platformName,
        name: 'Event Unavailable',
        subtitle: 'This event could not be loaded.',
        images: [],
        hostName: '',
        eventDate: '',
        status: 'draft' as const,
        theme: 'gold' as const,
        guestLink: '',
      };
    }
  }

  if (_cachedConfig && slug === _cachedSlug) {
    return _cachedConfig;
  }

  // Synchronous fallback (used by WelcomePage/HostPage which can't await)
  return getActiveEventConfig();
}

/**
 * Synchronous version for components that need immediate access.
 * Returns the cached config or an empty config.
 * Used by WelcomePage and HostPage as a temporary placeholder
 * until the async fetch completes.
 */
export function getActiveEventConfig(): EventConfig {
  if (_cachedConfig) return _cachedConfig;

  // Return a minimal placeholder — the async fetch will replace this.
  // NEVER fall back to demo event data for production events.
  return {
    platformName: eventConfig.platformName,
    name: '',
    subtitle: '',
    welcomeMessage: eventConfig.welcomeMessage,
    images: [],
    provider: eventConfig.provider,
    hostName: '',
    hostEmail: '',
    eventDate: '',
    status: 'draft' as const,
    theme: 'gold' as const,
    guestLink: '',
  };
}

/** Clear the cached config (call on navigation away). */
export function clearEventCache(): void {
  _cachedConfig = null;
  _cachedSlug = null;
}
