// ============================================================
// Lentis Gallery — Backend API Service
// ============================================================
// Central service for ALL communication with the FastAPI backend.
// ============================================================

import { API_BASE, getPublicBaseUrl } from './config';
import { authHeaders } from './auth';
import type { Event, EventSlide } from '../types/event';

// ============================================================
// Types (matching backend Pydantic schemas)
// ============================================================

export type MediaRole = 'HERO' | 'SLIDESHOW' | 'GALLERY' | 'HOST_SLIDESHOW';
export type MediaSource = 'ADMIN' | 'GUEST';
export type MediaPage = 'LANDING' | 'GUEST' | 'HOST' | 'CAMERA';

export interface BackendEvent {
  id: string;
  name: string;
  slug: string;
  subtitle: string | null;
  event_type: string | null;
  location: string | null;
  description: string | null;
  landing_message: string | null;
  host_id: string;
  event_date: string;
  status: 'CREATED' | 'LIVE' | 'ENDED' | 'ARCHIVED';
  theme: 'gold' | 'blue' | 'rose' | 'emerald';
  access_mode: 'PUBLIC' | 'PRIVATE';
  storage_limit_gb: number;
  storage_used_bytes: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  host?: { id: string; email: string } | null;
}

export interface PublicEvent {
  name: string;
  slug: string;
  subtitle: string | null;
  event_type: string | null;
  location: string | null;
  description: string | null;
  landing_message: string | null;
  theme: 'gold' | 'blue' | 'rose' | 'emerald';
  event_date: string;
  status: string;
  access_mode: 'PUBLIC' | 'PRIVATE';
}

export interface EventStats {
  event_id: string;
  photo_count: number;
  video_count: number;
  total_uploads: number;
  contributor_count: number;
  storage_used_bytes: number;
  storage_used_mb: number;
  storage_used_gb: number;
  storage_limit_gb: number;
}

export interface MediaItem {
  id: string;
  event_id: string;
  media_type: string;
  media_role: MediaRole;
  position: number | null;
  source: MediaSource;
  page: MediaPage | null;
  mime_type: string;
  original_filename: string;
  file_size: number;
  status: string;
  processing_status: string;
  optimized: boolean;
  thumbnail: boolean;
  poster: boolean;
  media_url: string | null;
  created_at: string;
  guest_name: string | null;
  moderation_status?: string;
}

export interface PublicMediaResponse {
  hero: Array<{ src: string; alt: string; id: string }>;
  slideshow: Array<{ src: string; alt: string; id: string }>;
  guest_slideshow: Array<{ src: string; alt: string; id: string }>;
  camera_slideshow: Array<{ src: string; alt: string; id: string }>;
  gallery: Array<{ src: string; alt: string; id: string; full_src?: string; media_type?: string }>;
  gallery_total?: number;
  next_cursor?: string | null;
  images: Array<{ src: string; alt: string; id: string }>; // backward compat
}

export interface GalleryItem {
  id: string;
  src: string;        // thumbnail URL (fast grid display)
  full_src: string;   // optimized full-size URL
  alt: string;
  media_type: string;  // PHOTO or VIDEO
  width: number | null;
  height: number | null;
  file_size: number;
  created_at: string | null;
}

export interface PaginatedGalleryResponse {
  items: GalleryItem[];
  total: number;
  next_cursor: string | null;
}

export interface MediaUploadResponse {
  id: string;
  media_type: string;
  media_role: MediaRole;
  position: number | null;
  source: MediaSource;
  page: MediaPage | null;
  status: string;
  processing_status: string;
  original_filename: string;
  file_size: number;
  created_at: string;
}

export interface CreateEventPayload {
  name: string;
  subtitle?: string;
  event_type?: string;
  location?: string;
  description?: string;
  landing_message?: string;
  host_id?: string;
  host_email?: string;
  host_password?: string;
  event_date: string;
  theme?: string;
  access_mode?: 'PUBLIC' | 'PRIVATE';
  slug?: string;
}

export interface UpdateEventPayload {
  name?: string;
  subtitle?: string;
  event_type?: string;
  location?: string;
  description?: string;
  landing_message?: string;
  event_date?: string;
  theme?: string;
  access_mode?: 'PUBLIC' | 'PRIVATE';
  status?: string;
  host_email?: string;
  host_password?: string;
}

