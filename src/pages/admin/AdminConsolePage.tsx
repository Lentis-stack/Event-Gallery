// ============================================================
// Lentis Gallery — Admin Console Page
// ------------------------------------------------------------
// The main Lentis Admin Console. Shows:
//   - Platform overview summary cards
//   - Full event list with status management (set live / end)
//   - Archive action
//   - Host preview link for the live event
//
// Data is provided by the mock admin service (frontend-only).
// ============================================================

import { useState } from 'react';
import { Link } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import EventCard from '../../components/admin/EventCard';
import ConfirmDialog from '../../components/host/ConfirmDialog';
import {
  getAdminSummary,
  getEvents,
  updateEventStatus,
  archiveEvent,
} from '../../services/mockAdminService';
import type { Event, EventStatus } from '../../types/event';

export default function AdminConsolePage() {
  const [summary] = useState(() => getAdminSummary());
  const [events, setEvents] = useState<Event[]>(() => getEvents());
  const [archiveTarget, setArchiveTarget] = useState<Event | null>(null);

  const handleStatus = (id: string, status: EventStatus) => {
    updateEventStatus(id, status);
    setEvents(getEvents());
  };

  const confirmArchive = () => {
    if (!archiveTarget) return;
    archiveEvent(archiveTarget.id);
    setEvents(getEvents());
    setArchiveTarget(null);
  };

  const liveEvent = events.find((e) => e.status === 'live');

  return (
    <AdminLayout title="Overview">
      <div className="admin-overview">
        <header className="admin-overview__header">
          <div>
            <p className="admin-overview__eyebrow">Platform Overview</p>
            <h1 className="admin-overview__title">Lentis Admin</h1>
          </div>
        </header>

        {/* Summary cards */}
        <section className="admin-overview__stats" aria-label="Platform summary">
          <div className="stat-card stat-card--accent">
            <div className="stat-card__value">{summary.totalEvents}</div>
            <div className="stat-card__label">Total Events</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value">{summary.liveEvents}</div>
            <div className="stat-card__label">Live Now</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value">{summary.totalUploads}</div>
            <div className="stat-card__label">Total Uploads</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value">{summary.totalHosts}</div>
            <div className="stat-card__label">Hosts</div>
          </div>
        </section>

        {/* Live event host preview */}
        {liveEvent && (
          <section className="admin-overview__live" aria-label="Live event">
            <div className="admin-overview__live-info">
              <span className="admin-overview__live-label">Currently Live</span>
              <span className="admin-overview__live-name">{liveEvent.name}</span>
              <span className="admin-overview__live-host">Host: {liveEvent.hostName}</span>
            </div>
            <Link to="/host/console" className="btn-ghost admin-overview__live-btn">
              View Host Console
            </Link>
          </section>
        )}

        {/* Event list */}
        <section className="admin-overview__events" aria-label="All events">
          <div className="admin-overview__section-head">
            <h2 className="admin-overview__section-title">All Events</h2>
            <Link to="/admin/console/create" className="btn-primary admin-overview__new-btn">
              + New Event
            </Link>
          </div>

          {events.length === 0 ? (
            <p className="admin-overview__empty">No events yet. Create your first event.</p>
          ) : (
            <div className="admin-overview__event-list">
              {events.map((e) => (
                <EventCard
                  key={e.id}
                  event={e}
                  onStatusChange={handleStatus}
                  onArchive={(id) => {
                    const target = events.find((x) => x.id === id);
                    if (target) setArchiveTarget(target);
                  }}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Confirm archive dialog */}
      <ConfirmDialog
        open={archiveTarget !== null}
        title="Archive this event?"
        message={
          archiveTarget
            ? `"${archiveTarget.name}" will be archived and hidden from the active event list. You can still manage it from the archived view.`
            : ''
        }
        confirmLabel="Archive"
        cancelLabel="Cancel"
        destructive
        onConfirm={confirmArchive}
        onCancel={() => setArchiveTarget(null)}
      />
    </AdminLayout>
  );
}
