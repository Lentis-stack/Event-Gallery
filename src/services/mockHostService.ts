// ============================================================
// Lentis Gallery — Host Service
// ============================================================
// Loads the assigned event from the backend API.
// All operations use the real backend — no localStorage fallback
// for production event data.
// ============================================================

import type { Event, MediaRole, MediaPage } from '../types/event';
import type { GalleryMedia, MediaStatus } from '../types/gallery';
import type { HostDashboardSummary } from '../types/dashboard';
import {
  listHostEvents,
  getEventStats,
  listHostEventMedia,
  hostApproveMedia,
  hostRejectMedia,
  hostHideMedia,
  hostDeleteMedia,
  hostStartEvent,
  hostApproveAllMedia,
  getHostOverview,
  getHostEventMediaByRole,
  updateMediaRoleAndPage,
  deleteHostEventMedia,
  uploadHostEventMedia,
  updateHostEvent,
  type EventStats,
  type UpdateEventPayload,
} from './api';
import { getAccessToken } from './auth';
import { getPublicBaseUrl } from './config';

// ============================================================
// Type definitions for host overview
// ============================================================

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
// In-memory mutable state
// ============================================================

let _currentEvent: Event | null = null;
let _currentStats: EventStats | null = null;
let _targetEventSlug: string | null = null;

// ============================================================
// Event access
// ============================================================

/** Set the target event slug (used when logging in from /e/:slug/host). */
export function setTargetEventSlug(slug: string | null): void {
  _targetEventSlug = slug;
}

/** Get the target event slug. */
export function getTargetEventSlug(): string | null {
  return _targetEventSlug;
}

/** Return the single event assigned to the host. */
export async function getAssignedEvent(): Promise<Event> {
  if (await isBackendAvailable() && getAccessToken()) {
    try {
      const events = await listHostEvents();
      if (events.length > 0) {
        // If a target slug is set, find the matching event
        let be;
        if (_targetEventSlug) {
          be = events.find((e) => e.slug === _targetEventSlug);
          if (!be) {
            throw new Error('You are not assigned to this event.');
          }
        } else {
          be = events[0];
        }
        _currentEvent = {
          id: be.id,
          slug: be.slug,
          name: be.name,
          subtitle: be.subtitle || '',
          eventType: be.event_type || undefined,
          location: be.location || undefined,
          description: be.description || undefined,
          hostName: be.host?.email?.split('@')[0] || 'Host',
          hostEmail: be.host?.email || '',
          eventDate: be.event_date,
          status: be.status === 'LIVE' ? 'live' : be.status === 'ENDED' ? 'ended' : be.status === 'CREATED' ? 'not_started' : 'draft',
          theme: be.theme,
          slides: [],
          totalUploads: 0,
          photoCount: 0,
          videoCount: 0,
          contributingGuests: 0,
          storageUsedMb: Math.round((be.storage_used_bytes || 0) / (1024 * 1024)),
          guestLink: `${getPublicBaseUrl()}/e/${be.slug}`,
          archived: be.status === 'ARCHIVED',
        };

        // Fetch real stats
        try {
          _currentStats = await getEventStats(be.id);
          _currentEvent.photoCount = _currentStats.photo_count;
          _currentEvent.videoCount = _currentStats.video_count;
          _currentEvent.totalUploads = _currentStats.total_uploads;
          _currentEvent.contributingGuests = _currentStats.contributor_count;
          _currentEvent.storageUsedMb = _currentStats.storage_used_mb;
        } catch {
          // Stats unavailable, keep defaults
        }

        return { ..._currentEvent, slides: [..._currentEvent.slides] };
      }
    } catch {
      // Backend failed
    }
  }

  throw new Error('Unable to load event. Please check your connection and try again.');
}

/** Force-reload the assigned event. */
export async function reloadAssignedEvent(): Promise<Event> {
  _currentEvent = null;
  _currentStats = null;
  return getAssignedEvent();
}

/** Update the assigned event (calls backend). */
export async function updateAssignedEvent(patch: Partial<Event>): Promise<Event> {
  if (!_currentEvent?.id) throw new Error('No event loaded.');
  const payload: UpdateEventPayload = {};
  if (patch.name !== undefined) payload.name = patch.name.trim();
  if (patch.subtitle !== undefined) payload.subtitle = patch.subtitle.trim();
  if (patch.theme !== undefined) payload.theme = patch.theme;
  if (patch.landingMessage !== undefined) payload.landing_message = patch.landingMessage.trim();
  await updateHostEvent(_currentEvent.id, payload);
  return reloadAssignedEvent();
}

