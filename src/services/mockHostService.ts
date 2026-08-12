// ============================================================
// Lentis Gallery — Mock Host Service
// ------------------------------------------------------------
// Frontend-only service layer for the Event Host Console.
// All operations are local/in-memory (React state or module state).
//
// FUTURE: These functions will be replaced by calls to the Python
// backend API (REST + WebSocket). Keep the same signatures so the
// UI does not need to change when the real API arrives.
// ============================================================

import type { Event } from '../types/event';
import type { GalleryMedia, MediaStatus } from '../types/gallery';
import type { ExportHistoryRecord, ExportSummary, HostDashboardSummary } from '../types/dashboard';
import {
  mockAssignedEvent,
  mockGalleryMedia,
  mockHostSummary,
} from '../data/mockHostData';

// --- In-memory mutable state (resets on refresh) -----------------
// This simulates what the backend will hold in a database.
let currentEvent: Event = { ...mockAssignedEvent };
let currentMedia: GalleryMedia[] = [...mockGalleryMedia];

// ================================================================
// Event access
// ================================================================

/** Return the single event assigned to the host. */
export function getAssignedEvent(): Event {
  return { ...currentEvent, slides: [...currentEvent.slides] };
}

/** Update the assigned event (frontend-only, resets on refresh). */
export function updateAssignedEvent(patch: Partial<Event>): Event {
  currentEvent = { ...currentEvent, ...patch };
  return getAssignedEvent();
}

// ================================================================
// Dashboard summary
// ================================================================

/** Return the host dashboard summary figures. */
export function getHostSummary(): HostDashboardSummary {
  return { ...mockHostSummary };
}

// ================================================================
// Gallery media
// ================================================================

/** Return all gallery media for the event. */
export function getGalleryMedia(): GalleryMedia[] {
  return [...currentMedia];
}

/** Change a media item's moderation status. */
export function setMediaStatus(id: string, status: MediaStatus): GalleryMedia[] {
  currentMedia = currentMedia.map((m) => (m.id === id ? { ...m, status } : m));
  return getGalleryMedia();
}

/** Remove a media item from the gallery. */
export function deleteMedia(id: string): GalleryMedia[] {
  currentMedia = currentMedia.filter((m) => m.id !== id);
  return getGalleryMedia();
}

// ================================================================
// Export (Archive & Export)
// ================================================================
// FUTURE BACKEND RESPONSIBILITIES (replaces this mock section):
//   1. Secure Python backend (FastAPI/Django) holding real events.
//   2. OAuth account connection + encrypted token storage so the
//      host can authorize Google Photos / Dropbox on their account.
//   3. Background export jobs that copy approved media to the chosen
//      destination, with progress and error tracking.
//   4. Permission checks so each Event Host can only export media
//      belonging to their own event.
// -----------------------------------------------------------------

/** Mock destinations advertised in the export UI. */
const MOCK_DESTINATIONS = ['Google Photos', 'Dropbox'] as const;

// In-memory export history (resets on refresh, like the rest of the mock).
let exportHistory: ExportHistoryRecord[] = [
  {
    id: 'exp-1',
    destination: 'Google Photos',
    date: 'Aug 12, 2026',
    mediaCount: 214,
    status: 'prepared',
  },
  {
    id: 'exp-2',
    destination: 'Dropbox',
    date: 'Aug 02, 2026',
    mediaCount: 32,
    status: 'completed',
  },
];

/**
 * Build an export summary from ONLY approved media.
 * Pending and hidden items are intentionally excluded.
 */
export function getExportSummary(): ExportSummary {
  const approved = currentMedia.filter((m) => m.status === 'approved');
  const photoCount = approved.filter((m) => m.type === 'photo').length;
  const videoCount = approved.filter((m) => m.type === 'video').length;
  const totalFileCount = photoCount + videoCount;
  // Placeholder estimate for a pre-backend demo: ~0.4 MB per photo.
  // FUTURE: The backend will compute accurate sizes from real files.
  const estimatedSizeMb = Math.round(photoCount * 0.4 + videoCount * 2.5);

  return {
    photoCount,
    videoCount,
    totalFileCount,
    estimatedSizeMb,
  };
}

/** Return the list of mock export destinations. */
export function getExportDestinations() {
  return [...MOCK_DESTINATIONS];
}

/** Return mock export history records. */
export function getExportHistory(): ExportHistoryRecord[] {
  return exportHistory.map((r) => ({ ...r }));
}

/**
 * Frontend-only "prepare export" mock.
 * Adds a history record and returns the updated list.
 */
export function prepareExport(): ExportHistoryRecord[] {
  const summary = getExportSummary();
  // Newest record first so the latest action is visible at the top.
  exportHistory = [
    {
      id: `exp-${Date.now()}`,
      destination: MOCK_DESTINATIONS[0], // default preview destination
      date: new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
      }),
      mediaCount: summary.totalFileCount,
      status: 'prepared',
    },
    ...exportHistory,
  ];
  return getExportHistory();
}

// ================================================================
// Client-side helpers
// ================================================================

/** Build a guest link from an event slug. */
export function buildGuestLink(slug: string): string {
  return `https://lentis.gallery/${slug}`;
}
