// ============================================================
// Lentis Gallery — Admin EventCard
// ------------------------------------------------------------
// A single event card in the Lentis Admin Console.
// Shows event name, host, date, status badge, upload count,
// and admin actions (set live / end / archive).
//
// Data is provided by the mock admin service (frontend-only).
// ============================================================

import type { Event, EventStatus } from '../../types/event';
import StatusBadge from '../host/StatusBadge';
import { buildGuestLink } from '../../services/mockHostService';

interface EventCardProps {
  event: Event;
  /** Called when the event status changes. */
  onStatusChange: (id: string, status: EventStatus) => void;
  /** Called when the event is archived. */
  onArchive: (id: string) => void;
}

/**
 * Admin-facing event card with lifecycle controls.
 */
export default function EventCard({ event, onStatusChange, onArchive }: EventCardProps) {
  const link = event.guestLink || buildGuestLink(event.slug);

  return (
    <article className={`admin-event-card${event.archived ? ' is-archived' : ''}`}>
      <div className="admin-event-card__top">
        <div className="admin-event-card__identity">
          <h3 className="admin-event-card__name">{event.name}</h3>
          <p className="admin-event-card__subtitle">{event.subtitle}</p>
        </div>
        <StatusBadge status={event.status} />
      </div>

      <div className="admin-event-card__meta">
        <span>Host: {event.hostName}</span>
        <span>Date: {event.eventDate}</span>
        <span>Uploads: {event.totalUploads}</span>
      </div>

      <div className="admin-event-card__link">
        <span className="admin-event-card__link-label">Guest link</span>
        <span className="admin-event-card__link-value">{link}</span>
      </div>

      <div className="admin-event-card__actions">
        {event.status !== 'live' && (
          <button
            type="button"
            className="admin-event-card__btn is-live"
            onClick={() => onStatusChange(event.id, 'live')}
          >
            Set Live
          </button>
        )}
        {event.status !== 'ended' && (
          <button
            type="button"
            className="admin-event-card__btn is-end"
            onClick={() => onStatusChange(event.id, 'ended')}
          >
            End
          </button>
        )}
        {!event.archived && (
          <button
            type="button"
            className="admin-event-card__btn is-archive"
            onClick={() => onArchive(event.id)}
          >
            Archive
          </button>
        )}
      </div>
    </article>
  );
}
