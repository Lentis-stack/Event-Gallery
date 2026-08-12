// ============================================================
// Lentis Gallery — Gallery Media Types
// ------------------------------------------------------------
// Types for guest uploads shown in the Host Console gallery.
//
// FUTURE: These will be served by the Python backend. For Phase 1
// they are frontend-only mock values.
// ============================================================

export type MediaType = 'photo' | 'video';

export type MediaStatus = 'approved' | 'pending' | 'hidden';

/**
 * A single guest upload (photo or video) in the event gallery.
 */
export interface GalleryMedia {
  id: string;
  /** Media type: photo or video. */
  type: MediaType;
  /** Thumbnail / source URL (local asset). */
  src: string;
  /** Guest who uploaded this media. */
  guestName: string;
  /** Human-readable upload time, e.g. "2h ago". */
  uploadedAt: string;
  /** Moderation status. */
  status: MediaStatus;
  /** Optional caption. */
  caption?: string;
}

/** A guest who contributed to the event gallery. */
export interface Guest {
  id: string;
  name: string;
  /** Number of items contributed. */
  contributionCount: number;
  /** Last active time. */
  lastActive: string;
}
