// ============================================================
// Lentis Gallery — Host Overview Page
// ------------------------------------------------------------
// The landing page of the Event Host Console. Shows summary
// stat cards, recent guest memories with quick moderation,
// and a quick actions row.
// ============================================================

import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import HostLayout from '../../components/host/HostLayout';
import StatCard from '../../components/host/StatCard';
import StatusBadge from '../../components/host/StatusBadge';
import ConfirmDialog from '../../components/host/ConfirmDialog';
import EventCountdown from '../../components/EventCountdown';
import { reloadAssignedEvent, getGalleryMedia, setMediaStatus, startEvent, endEvent, autoApproveAll, setTargetEventSlug } from '../../services/mockHostService';
import { getHostOverview, type HostOverviewStats } from '../../services/api';
import type { MediaStatus } from '../../types/gallery';
import type { Event } from '../../types/event';
import type { HostDashboardSummary } from '../../types/dashboard';
import type { GalleryMedia } from '../../types/gallery';

export default function HostOverviewPage() {
  const location = useLocation();
  const [event, setEventState] = useState<Event>({ id: '', slug: '', name: 'Loading...', subtitle: '', hostName: '', hostEmail: '', eventDate: '', status: 'not_started', theme: 'gold', slides: [], totalUploads: 0, photoCount: 0, videoCount: 0, contributingGuests: 0, storageUsedMb: 0, guestLink: '', archived: false });
  const [summary, setSummary] = useState<HostDashboardSummary>({ totalUploads: 0, photoCount: 0, videoCount: 0, contributingGuests: 0, storageUsedMb: 0, storageIsEstimate: true });
  const [media, setMedia] = useState<GalleryMedia[]>([]);
  const [approveAllOpen, setApproveAllOpen] = useState(false);
  const [approveAllCount, setApproveAllCount] = useState(0);
  const [overview, setOverview] = useState<HostOverviewStats | null>(null);

  const handleAutoApprove = async () => {
    if (!event?.id) return;
    try {
      const result = await autoApproveAll();
      setMedia(result);
      // Refresh overview after bulk approval
      if (event.id) {
        const overviewData = await getHostOverview(event.id);
        setOverview(overviewData);
        setSummary({
          totalUploads: overviewData.total_uploads,
          photoCount: overviewData.photos,
          videoCount: overviewData.videos,
          contributingGuests: overviewData.contributing_guests,
          storageUsedMb: Math.round(overviewData.storage_bytes / (1024 * 1024)),
          storageIsEstimate: false,
        });
      }
    } catch (err: any) {
      console.error('Failed to auto-approve:', err);
    }
  };

  useEffect(() => {
    // If navigated from event-specific host login, set the target slug
    const state = location.state as { eventSlug?: string } | null;
    if (state?.eventSlug) {
      setTargetEventSlug(state.eventSlug);
    }
    loadData();
  }, [event.slug]);

  const loadData = async () => {
    try {
      const [eventResult, mediaResult] = await Promise.all([
        reloadAssignedEvent(),
        getGalleryMedia(),
      ]);
      setEventState(eventResult);
      setMedia(mediaResult);

      // Load overview statistics
      if (eventResult.id) {
        const overviewData = await getHostOverview(eventResult.id);
        setOverview(overviewData);
        // Update summary with real data
        setSummary({
          totalUploads: overviewData.total_uploads,
          photoCount: overviewData.photos,
          videoCount: overviewData.videos,
          contributingGuests: overviewData.contributing_guests,
          storageUsedMb: Math.round(overviewData.storage_bytes / (1024 * 1024)),
          storageIsEstimate: false,
        });
      }
    } catch (err) {
      console.error('Failed to load host data:', err);
    }
  };

  const handleStartEvent = async () => {
    const updated = await startEvent();
    setEventState(updated);
    // Refresh overview after status change
    if (updated.id) {
      const overviewData = await getHostOverview(updated.id);
      setOverview(overviewData);
      setSummary({
        totalUploads: overviewData.total_uploads,
        photoCount: overviewData.photos,
        videoCount: overviewData.videos,
        contributingGuests: overviewData.contributing_guests,
        storageUsedMb: Math.round(overviewData.storage_bytes / (1024 * 1024)),
        storageIsEstimate: false,
      });
    }
  };

  const handleEndEvent = async () => {
    const updated = await endEvent();
    setEventState(updated);
    // Refresh overview after status change
    if (updated.id) {
      const overviewData = await getHostOverview(updated.id);
      setOverview(overviewData);
      setSummary({
        totalUploads: overviewData.total_uploads,
        photoCount: overviewData.photos,
        videoCount: overviewData.videos,
        contributingGuests: overviewData.contributing_guests,
        storageUsedMb: Math.round(overviewData.storage_bytes / (1024 * 1024)),
        storageIsEstimate: false,
      });
    }
  };

  const handleStatus = async (id: string, status: MediaStatus) => {
    setMedia(await setMediaStatus(id, status));
    // Refresh overview after status change
    if (event.id) {
      const overviewData = await getHostOverview(event.id);
      setOverview(overviewData);
    }
  };

  // Recent memories from overview API (newest first, up to 6)
  const recent = overview?.recent_memories || [];

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

        {/* Countdown timer */}
        {!event.archived && (
          <EventCountdown
            eventDate={event.eventDate}
            status={event.status}
            className="host-overview__countdown"
          />
        )}

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

        {/* Event lifecycle controls */}
        <section className="host-overview__lifecycle" aria-label="Event lifecycle">
          <div className="host-overview__lifecycle-header">
            <h2 className="host-overview__section-title">Event Controls</h2>
            <StatusBadge status={event.status} />
          </div>
          <div className="host-overview__lifecycle-actions">
            {event.status === 'not_started' && (
              <button type="button" className="btn-primary" onClick={handleStartEvent}>
                ▶ Start Event
              </button>
            )}
            {event.status === 'live' && (
              <button type="button" className="btn-ghost" onClick={handleEndEvent} style={{ borderColor: '#c98a8a', color: '#c98a8a' }}>
                ⏹ End Event
              </button>
            )}
            {event.status === 'ended' && (
              <span className="host-overview__ended-note">This event has ended. No new uploads accepted.</span>
            )}
          </div>
        </section>

        {/* Quick actions */}
        <section className="host-overview__actions" aria-label="Quick actions">
          <Link to="/host/console/gallery" className="btn-primary">Manage Gallery</Link>
          <Link to="/host/console/share" className="btn-ghost">Share Event</Link>
          {event.status === 'live' && (
            <>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => {
                  setApproveAllCount(
                    media.filter((m) => m.status === 'pending').length
                  );
                  setApproveAllOpen(true);
                }}
              >
                ✓ Approve All Media
              </button>
              <ConfirmDialog
                open={approveAllOpen}
                title="Approve all pending guest media?"
                message={
                  approveAllCount > 0
                    ? `This will approve ${approveAllCount} pending photo${approveAllCount === 1 ? '' : 's'}/video${approveAllCount === 1 ? '' : 's'} for your event.`
                    : 'No pending guest media to approve.'
                }
                confirmLabel={approveAllCount > 0 ? 'Approve All' : 'OK'}
                cancelLabel="Cancel"
                destructive={approveAllCount > 0}
                onConfirm={handleAutoApprove}
                onCancel={() => setApproveAllOpen(false)}
              />
            </>
          )}
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
                    {m.media_type === 'VIDEO' ? (
                      <video src={m.media_url} muted playsInline />
                    ) : (
                      <img src={m.media_url} alt={`${m.guest_name}'s photo`} loading="lazy" />
                    )}
                  </div>
                  <div className="host-overview__recent-info">
                    <span className="host-overview__recent-name">{m.guest_name}</span>
                    <span className="host-overview__recent-time">{new Date(m.created_at).toLocaleString()}</span>
                  </div>
                  <div className="host-overview__recent-actions">
                    <button
                      type="button"
                      className="host-overview__mini-btn is-approve"
                      onClick={() => handleStatus(m.id, 'approved')}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="host-overview__mini-btn is-hide"
                      onClick={() => handleStatus(m.id, 'hidden')}
                    >
                      Hide
                    </button>
                    <StatusBadge status="approved" />
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