// ============================================================
// API Client Helpers
// ============================================================

export function extractErrorDetail(body: any): string {
  if (typeof body?.detail === 'string') return body.detail;
  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((e: any) => {
        if (typeof e === 'string') return e;
        if (e?.msg) {
          const loc = Array.isArray(e.loc) ? e.loc.slice(1).join('.') : '';
          return loc ? `${loc}: ${e.msg}` : e.msg;
        }
        return String(e);
      })
      .join('; ');
  }
  return `API request failed (${body?.status || 'unknown'})`;
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = API_BASE + path;
  const headers = { ...authHeaders(), ...options.headers };
  const res = await fetch(url, { ...options, headers, credentials: 'include' });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorDetail(body));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ============================================================
// Event CRUD
// ============================================================

export async function createEvent(payload: CreateEventPayload): Promise<BackendEvent> {
  return apiRequest<BackendEvent>('/api/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function listEvents(): Promise<BackendEvent[]> {
  return apiRequest<BackendEvent[]>('/api/admin/events');
}

export async function getEvent(eventId: string): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/admin/events/${eventId}`);
}

export async function updateEvent(eventId: string, payload: UpdateEventPayload): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/admin/events/${eventId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function archiveEvent(eventId: string): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/admin/events/${eventId}/archive`, { method: 'POST' });
}

export async function restoreEvent(eventId: string): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/admin/events/${eventId}/restore`, { method: 'POST' });
}

export async function deleteEvent(eventId: string): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/admin/events/${eventId}`, { method: 'DELETE' });
}

export async function permanentDeleteEvent(eventId: string): Promise<void> {
  await apiRequest<void>(`/api/admin/events/${eventId}/permanent`, { method: 'DELETE' });
}

// ============================================================
// Public Event
// ============================================================

export async function getPublicEvent(slug: string): Promise<PublicEvent> {
  return apiRequest<PublicEvent>(`/api/events/${slug}/public`);
}

export async function getPublicEventMedia(slug: string): Promise<PublicMediaResponse> {
  return apiRequest<PublicMediaResponse>(`/api/events/${slug}/public-media`);
}

export async function getPublicHostSlideshow(slug: string): Promise<Array<{ src: string; alt: string; id: string }>> {
  return apiRequest<Array<{ src: string; alt: string; id: string }>>(`/api/events/${slug}/host-slideshow`);
}

export async function getPublicGallery(
  slug: string,
  cursor?: string | null,
  limit: number = 50,
  mediaType?: string,
): Promise<PaginatedGalleryResponse> {
  const params = new URLSearchParams();
  if (cursor) params.set('cursor', cursor);
  params.set('limit', String(limit));
  if (mediaType) params.set('media_type', mediaType);
  const qs = params.toString();
  return apiRequest<PaginatedGalleryResponse>(
    `/api/events/${slug}/gallery${qs ? '?' + qs : ''}`
  );
}

// ============================================================
// Event Stats
// ============================================================

export async function getEventStats(eventId: string): Promise<EventStats> {
  return apiRequest<EventStats>(`/api/events/${eventId}/stats`);
}

// ============================================================
// Media Upload (admin)
// ============================================================

export async function uploadEventMedia(
  eventId: string,
  file: File,
  mediaRole: MediaRole = 'GALLERY',
  source: MediaSource = 'ADMIN',
  page?: MediaPage,
): Promise<MediaUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('media_role', mediaRole);
  formData.append('source', source);
  if (page) formData.append('page', page);
  const url = API_BASE + `/api/admin/events/${eventId}/media`;
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorDetail(body));
  }
  return res.json();
}

export async function listEventMedia(eventId: string): Promise<{ items: MediaItem[]; total: number }> {
  return apiRequest<{ items: MediaItem[]; total: number }>(`/api/admin/events/${eventId}/media`);
}

export async function deleteEventMedia(eventId: string, mediaId: string): Promise<void> {
  await apiRequest<void>(`/api/admin/events/${eventId}/media/${mediaId}`, { method: 'DELETE' });
}

export async function setMediaRole(eventId: string, mediaId: string, role: MediaRole, page?: MediaPage): Promise<MediaItem> {
  return apiRequest<MediaItem>(`/api/admin/events/${eventId}/media/${mediaId}/role`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ media_role: role, page: page || null }),
  });
}

