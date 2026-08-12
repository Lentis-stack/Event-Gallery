// ============================================================
// Lentis Gallery — Dashboard Summary Types
// ------------------------------------------------------------
// Aggregate figures shown on the Host Overview and Admin Console.
//
// FUTURE: Computed by the Python backend. For Phase 1 these are
// frontend-only mock summaries.
// ============================================================

import type { EventStatus, ThemeChoice } from './event';

/** Host Overview summary cards. */
export interface HostDashboardSummary {
  totalUploads: number;
  photoCount: number;
  videoCount: number;
  contributingGuests: number;
  /** Storage used, clearly an estimate. */
  storageUsedMb: number;
  /** Whether storage is an estimate/mock value. */
  storageIsEstimate: boolean;
}

/** Admin Console overview totals. */
export interface AdminDashboardSummary {
  totalEvents: number;
  liveEvents: number;
  totalUploads: number;
  totalHosts: number;
}

/** A preview row for the admin event list. */
export interface AdminEventSummary {
  id: string;
  slug: string;
  name: string;
  hostName: string;
  eventDate: string;
  status: EventStatus;
  theme: ThemeChoice;
  totalUploads: number;
  guestLink: string;
  archived: boolean;
}

/**
 * Export summary computed from APPROVED media only.
 * Pending and hidden media are excluded from these figures.
 *
 * FUTURE: Computed by the Python backend. For Phase 1 these are
 * frontend-only mock values built from the in-memory gallery.
 */
export interface ExportSummary {
  /** Number of approved photos. */
  photoCount: number;
  /** Number of approved videos. */
  videoCount: number;
  /** Total approved files (photos + videos). */
  totalFileCount: number;
  /** Estimated total export size, clearly an estimate. */
  estimatedSizeMb: number;
}

/** A single row in the mock export history list. */
export interface ExportHistoryRecord {
  id: string;
  /** Export destination label, e.g. "Google Photos". */
  destination: string;
  /** Human-readable date, e.g. "Aug 15, 2026". */
  date: string;
  /** Number of media items included in this export. */
  mediaCount: number;
  /** Mock status of the export. */
  status: 'prepared' | 'in-progress' | 'completed' | 'pending';
}
