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
import EventCountdown from '../EventCountdown';

interface EventCardProps {
  event: Event;
  /** Called when the event status changes. */
  onStatusChange: (id: string, status: EventStatus) => void;
  /** Called when the event is archived. */
  onArchive: (id: string) => void;
  /** Called when the event is permanently deleted. */
  onDelete?: (id: string) => void;
  /** Called when the user wants to edit the event. */
  onEdit: (id: string) => void;
  /** Called when the user wants to view the host console for this event. */
  onViewHostConsole?: (slug: string) => void;
}

/**
 * Admin-facing event card with lifecycle controls.
 */
export default function EventCard({ event, onStatusChange, onArchive, onDelete, onEdit, onViewHostConsole }: EventCardProps) {
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

      {/* Slideshow preview — shows first image if available */}
      {event.slides.length > 0 && (
        <div className="admin-event-card__slides">
          {event.slides.slice(0, 4).map((slide, i) => (
            <img key={i} src={slide.src} alt={slide.alt} className="admin-event-card__slide-thumb" loading="lazy" />
          ))}
          {event.slides.length > 4 && (
            <span className="admin-event-card__slide-more">+{event.slides.length - 4}</span>
          )}
        </div>
      )}

      <div className="admin-event-card__meta">
        <span>Host: {event.hostName}</span>
        <span>Date: {event.eventDate}</span>
        <span>Uploads: {event.totalUploads}</span>
      </div>

      {/* Countdown timer */}
      {!event.archived && (
        <EventCountdown
          eventDate={event.eventDate}
          status={event.status}
          compact
          className="admin-event-card__countdown"
        />
      )}

      <div className="admin-event-card__link">
        <span className="admin-event-card__link-label">Guest link</span>
        <span className="admin-event-card__link-value">{link}</span>
      </div>

      <div className="admin-event-card__actions">
        <button
          type="button"
          className="admin-event-card__btn is-edit"
          onClick={() => onEdit(event.id)}
        >
          Edit
        </button>
        {onViewHostConsole && (
          <button
            type="button"
            className="admin-event-card__btn is-host-console"
            onClick={() => onViewHostConsole(event.slug)}
          >
            View Host Console
          </button>
        )}
        {event.status !== 'live' && (
          <button
            type="button"
            className="admin-event-card__btn is-live"
            onClick={() => onStatusChange(event.id, 'live')}
          >
            {event.status === 'not_started' ? 'Start Event' : 'Set Live'}
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
        {onDelete && (
          <button
            type="button"
            className="admin-event-card__btn is-delete"
            onClick={() => onDelete(event.id)}
          >
            Delete
          </button>
        )}
      </div>
    </article>
  );
}