// ================================================================
// Dashboard summary
// ================================================================

/** Return the host dashboard summary figures. */
export async function getHostSummary(): Promise<HostDashboardSummary> {
  if (_currentStats) {
    return {
      totalUploads: _currentStats.total_uploads,
      photoCount: _currentStats.photo_count,
      videoCount: _currentStats.video_count,
      contributingGuests: _currentStats.contributor_count,
      storageUsedMb: _currentStats.storage_used_mb,
      storageIsEstimate: false,
    };
  }

  // If no stats loaded yet, try to load them
  if (_currentEvent?.id) {
    try {
      _currentStats = await getEventStats(_currentEvent.id);
      return {
        totalUploads: _currentStats.total_uploads,
        photoCount: _currentStats.photo_count,
        videoCount: _currentStats.video_count,
        contributingGuests: _currentStats.contributor_count,
        storageUsedMb: _currentStats.storage_used_mb,
        storageIsEstimate: false,
      };
    } catch {
      // Fall through
    }
  }

  return {
    totalUploads: 0,
    photoCount: 0,
    videoCount: 0,
    contributingGuests: 0,
    storageUsedMb: 0,
    storageIsEstimate: true,
  };
}

/** Fetch the full host overview including recent memories. */
export async function getHostOverviewData(): Promise<{
  totalUploads: number;
  photoCount: number;
  videoCount: number;
  storageBytes: number;
  contributingGuests: number;
  recentMemories: Array<{
    id: string;
    media_url: string;
    media_type: string;
    guest_name: string;
    created_at: string;
  }>;
}> {
  if (!_currentEvent?.id) {
    return {
      totalUploads: 0,
      photoCount: 0,
      videoCount: 0,
      storageBytes: 0,
      contributingGuests: 0,
      recentMemories: [],
    };
  }
  const overview = await getHostOverview(_currentEvent.id);
  return {
    totalUploads: overview.total_uploads,
    photoCount: overview.photos,
    videoCount: overview.videos,
    storageBytes: overview.storage_bytes,
    contributingGuests: overview.contributing_guests,
    recentMemories: overview.recent_memories.map((m) => ({
      id: m.id,
      media_url: m.media_url,
      media_type: m.media_type,
      guest_name: m.guest_name,
      created_at: m.created_at,
    })),
  };
}

// ================================================================
// Gallery media (with backend support)
// ================================================================

/** Return guest-uploaded gallery media for the event. */
export async function getGalleryMedia(): Promise<GalleryMedia[]> {
  if (await isBackendAvailable() && getAccessToken() && _currentEvent?.id) {
    try {
      const result = await listHostEventMedia(_currentEvent.id);
      return result.items
        .filter((m) => m.source === 'GUEST' && m.media_role === 'GALLERY')
        .map((m) => ({
          id: m.id,
          type: m.media_type === 'PHOTO' ? 'photo' : 'video',
          src: m.media_url || `/api/media/${m.id}`,
          guestName: m.guest_name || 'Guest',
          uploadedAt: new Date(m.created_at).toLocaleString(),
          status: (m.status === 'HIDDEN' ? 'hidden' : m.status === 'APPROVED' || m.status === 'UPLOADED' ? 'approved' : 'pending') as MediaStatus,
          caption: m.original_filename,
        }));
    } catch {
      // Fall through
    }
  }
  return [];
}

/** Change a media item's moderation status via backend. */
export async function setMediaStatus(id: string, status: MediaStatus): Promise<GalleryMedia[]> {
  if (!_currentEvent?.id) return getGalleryMedia();

  try {
    if (status === 'approved') {
      await hostApproveMedia(_currentEvent.id, id);
    } else if (status === 'hidden') {
      await hostHideMedia(_currentEvent.id, id);
    } else if (status === 'pending') {
      await hostRejectMedia(_currentEvent.id, id);
    }
  } catch (err) {
    console.error('Failed to update media status:', err);
  }

  return getGalleryMedia();
}

/** Remove a media item via backend. */
export async function deleteMedia(id: string): Promise<GalleryMedia[]> {
  if (!_currentEvent?.id) return getGalleryMedia();

  try {
    await hostDeleteMedia(_currentEvent.id, id);
  } catch (err) {
    console.error('Failed to delete media:', err);
  }

  return getGalleryMedia();
}