export async function reorderSlideshow(eventId: string, orderedIds: string[]): Promise<void> {
  await apiRequest<void>(`/api/admin/events/${eventId}/media/reorder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ordered_ids: orderedIds }),
  });
}

export function getMediaUrl(storageKey: string): string {
  return `${API_BASE}/api/media/${storageKey}`;
}

// ============================================================
// Host Event
// ============================================================

export async function listHostEvents(): Promise<BackendEvent[]> {
  return apiRequest<BackendEvent[]>('/api/host/events');
}

export async function getHostEvent(eventId: string): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/host/events/${eventId}`);
}

export async function updateHostEvent(eventId: string, payload: UpdateEventPayload): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/host/events/${eventId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

// ============================================================
// Host Event Media Management
// ============================================================

export async function getHostEventMediaByRole(
  eventId: string,
  mediaRole: MediaRole,
  page?: MediaPage
): Promise<MediaItem[]> {
  const params = new URLSearchParams({ media_role: mediaRole });
  if (page) params.set('page', page);
  const res = await apiRequest<{ items: MediaItem[]; total: number }>(`/api/host/events/${eventId}/media?${params.toString()}`);
  return res.items || [];
}

export async function updateMediaRoleAndPage(
  eventId: string,
  mediaId: string,
  mediaRole: MediaRole,
  page?: MediaPage
): Promise<MediaItem> {
  return apiRequest<MediaItem>(`/api/host/events/${eventId}/media/${mediaId}/role`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ media_role: mediaRole, page: page || null }),
  });
}

export async function deleteHostEventMedia(eventId: string, mediaId: string): Promise<void> {
  await apiRequest<void>(`/api/host/events/${eventId}/media/${mediaId}`, { method: 'DELETE' });
}

export async function uploadHostEventMedia(
  eventId: string,
  file: File,
  mediaRole: MediaRole = 'GALLERY',
  page?: MediaPage
): Promise<MediaUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('media_role', mediaRole);
  formData.append('source', 'ADMIN');
  if (page) formData.append('page', page);
  const url = API_BASE + `/api/host/events/${eventId}/media`;
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorDetail(body));
  }
  return res.json();
}

export async function listHostEventMedia(eventId: string): Promise<{ items: MediaItem[]; total: number }> {
  return apiRequest<{ items: MediaItem[]; total: number }>(`/api/host/events/${eventId}/media`);
}

export async function getHostSlideshowMedia(eventId: string): Promise<Array<{ src: string; alt: string; id: string }>> {
  return apiRequest<Array<{ src: string; alt: string; id: string }>>(`/api/host/events/${eventId}/slideshow`);
}

// ============================================================
// Host Moderation
// ============================================================

export async function hostApproveMedia(eventId: string, mediaId: string): Promise<MediaItem> {
  return apiRequest<MediaItem>(`/api/host/events/${eventId}/media/${mediaId}/approve`, { method: 'POST' });
}

export async function hostRejectMedia(eventId: string, mediaId: string): Promise<MediaItem> {
  return apiRequest<MediaItem>(`/api/host/events/${eventId}/media/${mediaId}/reject`, { method: 'POST' });
}

export async function hostHideMedia(eventId: string, mediaId: string): Promise<MediaItem> {
  return apiRequest<MediaItem>(`/api/host/events/${eventId}/media/${mediaId}/hide`, { method: 'POST' });
}

export async function hostUnhideMedia(eventId: string, mediaId: string): Promise<MediaItem> {
  return apiRequest<MediaItem>(`/api/host/events/${eventId}/media/${mediaId}/unhide`, { method: 'POST' });
}

export async function hostDeleteMedia(eventId: string, mediaId: string): Promise<void> {
  await apiRequest<void>(`/api/host/events/${eventId}/media/${mediaId}`, { method: 'DELETE' });
}

// ============================================================
// Host Event Lifecycle
// ============================================================

export async function hostStartEvent(eventId: string): Promise<BackendEvent> {
  return apiRequest<BackendEvent>(`/api/host/events/${eventId}/start`, { method: 'POST' });
}

export async function hostApproveAllMedia(eventId: string): Promise<{ approved_count: number }> {
  return apiRequest<{ approved_count: number }>(`/api/host/events/${eventId}/media/approve-all`, { method: 'POST' });
}

