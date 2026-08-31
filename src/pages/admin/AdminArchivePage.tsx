// ============================================================
// Lentis Gallery — Admin Archive Page
// ============================================================
// Shows archived events with restore and permanent delete actions.
// Permanent delete is irreversible and includes R2 storage cleanup.
// ============================================================

import { useState, useEffect } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import ConfirmDialog from '../../components/host/ConfirmDialog';
import {
  listEvents,
  restoreEvent,
  permanentDeleteEvent,
  toFrontendEvent,
} from '../../services/api';
import type { Event } from '../../types/event';

export default function AdminArchivePage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Event | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<Event | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const backendEvents = await listEvents();
      const archived = backendEvents
        .filter((be) => be.status === 'ARCHIVED')
        .map((be) => toFrontendEvent(be));
      setEvents(archived);
    } catch (err: any) {
      setError(err.message || 'Failed to load archived events.');
    } finally {
      setLoading(false);
    }
  };

  const confirmPermanentDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setError(null);
    try {
      await permanentDeleteEvent(deleteTarget.id);
      setEvents((prev) => prev.filter((e) => e.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.message || 'Failed to delete event.');
    } finally {
      setDeleting(false);
    }
  };

  const confirmRestore = async () => {
    if (!restoreTarget) return;
    setRestoring(true);
    setError(null);
    try {
      await restoreEvent(restoreTarget.id);
      setEvents((prev) => prev.filter((e) => e.id !== restoreTarget.id));
      setRestoreTarget(null);
    } catch (err: any) {
      setError(err.message || 'Failed to restore event.');
    } finally {
      setRestoring(false);
    }
  };

  return (
    <AdminLayout title="Archive">
      <div className="admin-overview">
        <header className="admin-overview__header">
          <div>
            <p className="admin-overview__eyebrow">Archived Events</p>
            <h1 className="admin-overview__title">Event Archive</h1>
            <p style={{ color: 'var(--ink-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
              Archived events are hidden from the active list. Restore or permanently delete them.
            </p>
          </div>
        </header>

        {error && (
          <div style={{
            padding: '0.75rem 1rem',
            borderRadius: '12px',
            background: 'rgba(201, 138, 138, 0.12)',
            border: '1px solid rgba(201, 138, 138, 0.3)',
            color: '#c98a8a',
            fontSize: '0.85rem',
          }}>
            {error}
          </div>
        )}

        {loading ? (
          <p className="admin-overview__empty">Loading...</p>
        ) : events.length === 0 ? (
          <p className="admin-overview__empty">No archived events.</p>
        ) : (
          <div className="admin-overview__event-list">
            {events.map((e) => (
              <article key={e.id} className="admin-event-card is-archived">
                <div className="admin-event-card__top">
                  <div className="admin-event-card__identity">
                    <h3 className="admin-event-card__name">{e.name}</h3>
                    <p className="admin-event-card__subtitle">{e.subtitle}</p>
                  </div>
                  <span className="status-badge status-badge--archived">Archived</span>
                </div>

                <div className="admin-event-card__meta">
                  <span>Host: {e.hostName}</span>
                  <span>Date: {e.eventDate}</span>
                  <span>Uploads: {e.totalUploads}</span>
                </div>

                <div className="admin-event-card__actions">
                  <button
                    type="button"
                    className="admin-event-card__btn is-live"
                    onClick={() => setRestoreTarget(e)}
                    disabled={restoring || deleting}
                  >
                    Restore
                  </button>
                  <button
                    type="button"
                    className="admin-event-card__btn is-delete"
                    onClick={() => setDeleteTarget(e)}
                    disabled={restoring || deleting}
                  >
                    Permanent Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      {/* Confirm restore dialog */}
      <ConfirmDialog
        open={restoreTarget !== null}
        title="Restore this event?"
        message={
          restoreTarget
            ? `"${restoreTarget.name}" will be restored to the active event list with status "Created". The host can then start it.`
            : ''
        }
        confirmLabel={restoring ? 'Restoring...' : 'Restore'}
        cancelLabel="Cancel"
        onConfirm={confirmRestore}
        onCancel={() => setRestoreTarget(null)}
      />

      {/* Confirm permanent delete dialog */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Permanently delete this event?"
        message={
          deleteTarget
            ? `"${deleteTarget.name}" and ALL its media, guests, and data will be permanently deleted. This action CANNOT be undone.`
            : ''
        }
        confirmLabel={deleting ? 'Deleting...' : 'Delete Forever'}
        cancelLabel="Cancel"
        destructive
        onConfirm={confirmPermanentDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </AdminLayout>
  );
}
