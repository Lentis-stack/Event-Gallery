// ============================================================
// Lentis Gallery — Host Gallery Page
// ------------------------------------------------------------
// Full gallery management for the assigned event.
// Supports:
//   - Grid / list view toggle
//   - Filter by status (all / approved / pending / hidden)
//   - Search by guest name or caption
//   - Sort by newest / oldest
//   - Approve / hide / delete actions (with confirm dialog)
//
// Data is provided by the mock host service (frontend-only).
// ============================================================

import { useMemo, useState, useEffect } from 'react';
import HostLayout from '../../components/host/HostLayout';
import GalleryMediaCard from '../../components/host/GalleryMediaCard';
import ConfirmDialog from '../../components/host/ConfirmDialog';
import {
  getAssignedEvent,
  getGalleryMedia,
  setMediaStatus,
  deleteMedia,
} from '../../services/mockHostService';
import type { Event } from '../../types/event';
import type { GalleryMedia, MediaStatus } from '../../types/gallery';

type FilterStatus = 'all' | MediaStatus;
type ViewMode = 'grid' | 'list';
type SortOrder = 'newest' | 'oldest';

const EMPTY_EVENT: Event = { id: '', slug: '', name: 'Loading...', subtitle: '', hostName: '', hostEmail: '', eventDate: '', status: 'draft', theme: 'gold', slides: [], totalUploads: 0, photoCount: 0, videoCount: 0, contributingGuests: 0, storageUsedMb: 0, guestLink: '', archived: false };

export default function HostGalleryPage() {
  const [event, setEvent] = useState<Event>(EMPTY_EVENT);
  const [media, setMedia] = useState<GalleryMedia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getAssignedEvent(), getGalleryMedia()])
      .then(([e, m]) => {
        if (cancelled) return;
        setEvent(e);
        setMedia(m);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.message || 'Failed to load gallery. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);
  const [view, setView] = useState<ViewMode>('grid');
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortOrder>('newest');
  const [deleteTarget, setDeleteTarget] = useState<GalleryMedia | null>(null);

  const filtered = useMemo(() => {
    let list = [...media];

    // Filter by status
    if (filter !== 'all') {
      list = list.filter((m) => m.status === filter);
    }

    // Search by guest name or caption
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (m) =>
          m.guestName.toLowerCase().includes(q) ||
          (m.caption ?? '').toLowerCase().includes(q)
      );
    }

    // Sort: assume uploadedAt strings are human-readable ("12m ago").
    // For a real app this would be an ISO timestamp. Mock keeps display order.
    if (sort === 'oldest') {
      list = [...list].reverse();
    }

    return list;
  }, [media, filter, search, sort]);

  const handleStatus = async (id: string, status: MediaStatus) => {
    setMedia(await setMediaStatus(id, status));
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setMedia(await deleteMedia(deleteTarget.id));
    setDeleteTarget(null);
  };

  const counts = {
    all: media.length,
    approved: media.filter((m) => m.status === 'approved').length,
    pending: media.filter((m) => m.status === 'pending').length,
    hidden: media.filter((m) => m.status === 'hidden').length,
  };

  return (
    <HostLayout event={event}>
      <div className="host-gallery">
        <header className="host-gallery__header">
          <div>
            <p className="host-gallery__eyebrow">Gallery Management</p>
            <h1 className="host-gallery__title">Memories</h1>
          </div>
          {!loading && !error && (
            <div className="host-gallery__view-toggle" role="group" aria-label="View mode">
              <button
                type="button"
                className={`host-gallery__view-btn${view === 'grid' ? ' is-active' : ''}`}
                onClick={() => setView('grid')}
                aria-pressed={view === 'grid'}
              >
                Grid
              </button>
              <button
                type="button"
                className={`host-gallery__view-btn${view === 'list' ? ' is-active' : ''}`}
                onClick={() => setView('list')}
                aria-pressed={view === 'list'}
              >
                List
              </button>
            </div>
          )}
        </header>

        {/* Loading state */}
        {loading && (
          <div className="host-gallery__loading">
            <div className="host-gallery__spinner" />
            <p>Loading gallery…</p>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="host-gallery__error">
            <p>{error}</p>
            <button type="button" className="btn-primary" onClick={() => {
              setLoading(true);
              setError(null);
              Promise.all([getAssignedEvent(), getGalleryMedia()])
                .then(([e, m]) => { setEvent(e); setMedia(m); })
                .catch((err) => setError(err?.message || 'Failed to load gallery.'))
                .finally(() => setLoading(false));
            }}>
              Retry
            </button>
          </div>
        )}

        {/* Controls */}
        {!loading && !error && (
        <div className="host-gallery__controls">
          <input
            type="search"
            className="guest-form__input host-gallery__search"
            placeholder="Search by guest or caption…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search gallery"
          />

          <div className="host-gallery__filters" role="group" aria-label="Filter by status">
            {(['all', 'approved', 'pending', 'hidden'] as FilterStatus[]).map((f) => (
              <button
                key={f}
                type="button"
                className={`host-gallery__filter${filter === f ? ' is-active' : ''}`}
                onClick={() => setFilter(f)}
                aria-pressed={filter === f}
              >
                {f === 'all' ? 'All' : f[0].toUpperCase() + f.slice(1)}
                <span className="host-gallery__count">{counts[f]}</span>
              </button>
            ))}
          </div>

          <label className="host-gallery__sort">
            <span className="sr-only">Sort</span>
            <select
              className="guest-form__input host-gallery__sort-select"
              value={sort}
              onChange={(e) => setSort(e.target.value as SortOrder)}
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
        </div>
        )}

        {/* Grid / List */}
        {!loading && !error && (
          filtered.length === 0 ? (
            <p className="host-gallery__empty">
              No guest memories yet. Share your event link to get started.
            </p>
          ) : (
            <div className={`host-gallery__items host-gallery__items--${view}`}>
              {filtered.map((m) => (
                <GalleryMediaCard
                  key={m.id}
                  media={m}
                  onStatusChange={handleStatus}
                  onDelete={(id) => {
                    const target = media.find((x) => x.id === id);
                    if (target) setDeleteTarget(target);
                  }}
                />
              ))}
            </div>
          )
        )}
      </div>

      {/* Confirm delete dialog */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete this memory?"
        message={
          deleteTarget
            ? `This will permanently remove ${deleteTarget.guestName}'s ${
                deleteTarget.type === 'video' ? 'video' : 'photo'
              } from the gallery. This cannot be undone.`
            : ''
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        destructive
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </HostLayout>
  );
}
