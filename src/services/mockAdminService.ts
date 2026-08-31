// ============================================================
// Lentis Gallery — Admin Event Service
// ============================================================
// All event CRUD operations go through the real FastAPI backend.
// PostgreSQL is the source of truth for all events.
// ============================================================

import type { Event, EventSlide, EventStatus } from '../types/event';
import type { AdminDashboardSummary } from '../types/dashboard';
import {
  listEvents as apiListEvents,
  getEvent as apiGetEvent,
  createEvent as apiCreateEvent,
  updateEvent as apiUpdateEvent,
  archiveEvent as apiArchiveEvent,
  restoreEvent as apiRestoreEvent,
  deleteEvent as apiDeleteEvent,
  uploadEventMedia as apiUploadEventMedia,
  toFrontendEvent,
} from './api';
import type { CreateEventPayload, MediaRole, MediaPage } from './api';

// Re-export media management functions for admin use
export {
  listEventMedia,
  deleteEventMedia,
  setMediaRole,
  reorderSlideshow,
  uploadEventMedia,
  getHostSlideshowMedia,
} from './api';
export type { MediaItem, MediaRole, MediaPage } from './api';

// ============================================================
// Backend availability check
// ============================================================

let _backendAvailable: boolean | null = null;
async function isBackendAvailable(): Promise<boolean> {
  if (_backendAvailable !== null) return _backendAvailable;
  try {
    const res = await fetch('/api/health', { method: 'GET' });
    _backendAvailable = res.ok;
  } catch {
    _backendAvailable = false;
  }
  return _backendAvailable;
}

// ============================================================
// Public API
// ============================================================

export async function getEvents(includeArchived = false): Promise<Event[]> {
  if (!(await isBackendAvailable())) {
    throw new Error('Unable to load events. The backend server is not available. Please check your connection and try again.');
  }
  try {
    const backendEvents = await apiListEvents();
    const events = backendEvents.map((be) => toFrontendEvent(be));
    return events.filter((e) => includeArchived || !e.archived);
  } catch (err) {
    console.error('Failed to fetch events from backend:', err);
    throw new Error('Unable to load events. Please check your connection and try again.');
  }
}

export async function getEventById(id: string): Promise<Event | undefined> {
  if (!(await isBackendAvailable())) {
    throw new Error('Backend is not available. Cannot load event.');
  }
  try {
    const be = await apiGetEvent(id);
    return toFrontendEvent(be);
  } catch (err) {
    console.error('Failed to fetch event from backend:', err);
    throw new Error('Unable to load event. Please check your connection and try again.');
  }
}

export async function createEvent(input: {
  name: string;
  subtitle: string;
  hostName: string;
  eventDate: string;
  slug: string;
  theme: Event['theme'];
  hostEmail: string;
  hostPassword: string;
  eventType?: string;
  location?: string;
  description?: string;
  landingMessage?: string;
  accessMode?: 'PUBLIC' | 'PRIVATE';
}): Promise<Event> {
  if (!(await isBackendAvailable())) {
    throw new Error('Unable to create event. The backend server is not available. Please check your connection and try again.');
  }
  const payload: CreateEventPayload = {
    name: input.name.trim(),
    subtitle: input.subtitle.trim() || undefined,
    event_type: input.eventType || undefined,
    location: input.location || undefined,
    description: input.description || undefined,
    landing_message: input.landingMessage || undefined,
    host_email: input.hostEmail.trim(),
    host_password: input.hostPassword,
    event_date: input.eventDate,
    theme: input.theme,
    access_mode: (input as any).accessMode || undefined,
    slug: input.slug || undefined,
  };
  const backendEvent = await apiCreateEvent(payload);
  return toFrontendEvent(backendEvent);
}

export async function uploadFilesToEvent(
  eventId: string,
  files: File[],
  mediaRole: MediaRole = 'GALLERY',
  fileRoles?: MediaRole[],
  filePages?: (MediaPage | undefined)[],
): Promise<Array<{ file: string; success: boolean; error?: string; mediaId?: string }>> {
  const results: Array<{ file: string; success: boolean; error?: string; mediaId?: string }> = [];
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const role = fileRoles?.[i] || mediaRole;
    const page = filePages?.[i];
    try {
      const result = await apiUploadEventMedia(eventId, file, role, 'ADMIN', page);
      results.push({ file: file.name, success: true, mediaId: result.id });
    } catch (err: any) {
      results.push({ file: file.name, success: false, error: err.message || 'Upload failed' });
    }
  }
  return results;
}

