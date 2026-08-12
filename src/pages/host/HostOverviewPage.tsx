// ============================================================
// Lentis Gallery — Host Overview Page
// ------------------------------------------------------------
// The landing page of the Event Host Console. Shows summary
// stat cards, recent guest memories with quick moderation,
// and a quick actions row.
//
// Data is provided by the mock host service (frontend-only).
// ============================================================

import { useState } from 'react';
import { Link } from 'react-router-dom';
import HostLayout from '../../components/host/HostLayout';
import StatCard from '../../components/host/StatCard';
import StatusBadge from '../../components/host/StatusBadge';
import { getAssignedEvent, getHostSummary, getGalleryMedia, setMediaStatus } from '../../services/mockHostService';
import type { MediaStatus } from '../../types/gallery';

export default function HostOverviewPage() {
  const [event] = useState(() => getAssignedEvent());
  const [summary] = useState(() => getHostSummary());
  const [media, setMedia] = useState(() => getGalleryMedia());

  // Recent memories = first 3 pending items (or any items if none pending).
  const recent = media.slice(0, 3);

  const handleStatus = (id: string, status: MediaStatus) => {
    setMedia(setMediaStatus(id, status));
  };

  return (
    <HostLayout event={event}>
      <div className="host-overview">
        <header className="host-overview__header">
          <div>
            <p className="host-overview__eyebrow">Event Overview</p>
            <h1 className="host-overview__title">{event.name}</h1>
            <p className="host-overview__subtitle">{event.subtitle}</p>
          </div>
          <StatusBadge status={event.status} />
        </header>

        {/* Summary cards */}
        <section className="host-overview__stats" aria-label="Event summary">
          <StatCard label="Total Uploads" value={summary.totalUploads} accent />
          <StatCard label="Photos" value={summary.photoCount} />
          <StatCard label="Videos" value={summary.videoCount} />
          <StatCard
            label="Storage"
            value={`${summary.storageUsedMb} MB`}
            hint={summary.storageIsEstimate ? 'estimate' : undefined}
          />
        </section>

        {/* Quick actions */}
        <section className="host-overview__actions" aria-label="Quick actions">
          <Link to="/host/console/gallery" className="btn-primary">Manage Gallery</Link>
          <Link to="/host/console/share" className="btn-ghost">Share Event</Link>
          <Link to="/host/console/slideshow" className="btn-ghost">Start Live</Link>
        </section>

        {/* Recent memories */}
        <section className="host-overview__recent" aria-label="Recent memories">
          <div className="host-overview__section-head">
            <h2 className="host-overview__section-title">Recent Memories</h2>
            <Link to="/host/console/gallery" className="host-overview__view-all">View all</Link>
          </div>

          {recent.length === 0 ? (
            <p className="host-overview__empty">No memories yet. Share your event link to get started.</p>
          ) : (
            <ul className="host-overview__recent-list">
              {recent.map((m) => (
                <li key={m.id} className="host-overview__recent-item">
                  <div className="host-overview__recent-thumb">
                    {m.type === 'video' ? (
                      <video src={m.src} muted playsInline />
                    ) : (
                      <img src={m.src} alt={m.caption ?? `${m.guestName}'s photo`} loading="lazy" />
                    )}
                  </div>
                  <div className="host-overview__recent-info">
                    <span className="host-overview__recent-name">{m.guestName}</span>
                    <span className="host-overview__recent-time">{m.uploadedAt}</span>
                  </div>
                  <div className="host-overview__recent-actions">
                    {m.status !== 'approved' && (
                      <button
                        type="button"
                        className="host-overview__mini-btn is-approve"
                        onClick={() => handleStatus(m.id, 'approved')}
                      >
                        Approve
                      </button>
                    )}
                    {m.status !== 'hidden' && (
                      <button
                        type="button"
                        className="host-overview__mini-btn is-hide"
                        onClick={() => handleStatus(m.id, 'hidden')}
                      >
                        Hide
                      </button>
                    )}
                    <StatusBadge status={m.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </HostLayout>
  );
}
