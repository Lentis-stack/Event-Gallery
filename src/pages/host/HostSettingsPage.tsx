// ============================================================
// Lentis Gallery — Host Settings Page
// ============================================================
// Lets the Host manage their event's visual presentation:
//   1. Theme selector
//   2. Landing page message editor
//   3. Visual media management (Hero, Slideshows)
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import HostLayout from '../../components/host/HostLayout';
import ConfirmDialog from '../../components/host/ConfirmDialog';
import {
  getAssignedEvent,
  updateAssignedEvent,
  getEventMediaByRole,
  uploadPresentationImage,
  updateMediaRoleAndPageLocal,
  deletePresentationMedia,
} from '../../services/mockHostService';
import type { Event, ThemeChoice, MediaRole, MediaPage } from '../../types/event';
import type { GalleryMedia } from '../../types/gallery';

// ============================================================
// Constants
// ============================================================

const THEME_OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: 'gold', label: 'Gold' },
  { value: 'blue', label: 'Blue' },
  { value: 'rose', label: 'Rose' },
  { value: 'emerald', label: 'Emerald' },
];

interface MediaCategory {
  key: string;
  label: string;
  description: string;
  role: MediaRole;
  page?: MediaPage;
}

const MEDIA_CATEGORIES: MediaCategory[] = [
  { key: 'hero', label: 'Hero Images', description: 'Displayed on the event landing page header.', role: 'HERO', page: 'LANDING' },
  { key: 'landing', label: 'Landing Page Slideshow', description: 'Rotating images on the public landing page.', role: 'SLIDESHOW', page: 'LANDING' },
  { key: 'guest', label: 'Guest Page Slideshow', description: 'Background slideshow on the guest registration page.', role: 'SLIDESHOW', page: 'GUEST' },
  { key: 'camera', label: 'Camera Page Slideshow', description: 'Background slideshow on the camera capture page.', role: 'SLIDESHOW', page: 'CAMERA' },
  { key: 'host', label: 'Host Page Slideshow', description: 'Background slideshow in the Host Console.', role: 'HOST_SLIDESHOW', page: 'HOST' },
];

const ALL_ROLES: { role: MediaRole; page?: MediaPage; label: string }[] = [
  { role: 'HERO', page: 'LANDING', label: 'Hero / Cover' },
  { role: 'SLIDESHOW', page: 'LANDING', label: 'Landing Slideshow' },
  { role: 'SLIDESHOW', page: 'GUEST', label: 'Guest Page Slideshow' },
  { role: 'SLIDESHOW', page: 'CAMERA', label: 'Camera Page Slideshow' },
  { role: 'HOST_SLIDESHOW', page: 'HOST', label: 'Host Page Slideshow' },
];

// ============================================================
// Component
// ============================================================

