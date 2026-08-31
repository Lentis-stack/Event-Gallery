// ============================================================
// Lentis Gallery — Host Archive & Export Page
// ------------------------------------------------------------
// After an event ends, the Event Host prepares all APPROVED
// media for future transfer to Google Photos or Dropbox.
//
// This phase is FRONTEND-ONLY. No real connection, transfer,
// authentication, API call, cloud storage, or account linking
// is performed. The destination cards and buttons are clearly
// marked as mock/disabled.
//
// FUTURE BACKEND (real export system) requires:
//   1. Secure Python backend (FastAPI/Django).
//   2. OAuth account connection + encrypted token storage.
//   3. Background export jobs with progress & error tracking.
//   4. Permission checks so each host can only export their own
//      event media.
// ============================================================

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import HostLayout from '../../components/host/HostLayout';
import ConfirmDialog from '../../components/host/ConfirmDialog';
import StatusBadge from '../../components/host/StatusBadge';
import {
  getAssignedEvent,
  updateAssignedEvent,
  getExportSummary,
  getExportHistory,
  prepareExport,
} from '../../services/mockHostService';
import type { Event } from '../../types/event';
import type { ExportHistoryRecord, ExportSummary } from '../../types/dashboard';

/** A single export destination card (Google Photos / Dropbox). */
interface DestinationInfo {
  key: string;
  name: string;
  blurb: string;
}

// Static destination descriptions — no SDKs or API keys are used.
const DESTINATIONS: DestinationInfo[] = [
  {
    key: 'google-photos',
    name: 'Google Photos',
    blurb:
      'After the event, your approved photos and videos can be copied to your Google Photos library.',
  },
  {
    key: 'dropbox',
    name: 'Dropbox',
    blurb:
      'After the event, your approved media can be exported to a Dropbox folder for easy sharing and backup.',
  },
];

const EMPTY_EVENT: Event = { id: '', slug: '', name: 'Loading...', subtitle: '', hostName: '', hostEmail: '', eventDate: '', status: 'draft', theme: 'gold', slides: [], totalUploads: 0, photoCount: 0, videoCount: 0, contributingGuests: 0, storageUsedMb: 0, guestLink: '', archived: false };