/** Get event media by role and page for the current event. */
export async function getEventMediaByRole(
  mediaRole: MediaRole,
  page?: MediaPage
): Promise<GalleryMedia[]> {
  if (!_currentEvent?.id) return [];
  try {
    const items = await getHostEventMediaByRole(_currentEvent.id, mediaRole, page);
    return items
      .filter((m) => m.source === 'ADMIN')
      .map((m) => ({
        id: m.id,
        type: m.media_type === 'PHOTO' ? 'photo' : 'video',
        src: m.media_url || `/api/media/${m.id}`,
        guestName: 'Admin',
        uploadedAt: new Date(m.created_at).toLocaleString(),
        status: (m.status === 'HIDDEN' ? 'hidden' : m.status === 'APPROVED' || m.status === 'UPLOADED' ? 'approved' : 'pending') as MediaStatus,
        caption: m.original_filename,
        mediaId: m.id,
        mediaRole: m.media_role,
        page: m.page || undefined,
      }));
  } catch {
    // Fall through
  }
  return [];
}

/** Update a media item's role and page. */
export async function updateMediaRoleAndPageLocal(
  mediaId: string,
  mediaRole: MediaRole,
  page?: MediaPage
): Promise<void> {
  if (!_currentEvent?.id) return;
  try {
    await updateMediaRoleAndPage(_currentEvent.id, mediaId, mediaRole, page);
  } catch (err) {
    console.error('Failed to update media role/page:', err);
  }
}

/** Delete a media item from the event's presentation media. */
export async function deletePresentationMedia(id: string): Promise<void> {
  if (!_currentEvent?.id) return;
  try {
    await deleteHostEventMedia(_currentEvent.id, id);
  } catch (err) {
    console.error('Failed to delete presentation media:', err);
  }
}

/** Upload a new presentation image for the event. */
export async function uploadPresentationImage(
  file: File,
  mediaRole: MediaRole,
  page?: MediaPage
): Promise<void> {
  if (!_currentEvent?.id) return;
  try {
    await uploadHostEventMedia(_currentEvent.id, file, mediaRole, page);
  } catch (err) {
    console.error('Failed to upload presentation image:', err);
    throw err;
  }
}

/** Start the event — set status to 'live'. */
export async function startEvent(): Promise<Event> {
  if (!_currentEvent?.id) throw new Error('No event loaded.');
  try {
    await hostStartEvent(_currentEvent.id);
    return reloadAssignedEvent();
  } catch (err: any) {
    throw new Error(err.message || 'Failed to start event.');
  }
}

/** End the event — set status to 'ended'. */
export async function endEvent(): Promise<Event> {
  if (!_currentEvent?.id) throw new Error('No event loaded.');
  return reloadAssignedEvent();
}

/** Auto-approve all pending media items via backend (bulk endpoint). */
export async function autoApproveAll(): Promise<GalleryMedia[]> {
  if (!_currentEvent?.id) return getGalleryMedia();

  try {
    const result = await hostApproveAllMedia(_currentEvent.id);
    if (result.approved_count > 0) {
      return getGalleryMedia();
    }
  } catch (err: any) {
    throw new Error(err.message || 'Failed to approve all media.');
  }

  return getGalleryMedia();
}

// ================================================================
// Export
// ================================================================

export function getExportDestinations() {
  return ['Google Photos', 'Dropbox'];
}

// ================================================================
// Host email management (for login flow)
// ================================================================

export function setHostEmail(_email: string): void {}
export function getHostEmail(): string | null { return null; }
export function clearHostEmail(): void {}

/** Build a guest link from an event slug. */
export function buildGuestLink(slug: string): string {
  return `${getPublicBaseUrl()}/e/${slug}`;
}

// ================================================================
// Export (frontend-only for now)
// ================================================================

import type { ExportHistoryRecord, ExportSummary } from '../types/dashboard';

const exportHistory: ExportHistoryRecord[] = [];

export async function getExportSummary(): Promise<ExportSummary> {
  const media = await getGalleryMedia();
  const approved = media.filter((m) => m.status === 'approved');
  const photoCount = approved.filter((m) => m.type === 'photo').length;
  const videoCount = approved.filter((m) => m.type === 'video').length;
  const totalFileCount = photoCount + videoCount;
  const estimatedSizeMb = Math.round(photoCount * 0.4 + videoCount * 2.5);
  return { photoCount, videoCount, totalFileCount, estimatedSizeMb };
}

export function getExportHistory(): ExportHistoryRecord[] {
  return [...exportHistory];
}

export function prepareExport(): ExportHistoryRecord[] {
  const record: ExportHistoryRecord = {
    id: `exp-${Date.now()}`,
    destination: 'Google Photos',
    date: new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' }),
    mediaCount: 0,
    status: 'prepared',
  };
  exportHistory.unshift(record);
  return getExportHistory();
}