export async function updateEventStatus(id: string, status: EventStatus): Promise<Event | undefined> {
  if (!(await isBackendAvailable())) {
    throw new Error('Unable to update event. Backend is not available.');
  }
  try {
    const backendStatus = status === 'live' ? 'LIVE' : status === 'ended' ? 'ENDED' : status === 'not_started' ? 'CREATED' : 'ARCHIVED';
    await apiUpdateEvent(id, { status: backendStatus });
    return getEventById(id);
  } catch (err) {
    throw new Error('Failed to update event status. Please try again.');
  }
}

export async function updateEvent(id: string, patch: Partial<Event>): Promise<Event | undefined> {
  if (!(await isBackendAvailable())) {
    throw new Error('Unable to update event. Backend is not available.');
  }
  try {
    // Support both camelCase (hostPassword) from the Event type
    // and snake_case (host_password) passed directly by callers.
    const password = (patch as any).host_password || patch.hostPassword;
    await apiUpdateEvent(id, {
      name: patch.name, subtitle: patch.subtitle,
      event_type: patch.eventType, location: patch.location,
      description: patch.description, landing_message: patch.landingMessage,
      event_date: patch.eventDate,
      theme: patch.theme,
      access_mode: (patch as any).accessMode,
      ...(password ? { host_password: password } : {}),
    });
    return getEventById(id);
  } catch (err) {
    throw new Error('Failed to save changes. Please try again.');
  }
}

export async function deleteEvent(id: string): Promise<void> {
  if (!(await isBackendAvailable())) {
    throw new Error('Unable to delete event. Backend is not available.');
  }
  try {
    await apiDeleteEvent(id);
  } catch (err) {
    throw new Error('Failed to delete event. Please try again.');
  }
}

export async function archiveEvent(id: string): Promise<Event | undefined> {
  if (!(await isBackendAvailable())) {
    throw new Error('Unable to archive event. Backend is not available.');
  }
  try {
    await apiArchiveEvent(id);
    return getEventById(id);
  } catch (err) {
    throw new Error('Failed to archive event. Please try again.');
  }
}

export async function restoreEvent(id: string): Promise<Event | undefined> {
  if (!(await isBackendAvailable())) {
    throw new Error('Unable to restore event. Backend is not available.');
  }
  try {
    await apiRestoreEvent(id);
    return getEventById(id);
  } catch (err) {
    throw new Error('Failed to restore event. Please try again.');
  }
}

export async function updateHostCredentials(id: string, _hostEmail: string, _hostPassword: string): Promise<Event | undefined> {
  // Host credentials are managed by the backend. This is a no-op on the frontend.
  return getEventById(id);
}

export async function getActiveEvent(): Promise<Event | null> {
  if (!(await isBackendAvailable())) {
    return null;
  }
  try {
    const backendEvents = await apiListEvents();
    const events = backendEvents
      .filter((be) => be.status !== 'ARCHIVED')
      .map((be) => toFrontendEvent(be));
    const live = events.find((e) => e.status === 'live');
    return live || events[0] || null;
  } catch {
    return null;
  }
}

export async function getAdminSummary(): Promise<AdminDashboardSummary> {
  const events = await getEvents(true);
  return {
    totalEvents: events.filter((e) => !e.archived).length,
    liveEvents: events.filter((e) => e.status === 'live' && !e.archived).length,
    totalUploads: events.reduce((sum, e) => sum + e.totalUploads, 0),
    totalHosts: new Set(events.map((e) => e.hostName)).size,
  };
}

export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export async function fileToSlide(file: File): Promise<EventSlide> {
  const dataUrl = await fileToDataUrl(file);
  return { src: dataUrl, alt: file.name };
}

export async function uploadFileToEvent(eventId: string, file: File, mediaRole: MediaRole = 'GALLERY') {
  return apiUploadEventMedia(eventId, file, mediaRole);
}

export function slugify(name: string): string {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