export default function HostExportPage() {
  const [event, setEvent] = useState<Event>(EMPTY_EVENT);
  const [summary, setSummary] = useState<ExportSummary>({ photoCount: 0, videoCount: 0, totalFileCount: 0, estimatedSizeMb: 0 });
  const [destinations] = useState<DestinationInfo[]>(DESTINATIONS);
  const [history, setHistory] = useState<ExportHistoryRecord[]>([]);
  const [preparing, setPreparing] = useState(false);
  const [prepared, setPrepared] = useState(false);
  const [confirmComplete, setConfirmComplete] = useState(false);

  useEffect(() => {
    Promise.all([getAssignedEvent(), getExportSummary(), getExportHistory()]).then(([e, s, h]) => {
      setEvent(e);
      setSummary(s);
      setHistory(h);
    });
  }, []);

  // Whether the event is still live (so the "Event Complete" action matters).
  const isLive = event.status === 'live';

  // Changing the event from Live to Ended requires explicit confirmation.
  const handleMarkComplete = async () => {
    setEvent(await updateAssignedEvent({ status: 'ended' }));
    setConfirmComplete(false);
  };

  // Frontend-only "Prepare Export" — adds a mock history record.
  const handlePrepare = () => {
    setPreparing(true);
    // Simulate a short async preparation step for a polished feel.
    window.setTimeout(() => {
      setHistory(prepareExport());
      setPreparing(false);
      setPrepared(true);
    }, 900);
  };

  return (
    <HostLayout event={event}>
      <div className="host-export">
        <header className="host-export__header">
          <div>
            <p className="host-export__eyebrow">Archive &amp; Export</p>
            <h1 className="host-export__title">Prepare Event Media</h1>
            <p className="host-export__subtitle">
              After the event ends, prepare all approved media for transfer to a cloud destination.
            </p>
          </div>
          <StatusBadge status={event.status} />
        </header>

        {/* Event completion */}
        <section className="host-export__status" aria-label="Event status">
          <div className="host-export__status-info">
            <p className="host-export__label">Current Event Status</p>
            <p className="host-export__status-value">
              {isLive ? 'Your event is live and collecting memories.' : 'This event has ended.'}
            </p>
          </div>
          {isLive && (
            <button
              type="button"
              className="btn-ghost host-export__complete-btn"
              onClick={() => setConfirmComplete(true)}
            >
              Mark Event Complete
            </button>
          )}
        </section>

        {/* Export summary — computed from approved media only */}
        <section className="host-export__summary" aria-label="Export summary">
          <div className="host-export__section-head">
            <h2 className="host-export__section-title">Export Summary</h2>
            <span className="host-export__only-approved">Approved media only</span>
          </div>
          <div className="host-export__cards">
            <div className="stat-card host-export__stat">
              <div className="stat-card__value">{summary.photoCount}</div>
              <div className="stat-card__label">Photos</div>
            </div>
            <div className="stat-card host-export__stat">
              <div className="stat-card__value">{summary.videoCount}</div>
              <div className="stat-card__label">Videos</div>
            </div>
            <div className="stat-card host-export__stat">
              <div className="stat-card__value">{summary.totalFileCount}</div>
              <div className="stat-card__label">Total Files</div>
            </div>
            <div className="stat-card stat-card--accent host-export__stat">
              <div className="stat-card__value">{summary.estimatedSizeMb} MB</div>
              <div className="stat-card__label">Est. Size</div>
              <div className="stat-card__hint">estimate</div>
            </div>
          </div>
        </section>

        {/* Destination cards */}
        <section className="host-export__destinations" aria-label="Export destinations">
          <div className="host-export__section-head">
            <h2 className="host-export__section-title">Choose a Destination</h2>
          </div>
          <div className="host-export__dest-grid">
            {destinations.map((dest) => (
              <div key={dest.key} className="host-export__dest-card">
                <div className="host-export__dest-top">
                  <div className="host-export__dest-icon" aria-hidden="true">
                    {dest.name === 'Google Photos' ? (
                      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.2">
                        <rect x="3" y="3" width="18" height="18" rx="3" />
                        <circle cx="9" cy="9" r="2" />
                        <path d="M21 15l-5-5-9 9" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.2">
                        <path d="M12 3v12" />
                        <path d="M7 10l5 5 5-5" />
                        <path d="M5 21h14" />
                      </svg>
                    )}
                  </div>
                  <h3 className="host-export__dest-name">{dest.name}</h3>
                </div>
                <p className="host-export__dest-blurb">{dest.blurb}</p>
                <p className="host-export__dest-pending">
                  Secure account connection and real transfer will be available once the backend is built.
                </p>
                <button type="button" className="host-export__mock-btn" disabled>
                  Connect {dest.name}
                </button>
              </div>
            ))}
          </div>

          {/* Mock prepare action */}
          <div className="host-export__prepare">
            <p className="host-export__prepare-note">
              Export destination connections are mock/disabled for now. You can still prepare the export
              summary to see how the workflow will feel.
            </p>
            <button
              type="button"
              className="btn-primary"
              onClick={handlePrepare}
              disabled={preparing || prepared}
            >
              {preparing ? 'Preparing…' : prepared ? 'Export Prepared ✓' : 'Prepare Export'}
            </button>
          </div>

          {/* Polished success state on activation */}
          <AnimatePresence>
            {prepared && (
              <motion.div
                className="host-export__success"
                role="status"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              >
                <div className="host-export__success-icon" aria-hidden="true">✓</div>
                <div>
                  <h3 className="host-export__success-title">Your export has been prepared.</h3>
                  <p className="host-export__success-text">
                    Real transfer will be connected when the secure backend is added.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Mock export history */}
        <section className="host-export__history" aria-label="Export history">
          <div className="host-export__section-head">
            <h2 className="host-export__section-title">Export History</h2>
          </div>
          {history.length === 0 ? (
            <p className="host-export__empty">No exports have been prepared yet.</p>
          ) : (
            <ul className="host-export__history-list">
              {history.map((record) => (
                <li key={record.id} className="host-export__history-item">
                  <div className="host-export__history-dest">{record.destination}</div>
                  <div className="host-export__history-meta">
                    <span className="host-export__history-date">{record.date}</span>
                    <span className="host-export__history-count">{record.mediaCount} files</span>
                  </div>
                  <span className={`host-export__history-status is-${record.status}`}>
                    {record.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Confirm before changing event from Live to Ended */}
      <ConfirmDialog
        open={confirmComplete}
        title="End this event?"
        message="This will change the event from Live to Ended. Guests will no longer be able to upload, and you can begin preparing the export. This can be changed later."
        confirmLabel="End Event"
        cancelLabel="Cancel"
        onConfirm={handleMarkComplete}
        onCancel={() => setConfirmComplete(false)}
      />
    </HostLayout>
  );
}
