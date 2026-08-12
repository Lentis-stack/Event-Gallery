// ============================================================
// Lentis Gallery — Mock Admin Service
// ------------------------------------------------------------
// Frontend-only service layer for the Lentis Admin Console.
// All operations are local/in-memory (module-level state),
// so they reset on page refresh.
//
// FUTURE: These functions will be replaced by calls to the Python
// backend API. Keep the same signatures so the UI does not need
// to change when the real API arrives.
// ============================================================

import type { Event, EventStatus } from '../types/event';
import type { AdminDashboardSummary } from '../types/dashboard';
import { mockAdminSummary, mockEvents } from '../data/mockAdminData';
import { buildGuestLink } from './mockHostService';

// --- In-memory mutable state (resets on refresh) -----------------
let events: Event[] = [...mockEvents];

// Track new event ids so we can generate unique slugs.
let idCounter = events.length + 1;

// ================================================================
// Event access
// ================================================================

/** Return all events (optionally excluding archived). */
export function getEvents(includeArchived = false): Event[] {
  return events
    .filter((e) => includeArchived || !e.archived)
    .map((e) => ({ ...e, slides: [...e.slides] }));
}

/** Return a single event by id. */
export function getEventById(id: string): Event | undefined {
  const found = events.find((e) => e.id === id);
  return found ? { ...found, slides: [...found.slides] } : undefined;
}

// ================================================================
// Event creation & management
// ================================================================

/** Create a new event from a partial payload. */
export function createEvent(input: {
  name: string;
  subtitle: string;
  hostName: string;
  eventDate: string;
  slug: string;
  theme: Event['theme'];
  slides: Event['slides'];
}): Event {
  const id = `evt_${Date.now()}`;
  idCounter += 1;

  const newEvent: Event = {
    id,
    slug: input.slug,
    name: input.name,
    subtitle: input.subtitle,
    hostName: input.hostName,
    eventDate: input.eventDate,
    status: 'draft',
    theme: input.theme,
    slides: [...input.slides],
    totalUploads: 0,
    photoCount: 0,
    videoCount: 0,
    contributingGuests: 0,
    storageUsedMb: 0,
    guestLink: buildGuestLink(input.slug),
    archived: false,
  };

  events = [newEvent, ...events];
  return { ...newEvent, slides: [...newEvent.slides] };
}

/** Update an event's status. */
export function updateEventStatus(id: string, status: EventStatus): Event | undefined {
  events = events.map((e) => (e.id === id ? { ...e, status } : e));
  return getEventById(id);
}

/** Edit an event's basic fields (frontend-only). */
export function updateEvent(
  id: string,
  patch: Partial<Event>
): Event | undefined {
  events = events.map((e) => (e.id === id ? { ...e, ...patch } : e));
  return getEventById(id);
}

/** Archive (soft-delete) an event. */
export function archiveEvent(id: string): Event | undefined {
  events = events.map((e) => (e.id === id ? { ...e, archived: true } : e));
  return getEventById(id);
}

// ================================================================
// Dashboard summary
// ================================================================

/** Return the admin dashboard totals. */
export function getAdminSummary(): AdminDashboardSummary {
  return { ...mockAdminSummary };
}

/** Generate a slug from an event name. */
export function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
