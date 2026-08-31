// ============================================================
// Lentis Gallery — Admin Events Page
// ============================================================
// Shows ALL events (active, ended, archived) with full status
// management. The admin can set events live, end them, or
// archive them from this page.
// ============================================================

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import EventCard from '../../components/admin/EventCard';
import ConfirmDialog from '../../components/host/ConfirmDialog';
import {
  getEvents,
  updateEventStatus,
  archiveEvent,
} from '../../services/mockAdminService';
import type { Event, EventStatus } from '../../types/event';

/** Filter tabs for the events list. */
type FilterTab = 'all' | 'upcoming' | 'live' | 'ended';

const TABS: { value: FilterTab; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'live', label: 'Live' },
  { value: 'ended', label: 'Ended' },
];

export default function AdminEventsPage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<FilterTab>('all');
  const [events, setEvents] = useState<Event[]>([]);
  const [archiveTarget, setArchiveTarget] = useState<Event | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const result = await getEvents(true);
      setEvents(result);
    } catch (err) {
      console.error('Failed to load events:', err);
    }
  };

  /** Filter events based on selected tab. */
  const filteredEvents = events.filter((e) => {
    if (filter === 'all') return true;
    if (filter === 'upcoming') return (e.status === 'draft' || e.status === 'not_started') && !e.archived;
    return e.status === filter && !e.archived;
  });

  /** Update an event's status and refresh the list. */
  const handleStatus = async (id: string, status: EventStatus) => {
    await updateEventStatus(id, status);
    loadData();
  };

  /** Confirm archive action. */
  const confirmArchive = async () => {
    if (!archiveTarget) return;
    await archiveEvent(archiveTarget.id);
    loadData();
    setArchiveTarget(null);
  };

  /** Count events per status. */
  const counts = {
    all: events.filter((e) => !e.archived).length,
    upcoming: events.filter((e) => (e.status === 'draft' || e.status === 'not_started') && !e.archived).length,
    live: events.filter((e) => e.status === 'live' && !e.archived).length,
    ended: events.filter((e) => e.status === 'ended' && !e.archived).length,
  };

  return (
    <AdminLayout title="Events">
      <div className="admin-overview">
        <header className="admin-overview__header">
          <div>
            <p className="admin-overview__eyebrow">Event Management</p>
            <h1 className="admin-overview__title">All Events</h1>
          </div>
        </header>

        {/* Filter tabs */}
        <div className="admin-events__tabs" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              role="tab"
              aria-selected={filter === tab.value}
              className={`admin-events__tab${filter === tab.value ? ' is-active' : ''}`}
              onClick={() => setFilter(tab.value)}
            >
              {tab.label}
              <span className="admin-events__tab-count">
                {counts[tab.value]}
              </span>
            </button>
          ))}
        </div>

        {/* Events list */}
        {filteredEvents.length === 0 ? (
          <p className="admin-overview__empty">
            No events match this filter.
          </p>
        ) : (
          <div className="admin-overview__event-list">
{filteredEvents.map((e) => (
                <EventCard
                  key={e.id}
                  event={e}
                  onStatusChange={handleStatus}
                  onArchive={(id) => {
                    const target = events.find((x) => x.id === id);
                    if (target) setArchiveTarget(target);
                  }}
                  onEdit={(id) => navigate(`/admin/console/events/${id}/edit`)}
                  onViewHostConsole={(slug) => navigate(`/e/${slug}/host`)}
                />
              ))}
          </div>
        )}
      </div>

      {/* Confirm archive dialog */}
      <ConfirmDialog
        open={archiveTarget !== null}
        title="Archive this event?"
        message={
          archiveTarget
            ? `"${archiveTarget.name}" will be archived and hidden from the active event list. You can restore it later from the Archive page.`
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