export default function HostSettingsPage() {
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);

  // Theme
  const [theme, setTheme] = useState<ThemeChoice>('gold');
  const [themeSaving, setThemeSaving] = useState(false);
  const [themeSaved, setThemeSaved] = useState(false);

  // Landing message
  const [landingMessage, setLandingMessage] = useState('');
  const [messageSaving, setMessageSaving] = useState(false);
  const [messageSaved, setMessageSaved] = useState(false);

  // Media per category
  const [mediaData, setMediaData] = useState<Record<string, GalleryMedia[]>>({});
  const [uploadStates, setUploadStates] = useState<Record<string, { uploading: boolean; error?: string }>>({});

  // Reassign modal
  const [reassignTarget, setReassignTarget] = useState<{ mediaId: string; currentRole: MediaRole; currentPage?: MediaPage } | null>(null);
  const [reassignRole, setReassignRole] = useState<MediaRole>('HERO');
  const [reassignPage, setReassignPage] = useState<MediaPage | undefined>('LANDING');

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<{ mediaId: string; label: string } | null>(null);

  // ============================================================
  // Load event
  // ============================================================

  const loadEvent = useCallback(async () => {
    try {
      const ev = await getAssignedEvent();
      setEvent(ev);
      setTheme(ev.theme);
      setLandingMessage(ev.landingMessage || '');
    } catch (err) {
      console.error('Failed to load event:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // ============================================================
  // Load media for all categories
  // ============================================================

  const loadAllMedia = useCallback(async () => {
    const results: Record<string, GalleryMedia[]> = {};
    for (const cat of MEDIA_CATEGORIES) {
      try {
        results[cat.key] = await getEventMediaByRole(cat.role, cat.page);
      } catch {
        results[cat.key] = [];
      }
    }
    setMediaData(results);
  }, []);

  useEffect(() => {
    loadEvent();
  }, [loadEvent]);

  useEffect(() => {
    if (event?.id) {
      loadAllMedia();
    }
  }, [event?.id, loadAllMedia]);

  // ============================================================
  // Theme save
  // ============================================================

  const handleSaveTheme = async () => {
    if (!event) return;
    setThemeSaving(true);
    try {
      await updateAssignedEvent({ theme });
      setThemeSaved(true);
      setTimeout(() => setThemeSaved(false), 2500);
    } catch (err) {
      console.error('Failed to save theme:', err);
    } finally {
      setThemeSaving(false);
    }
  };

  // ============================================================
  // Landing message save
  // ============================================================

  const handleSaveMessage = async () => {
    if (!event) return;
    setMessageSaving(true);
    try {
      await updateAssignedEvent({ landingMessage });
      setMessageSaved(true);
      setTimeout(() => setMessageSaved(false), 2500);
    } catch (err) {
      console.error('Failed to save message:', err);
    } finally {
      setMessageSaving(false);
    }
  };

  // ============================================================
  // Media upload
  // ============================================================

  const handleUpload = async (catKey: string, file: File, role: MediaRole, page?: MediaPage) => {
    setUploadStates((prev) => ({ ...prev, [catKey]: { uploading: true } }));
    try {
      await uploadPresentationImage(file, role, page);
      await loadAllMedia();
      setUploadStates((prev) => ({ ...prev, [catKey]: { uploading: false } }));
    } catch (err: any) {
      setUploadStates((prev) => ({
        ...prev,
        [catKey]: { uploading: false, error: err.message || 'Upload failed' },
      }));
    }
  };

  // ============================================================
  // Media reassign
  // ============================================================

  const handleReassign = async () => {
    if (!reassignTarget) return;
    try {
      await updateMediaRoleAndPageLocal(reassignTarget.mediaId, reassignRole, reassignPage);
      await loadAllMedia();
    } catch (err) {
      console.error('Failed to reassign:', err);
    } finally {
      setReassignTarget(null);
    }
  };

  // ============================================================
  // Media delete
  // ============================================================

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deletePresentationMedia(deleteTarget.mediaId);
      await loadAllMedia();
    } catch (err) {
      console.error('Failed to delete:', err);
    } finally {
      setDeleteTarget(null);
    }
  };

  // ============================================================
  // Render
  // ============================================================

  if (loading) {
    return (
      <HostLayout event={{ id: '', slug: '', name: 'Loading...', subtitle: '', hostName: '', hostEmail: '', eventDate: '', status: 'not_started', theme: 'gold', slides: [], totalUploads: 0, photoCount: 0, videoCount: 0, contributingGuests: 0, storageUsedMb: 0, guestLink: '', archived: false }}>
        <p style={{ color: 'var(--color-muted, #8a7e72)', textAlign: 'center', padding: '2rem' }}>Loading settings...</p>
      </HostLayout>
    );
  }

  if (!event) {
    return (
      <HostLayout event={{ id: '', slug: '', name: 'Error', subtitle: '', hostName: '', hostEmail: '', eventDate: '', status: 'not_started', theme: 'gold', slides: [], totalUploads: 0, photoCount: 0, videoCount: 0, contributingGuests: 0, storageUsedMb: 0, guestLink: '', archived: false }}>
        <p style={{ color: '#c98a8a', textAlign: 'center', padding: '2rem' }}>Failed to load event settings.</p>
      </HostLayout>
    );
  }

  return (
    <HostLayout event={event}>
      <div className="host-settings">
        <header className="host-settings__header">
          <div>
            <p className="host-settings__eyebrow">Event Settings</p>
            <h1 className="host-settings__title">Customize Your Event</h1>
          </div>
        </header>

        <form className="host-settings__form" onSubmit={(e) => e.preventDefault()}>

          {/* ============================================================ */}
          {/* THEME SELECTOR */}
          {/* ============================================================ */}
          <fieldset className="host-settings__field">
            <legend className="guest-form__label">Theme</legend>
            <div className="host-settings__themes" role="radiogroup" aria-label="Theme choice">
              {THEME_OPTIONS.map((opt) => (
                <label key={opt.value} className="host-settings__theme">
                  <input
                    type="radio"
                    name="theme"
                    value={opt.value}
                    checked={theme === opt.value}
                    onChange={() => setTheme(opt.value)}
                  />
                  <span className={`host-settings__swatch host-settings__swatch--${opt.value}`} aria-hidden="true" />
                  {opt.label}
                </label>
              ))}
            </div>
            <div className="host-settings__actions">
              <button type="button" className="btn-primary" onClick={handleSaveTheme} disabled={themeSaving}>
                {themeSaving ? 'Saving...' : 'Save Theme'}
              </button>
              {themeSaved && <span className="host-settings__saved" role="status">Saved ✓</span>}
            </div>
          </fieldset>

          {/* ============================================================ */}
          {/* LANDING PAGE MESSAGE */}
          {/* ============================================================ */}
          <div className="host-settings__field">
            <label className="guest-form__label" htmlFor="host-landing-message">Landing Page Message</label>
            <textarea
              id="host-landing-message"
              className="guest-form__input"
              value={landingMessage}
              onChange={(e) => setLandingMessage(e.target.value)}
              placeholder="A personal message for your guests (shown on the public landing page)..."
              rows={4}
              style={{ resize: 'vertical', minHeight: '100px' }}
            />
            <p className="admin-create__field-hint">
              This message appears on the public event page below the Share Your Memories button. Line breaks are preserved.
            </p>
            <div className="host-settings__actions">
              <button type="button" className="btn-primary" onClick={handleSaveMessage} disabled={messageSaving}>
                {messageSaving ? 'Saving...' : 'Save Message'}
              </button>
              {messageSaved && <span className="host-settings__saved" role="status">Saved ✓</span>}
            </div>
          </div>

          {/* ============================================================ */}
          {/* EVENT VISUAL MEDIA */}
          {/* ============================================================ */}
          <div className="host-settings__field">
            <label className="guest-form__label">Event Visual Media</label>
            <p className="admin-create__field-hint" style={{ marginBottom: '1.5rem' }}>
              Upload and manage images that appear on different pages of your event. Guest uploads remain completely separate.
            </p>

            {MEDIA_CATEGORIES.map((cat) => {
              const items = mediaData[cat.key] || [];
              const uploadState = uploadStates[cat.key] || { uploading: false };

              return (
                <div key={cat.key} className="host-settings__media-category">
                  <div className="host-settings__media-category-header">
                    <h3 className="host-settings__media-category-title">{cat.label}</h3>
                    <p className="host-settings__media-category-desc">{cat.description}</p>
                  </div>

                  {/* Thumbnails */}
                  <div className="host-settings__media-grid">
                    {items.length === 0 ? (
                      <div className="host-settings__media-empty">
                        <p>No images assigned yet.</p>
                      </div>
                    ) : (
                      <div className="host-settings__media-thumbnails">
                        {items.map((m) => (
                          <div key={m.id} className="host-settings__media-thumb">
                            <div className="host-settings__media-thumb-inner">
                              {m.type === 'video' ? (
                                <video src={m.src} muted playsInline />
                              ) : (
                                <img src={m.src} alt={m.caption || m.guestName} loading="lazy" />
                              )}
                              <div className="host-settings__media-overlay">
                                <button
                                  type="button"
                                  className="host-settings__media-action is-reassign"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setReassignTarget({
                                      mediaId: m.mediaId || m.id,
                                      currentRole: (m.mediaRole || cat.role) as MediaRole,
                                      currentPage: (m.page || cat.page) as MediaPage | undefined,
                                    });
                                    setReassignRole(cat.role);
                                    setReassignPage(cat.page);
                                  }}
                                  title="Reassign to another category"
                                >
                                  ⟳
                                </button>
                                <button
                                  type="button"
                                  className="host-settings__media-action is-delete"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setDeleteTarget({
                                      mediaId: m.mediaId || m.id,
                                      label: m.caption || m.guestName || 'this image',
                                    });
                                  }}
                                  title="Remove"
                                >
                                  ✕
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Upload */}
                  <div className="host-settings__media-upload">
                    <label className="host-settings__upload-label">
                      <input
                        type="file"
                        accept="image/*"
                        multiple
                        onChange={(e) => {
                          const files = Array.from(e.target.files || []);
                          files.forEach((file) => handleUpload(cat.key, file, cat.role, cat.page));
                          e.target.value = '';
                        }}
                        className="host-settings__file-input"
                        disabled={uploadState.uploading}
                      />
                      <span className="host-settings__upload-text">
                        {uploadState.uploading ? 'Uploading...' : '+ Upload Images'}
                      </span>
                      {uploadState.error && (
                        <span className="host-settings__upload-error">{uploadState.error}</span>
                      )}
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
        </form>

        {/* ============================================================ */}
        {/* REASSIGN MODAL */}
        {/* ============================================================ */}
        {reassignTarget && (
          <div className="host-settings__modal-overlay" onClick={() => setReassignTarget(null)}>
            <div className="host-settings__modal" onClick={(e) => e.stopPropagation()}>
              <h3 className="host-settings__modal-title">Reassign Image</h3>
              <p className="host-settings__modal-desc">Move this image to a different category.</p>

              <label className="guest-form__label" htmlFor="reassign-role">Category</label>
              <select
                id="reassign-role"
                className="guest-form__input"
                value={ALL_ROLES.findIndex((r) => r.role === reassignRole && r.page === reassignPage)}
                onChange={(e) => {
                  const idx = parseInt(e.target.value);
                  setReassignRole(ALL_ROLES[idx].role);
                  setReassignPage(ALL_ROLES[idx].page as MediaPage);
                }}
              >
                {ALL_ROLES.map((r, i) => (
                  <option key={i} value={i}>{r.label}</option>
                ))}
              </select>

              <div className="host-settings__modal-actions">
                <button type="button" className="btn-ghost" onClick={() => setReassignTarget(null)}>Cancel</button>
                <button type="button" className="btn-primary" onClick={handleReassign}>Reassign</button>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* DELETE CONFIRMATION */}
        {/* ============================================================ */}
        <ConfirmDialog
          open={!!deleteTarget}
          title="Remove this image?"
          message={`This image will be removed from this event. This action cannot be undone.`}
          confirmLabel="Remove"
          cancelLabel="Cancel"
          destructive
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      </div>
    </HostLayout>
  );
}
