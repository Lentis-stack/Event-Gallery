// ============================================================
// Lentis Gallery — Host StatusBadge
// ------------------------------------------------------------
// Displays a media moderation status (approved/pending/hidden)
// or an event lifecycle status (draft/live/ended) as a small
// pill. Uses the cinematic gold/dark design language.
// ============================================================

import type { MediaStatus } from '../../types/gallery';
import type { EventStatus } from '../../types/event';

type BadgeStatus = MediaStatus | EventStatus;

interface StatusBadgeProps {
  status: BadgeStatus;
  /** Optional custom label (defaults to the status text). */
  label?: string;
}

/** Human-friendly label per status. */
const LABELS: Record<BadgeStatus, string> = {
  approved: 'Approved',
  pending: 'Pending',
  hidden: 'Hidden',
  draft: 'Draft',
  not_started: 'Not Started',
  live: 'Live',
  ended: 'Ended',
  archived: 'Archived',
};

/**
 * A small pill badge that reflects the semantic tone of a status.
 * Approved/Live → gold; Pending → neutral; Hidden/Ended/Draft → muted.
 */
export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const text = label ?? LABELS[status];
  return (
    <span className={`status-badge status-badge--${status}`} aria-label={`Status: ${text}`}>
      <span className="status-badge__dot" aria-hidden="true" />
      {text}
    </span>
  );
}