export interface HostOverviewStats {
  total_uploads: number;
  photos: number;
  videos: number;
  storage_bytes: number;
  contributing_guests: number;
  recent_memories: Array<{
    id: string;
    media_url: string;
    media_type: string;
    guest_name: string;
    created_at: string;
  }>;
}

export async function getHostOverview(eventId: string): Promise<HostOverviewStats> {
  return apiRequest<HostOverviewStats>(`/api/host/events/${eventId}/overview`);
}

// ============================================================
// Guest Upload
// ============================================================

export async function guestUploadMedia(
  slug: string,
  guestToken: string,
  file: File
): Promise<MediaUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/api/events/${slug}/media`, {
    method: 'POST',
    headers: { 'X-Guest-Token': guestToken },
    credentials: 'include',
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorDetail(body));
  }
  return res.json();
}

export interface GuestMediaItem {
  id: string;
  media_type: string;
  status: string;
  processing_status: string;
  original_filename: string;
  file_size: number;
  media_url: string | null;
  created_at: string;
}

export interface GuestMediaListResponse {
  items: GuestMediaItem[];
  total: number;
}

export async function getGuestMedia(
  slug: string,
  guestToken: string
): Promise<GuestMediaListResponse> {
  const res = await fetch(`${API_BASE}/api/events/${slug}/media/me`, {
    headers: { 'X-Guest-Token': guestToken },
    credentials: 'include',
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorDetail(body));
  }
  return res.json();
}

// ============================================================
// Utility
// ============================================================

export function toFrontendEvent(backend: BackendEvent, slides: EventSlide[] = []): Event {
  return {
    id: backend.id,
    slug: backend.slug,
    name: backend.name,
    subtitle: backend.subtitle || '',
    eventType: backend.event_type || undefined,
    location: backend.location || undefined,
    description: backend.description || undefined,
    landingMessage: backend.landing_message || undefined,
    hostName: backend.host?.email?.split('@')[0] || 'Host',
    hostEmail: backend.host?.email || '',
    eventDate: backend.event_date,
    status: backend.status === 'LIVE' ? 'live' : backend.status === 'ENDED' ? 'ended' : backend.status === 'CREATED' ? 'not_started' : 'draft',
    theme: backend.theme,
    accessMode: backend.access_mode || 'PUBLIC',
    slides,
    totalUploads: 0,
    photoCount: 0,
    videoCount: 0,
    contributingGuests: 0,
    storageUsedMb: Math.round((backend.storage_used_bytes || 0) / (1024 * 1024)),
    guestLink: `${getPublicBaseUrl()}/e/${backend.slug}`,
    archived: backend.status === 'ARCHIVED',
  };
}

// ============================================================
// Invited Guest Management (Private Events)
// ============================================================

export interface InvitedGuest {
  id: string;
  event_id: string;
  name: string;
  status: 'INVITED' | 'ACTIVE' | 'REMOVED';
  created_at: string;
  last_login_at: string | null;
}

export interface InvitedGuestListResponse {
  guests: InvitedGuest[];
  total: number;
  joined: number;
  not_joined: number;
}

export async function listInvitedGuests(eventId: string): Promise<InvitedGuestListResponse> {
  return apiRequest<InvitedGuestListResponse>(`/api/admin/events/${eventId}/guests`);
}

export async function addInvitedGuest(
  eventId: string,
  name: string,
  password: string,
): Promise<InvitedGuest> {
  return apiRequest<InvitedGuest>(`/api/admin/events/${eventId}/guests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, password }),
  });
}

export async function resetInvitedGuestPassword(
  eventId: string,
  guestId: string,
  password: string,
): Promise<InvitedGuest> {
  return apiRequest<InvitedGuest>(`/api/admin/events/${eventId}/guests/${guestId}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
}

export async function removeInvitedGuest(
  eventId: string,
  guestId: string,
): Promise<void> {
  await apiRequest<void>(`/api/admin/events/${eventId}/guests/${guestId}`, {
    method: 'DELETE',
  });
}

export async function privateGuestLogin(
  slug: string,
  name: string,
  password: string,
): Promise<{ guest: InvitedGuest; session_token: string; expires_at: string }> {
  return apiRequest(`/api/events/${slug}/guests/private-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, password }),
  });
}
