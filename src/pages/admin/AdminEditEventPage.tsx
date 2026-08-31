// ============================================================
// Lentis Gallery — Admin Edit Event Page
// ============================================================
// Lets the admin edit an existing event's details and manage
// media assignments (role + page) for uploaded images.
// ============================================================

import { useMemo, useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import {
  getEventById,
  updateEvent,
  listEventMedia,
  uploadFilesToEvent,
  setMediaRole,
  deleteEventMedia,
  slugify,
} from '../../services/mockAdminService';
import {
  listInvitedGuests,
  addInvitedGuest,
  removeInvitedGuest,
} from '../../services/api';
import type { MediaItem, MediaRole, MediaPage, InvitedGuest } from '../../services/api';
import { getPublicBaseUrl } from '../../services/config';
import type { Event, ThemeChoice } from '../../types/event';

const THEME_OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: 'gold', label: 'Gold' },
  { value: 'blue', label: 'Blue' },
  { value: 'rose', label: 'Rose' },
  { value: 'emerald', label: 'Emerald' },
];

const ROLE_PAGE_OPTIONS: { role: MediaRole; page: MediaPage | null; label: string }[] = [
  { role: 'HERO', page: 'LANDING', label: 'Hero / Cover' },
  { role: 'SLIDESHOW', page: 'LANDING', label: 'Landing Slideshow' },
  { role: 'SLIDESHOW', page: 'GUEST', label: 'Guest Page Slideshow' },
  { role: 'SLIDESHOW', page: 'CAMERA', label: 'Camera Page Slideshow' },
  { role: 'HOST_SLIDESHOW', page: 'HOST', label: 'Host Page Slideshow' },
  { role: 'GALLERY', page: null, label: 'Gallery' },
];

function getOptionIndex(role: MediaRole, page: MediaPage | null): number {
  return ROLE_PAGE_OPTIONS.findIndex((o) => o.role === role && o.page === page);
}

interface FormErrors {
  name?: string;
  subtitle?: string;
  hostName?: string;
  hostEmail?: string;
  eventDate?: string;
  slug?: string;
  hostPassword?: string;
}

interface SelectedNewFile {
  file: File;
  preview: string;
  role: MediaRole;
  page: MediaPage | null;
  label: string;
}

export default function AdminEditEventPage() {
  const navigate = useNavigate();
  const { eventId } = useParams<{ eventId: string }>();

  const [existing, setExisting] = useState<Event | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [hostName, setHostName] = useState('');
  const [hostEmail, setHostEmail] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [slug, setSlug] = useState('');
  const [theme, setTheme] = useState<ThemeChoice>('gold');
  const [landingMessage, setLandingMessage] = useState('');
  const [newHostPassword, setNewHostPassword] = useState('');
  const [confirmHostPassword, setConfirmHostPassword] = useState('');
  const [accessMode, setAccessMode] = useState<'PUBLIC' | 'PRIVATE'>('PUBLIC');
  const [invitedGuests, setInvitedGuests] = useState<InvitedGuest[]>([]);
  const [guestCounts, setGuestCounts] = useState<{ total: number; joined: number; not_joined: number }>({ total: 0, joined: 0, not_joined: 0 });
  const [guestName, setGuestName] = useState('');
  const [guestPassword, setGuestPassword] = useState('');
  const [guestError, setGuestError] = useState('');

  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [newFiles, setNewFiles] = useState<SelectedNewFile[]>([]);

  useEffect(() => {
    if (eventId) {
      Promise.all([
        getEventById(eventId),
        listEventMedia(eventId).catch(() => ({ items: [], total: 0 })),
        listInvitedGuests(eventId).catch(() => ({ guests: [], total: 0, joined: 0, not_joined: 0 })),
      ]).then(([ev, media, guests]) => {
        setExisting(ev);
        setMediaItems(media.items);
        setInvitedGuests(guests.guests);
        setGuestCounts({ total: guests.total, joined: guests.joined, not_joined: guests.not_joined });
        setLoading(false);
      }).catch(() => setLoading(false));
    }
  }, [eventId]);

  useEffect(() => {
    if (existing) {
      setName(existing.name);
      setSubtitle(existing.subtitle);
      setHostName(existing.hostName);
      setHostEmail(existing.hostEmail);
      setEventDate(existing.eventDate);
      setSlug(existing.slug);
      setTheme(existing.theme);
      setLandingMessage(existing.landingMessage || '');
      setAccessMode(existing.accessMode || 'PUBLIC');
    }
  }, [existing]);

  const [errors, setErrors] = useState<FormErrors>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const autoSlug = useMemo(() => (name.trim() ? slugify(name) : ''), [name]);
  const effectiveSlug = slug.trim() ? slug.trim() : autoSlug;

  const validate = (): boolean => {
    const next: FormErrors = {};
    if (name.trim().length < 3) next.name = 'Event name is required (min 3 characters).';
    if (subtitle.trim().length < 3) next.subtitle = 'Subtitle is required (min 3 characters).';
    if (hostName.trim().length < 2) next.hostName = 'Host name is required.';
    if (!hostEmail.trim() || !hostEmail.includes('@')) next.hostEmail = 'Valid host email is required.';
    if (!eventDate) next.eventDate = 'Event date is required.';
    if (!effectiveSlug) next.slug = 'Slug is required.';
    // Password validation (only if a new password is being set)
    if (newHostPassword || confirmHostPassword) {
      if (newHostPassword.length < 10) next.hostPassword = 'Password must be at least 10 characters.';
      else if (newHostPassword !== confirmHostPassword) next.hostPassword = 'Passwords do not match.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  // Invited guest management
  const generatePassword = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%';
    let pw = '';
    const arr = new Uint8Array(12);
    crypto.getRandomValues(arr);
    for (let i = 0; i < 12; i++) pw += chars[arr[i] % chars.length];
    return pw;
  };

  const handleAddGuest = async () => {
    if (!eventId || !guestName.trim() || !guestPassword) return;
    setGuestError('');
    try {
      const g = await addInvitedGuest(eventId, guestName.trim(), guestPassword);
      setInvitedGuests((prev) => [g, ...prev]);
      setGuestCounts((prev) => ({ total: prev.total + 1, joined: prev.joined, not_joined: prev.not_joined + 1 }));
      setGuestName('');
      setGuestPassword('');
    } catch (err: any) {
      setGuestError(err.message || 'Failed to add guest.');
    }
  };

  const handleRemoveGuest = async (guestId: string) => {
    if (!eventId) return;
    try {
      await removeInvitedGuest(eventId, guestId);
      setInvitedGuests((prev) => prev.filter((g) => g.id !== guestId));
      setGuestCounts((prev) => ({ total: prev.total - 1, joined: prev.joined, not_joined: prev.not_joined }));
    } catch (err: any) {
      setGuestError(err.message || 'Failed to remove guest.');
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate() || !eventId) return;
    setSaving(true);
    try {
      await updateEvent(eventId, {
        name: name.trim(),
        subtitle: subtitle.trim(),
        eventDate,
        theme,
        accessMode,
        landingMessage: landingMessage.trim() || undefined,
        ...(newHostPassword ? { host_password: newHostPassword } : {}),
      });
      // Clear password fields after successful save
      setNewHostPassword('');
      setConfirmHostPassword('');
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2500);
    } catch (err: any) {
      // Error handled silently
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    const newItems: SelectedNewFile[] = files.map((file) => ({
      file,
      preview: '',
      role: 'GALLERY' as MediaRole,
      page: null,
      label: 'Gallery',
    }));
    newItems.forEach((item, i) => {
      const reader = new FileReader();
      reader.onload = () => {
        setNewFiles((prev) => {
          const updated = [...prev];
          const idx = prev.length - newItems.length + i;
          if (idx >= 0 && idx < updated.length) {
            updated[idx] = { ...updated[idx], preview: reader.result as string };
          }
          return updated;
        });
      };
      reader.readAsDataURL(item.file);
    });
    setNewFiles((prev) => [...prev, ...newItems]);
    e.target.value = '';
  };

  const removeNewFile = (index: number) => {
    setNewFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const setNewFileAssignment = (index: number, optionIndex: number) => {
    const opt = ROLE_PAGE_OPTIONS[optionIndex];
    setNewFiles((prev) => prev.map((f, i) => i === index ? { ...f, role: opt.role, page: opt.page, label: opt.label } : f));
  };

  const handleMediaUpload = async () => {
    if (!eventId || newFiles.length === 0) return;
    setUploading(true);
    try {
      const roles = newFiles.map((f) => f.role);
      const pages = newFiles.map((f) => f.page ?? undefined);
      await uploadFilesToEvent(eventId, newFiles.map((f) => f.file), 'GALLERY', roles, pages);
      const newMedia = await listEventMedia(eventId);
      setMediaItems(newMedia.items);
      setNewFiles([]);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleRoleChange = async (mediaId: string, optionIndex: number) => {
    if (!eventId) return;
    const opt = ROLE_PAGE_OPTIONS[optionIndex];
    try {
      await setMediaRole(eventId, mediaId, opt.role, opt.page || undefined);
      const updated = await listEventMedia(eventId);
      setMediaItems(updated.items);
    } catch (err) {
      console.error('Role update failed:', err);
    }
  };

  const handleDeleteMedia = async (mediaId: string) => {
    if (!eventId || !confirm('Remove this media item?')) return;
    try {
      await deleteEventMedia(eventId, mediaId);
      setMediaItems((prev) => prev.filter((m) => m.id !== mediaId));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  if (loading) {
    return (
      <AdminLayout title="Edit Event">
        <div className="admin-create">
          <p className="admin-overview__empty">Loading...</p>
        </div>
      </AdminLayout>
    );
  }

  if (!existing) {
    return (
      <AdminLayout title="Edit Event">
        <div className="admin-create">
          <p className="admin-overview__empty">Event not found.</p>
          <button className="btn-ghost" onClick={() => navigate('/admin/console/events')}>Back to Events</button>
        </div>
      </AdminLayout>
    );
  }

  const groupedMedia = {
    hero: mediaItems.filter((m) => m.media_role === 'HERO'),
    landingSlideshow: mediaItems.filter((m) => m.media_role === 'SLIDESHOW' && m.page === 'LANDING'),
    guestSlideshow: mediaItems.filter((m) => m.media_role === 'SLIDESHOW' && m.page === 'GUEST'),
    cameraSlideshow: mediaItems.filter((m) => m.media_role === 'SLIDESHOW' && m.page === 'CAMERA'),
    hostSlideshow: mediaItems.filter((m) => m.media_role === 'HOST_SLIDESHOW'),
    gallery: mediaItems.filter((m) => m.media_role === 'GALLERY'),
  };

  return (
    <AdminLayout title="Edit Event">
      <div className="admin-create">
        <header className="admin-create__header">
          <div>
            <p className="admin-create__eyebrow">Edit Event</p>
            <h1 className="admin-create__title">{existing.name}</h1>
          </div>
        </header>

        <form className="admin-create__form" onSubmit={handleSubmit} noValidate>
          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="edit-name">Event Name</label>
            <input id="edit-name" className="guest-form__input" type="text" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={errors.name ? true : undefined} />
            {errors.name && <p className="guest-form__error" role="alert">{errors.name}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="edit-subtitle">Subtitle</label>
            <input id="edit-subtitle" className="guest-form__input" type="text" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} aria-invalid={errors.subtitle ? true : undefined} />
            {errors.subtitle && <p className="guest-form__error" role="alert">{errors.subtitle}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="edit-host">Host Name</label>
            <input id="edit-host" className="guest-form__input" type="text" value={hostName} onChange={(e) => setHostName(e.target.value)} aria-invalid={errors.hostName ? true : undefined} />
            {errors.hostName && <p className="guest-form__error" role="alert">{errors.hostName}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="edit-host-email">Host Email</label>
            <input id="edit-host-email" className="guest-form__input" type="email" value={hostEmail} onChange={(e) => setHostEmail(e.target.value)} aria-invalid={errors.hostEmail ? true : undefined} />
            {errors.hostEmail && <p className="guest-form__error" role="alert">{errors.hostEmail}</p>}
          </div>

          <div className="admin-create__field" style={{ padding: '0.8rem 1rem', background: 'rgba(200, 169, 106, 0.04)', borderRadius: '8px', border: '1px solid rgba(200, 169, 106, 0.12)' }}>
            <label className="guest-form__label" style={{ color: 'var(--color-muted, #8a7e72)' }}>Change Host Password (leave empty to keep current)</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <input
                id="edit-host-password"
                className="guest-form__input"
                type="password"
                value={newHostPassword}
                onChange={(e) => setNewHostPassword(e.target.value)}
                placeholder="New host password (min 10 characters)"
                autoComplete="new-password"
              />
              <input
                id="edit-host-password-confirm"
                className="guest-form__input"
                type="password"
                value={confirmHostPassword}
                onChange={(e) => setConfirmHostPassword(e.target.value)}
                placeholder="Confirm new password"
                autoComplete="new-password"
              />
            </div>
            {errors.hostPassword && <p className="guest-form__error" role="alert">{errors.hostPassword}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="edit-date">Event Date</label>
            <input id="edit-date" className="guest-form__input" type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} aria-invalid={errors.eventDate ? true : undefined} />
            {errors.eventDate && <p className="guest-form__error" role="alert">{errors.eventDate}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="edit-slug">Slug</label>
            <input id="edit-slug" className="guest-form__input" type="text" value={effectiveSlug} onChange={(e) => setSlug(e.target.value)} aria-invalid={errors.slug ? true : undefined} />
            <p className="admin-create__field-hint">{getPublicBaseUrl()}/e/{effectiveSlug || '…'}</p>
            {errors.slug && <p className="guest-form__error" role="alert">{errors.slug}</p>}
          </div>

          <fieldset className="admin-create__field">
            <legend className="guest-form__label">Theme</legend>
            <div className="host-settings__themes" role="radiogroup" aria-label="Theme choice">
              {THEME_OPTIONS.map((opt) => (
                <label key={opt.value} className="host-settings__theme">
                  <input type="radio" name="theme" value={opt.value} checked={theme === opt.value} onChange={() => setTheme(opt.value)} />
                  <span className={`host-settings__swatch host-settings__swatch--${opt.value}`} aria-hidden="true" />
                  {opt.label}
                </label>
              ))}
            </div>
          </fieldset>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="edit-landing-message">Landing Page Message</label>
            <textarea
              id="edit-landing-message"
              className="guest-form__input"
              value={landingMessage}
              onChange={(e) => setLandingMessage(e.target.value)}
              placeholder="A personal message for your guests (shown below Share Your Memories)…"
              rows={3}
              style={{ resize: 'vertical', minHeight: '80px' }}
            />
            <p className="admin-create__field-hint">Optional. This message appears on the public landing page below the Share Your Memories button.</p>
          </div>

          <fieldset className="admin-create__field">
            <legend className="guest-form__label">Event Access</legend>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', color: 'var(--color-text, #e8e0d4)', fontSize: '0.9rem' }}>
                <input type="radio" name="accessMode" value="PUBLIC" checked={accessMode === 'PUBLIC'} onChange={() => setAccessMode('PUBLIC')} style={{ accentColor: '#c8a96a' }} />
                Public Event
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', color: 'var(--color-text, #e8e0d4)', fontSize: '0.9rem' }}>
                <input type="radio" name="accessMode" value="PRIVATE" checked={accessMode === 'PRIVATE'} onChange={() => setAccessMode('PRIVATE')} style={{ accentColor: '#c8a96a' }} />
                Private Event
              </label>
            </div>
            <p className="admin-create__field-hint">
              {accessMode === 'PUBLIC' ? 'Anyone with the event link can participate.' : 'Only invited guests can participate.'}
            </p>
          </fieldset>

          {accessMode === 'PRIVATE' && (
            <fieldset className="admin-create__field">
              <legend className="guest-form__label">Invited Guests ({guestCounts.total} total, {guestCounts.joined} joined, {guestCounts.not_joined} not joined)</legend>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                <input className="guest-form__input" type="text" placeholder="Guest name" value={guestName} onChange={(e) => setGuestName(e.target.value)} style={{ flex: 1, minWidth: '120px', fontSize: '0.85rem' }} />
                <input className="guest-form__input" type="text" placeholder="Password" value={guestPassword} onChange={(e) => setGuestPassword(e.target.value)} style={{ flex: 1, minWidth: '120px', fontSize: '0.85rem' }} />
                <button type="button" className="btn-ghost" onClick={() => setGuestPassword(generatePassword())} style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>Generate</button>
                <button type="button" className="btn-primary" onClick={handleAddGuest} disabled={!guestName.trim() || !guestPassword} style={{ fontSize: '0.8rem' }}>Add Guest</button>
              </div>
              {guestError && <p style={{ color: '#c98a8a', fontSize: '0.8rem', marginBottom: '0.5rem' }}>{guestError}</p>}
              {invitedGuests.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                  {invitedGuests.map((g) => (
                    <div key={g.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0.6rem', background: 'rgba(255,255,255,0.03)', borderRadius: '4px' }}>
                      <div>
                        <span style={{ color: 'var(--color-text, #e8e0d4)', fontSize: '0.85rem' }}>{g.name}</span>
                        <span style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.75rem', marginLeft: '0.5rem' }}>
                          {g.status === 'ACTIVE' ? '✓ Joined' : g.status === 'REMOVED' ? '✗ Removed' : 'Pending'}
                        </span>
                      </div>
                      {g.status !== 'REMOVED' && (
                        <button type="button" onClick={() => handleRemoveGuest(g.id)} style={{ background: 'none', border: 'none', color: '#c98a8a', cursor: 'pointer', fontSize: '0.8rem' }}>Remove</button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.8rem' }}>No guests added yet.</p>
              )}
            </fieldset>
          )}

          <div className="admin-create__actions">
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
            {saved && <span className="host-settings__saved" role="status">Saved ✓</span>}
            <button type="button" className="btn-ghost" onClick={() => navigate('/admin/console/events')}>Cancel</button>
          </div>
        </form>

        {/* Media Management Section */}
        <fieldset className="admin-create__field" style={{ marginTop: '2rem' }}>
          <legend className="guest-form__label">Event Media ({mediaItems.length} items)</legend>

          {/* New file selection with role assignment */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.6rem 1.2rem',
              background: 'rgba(200, 169, 106, 0.08)',
              border: '1px dashed rgba(200, 169, 106, 0.3)',
              borderRadius: '6px', cursor: 'pointer',
              color: 'var(--color-gold, #c8a96a)', fontSize: '0.85rem',
            }}>
              <input type="file" accept="image/*" multiple onChange={handleFileSelect} style={{ display: 'none' }} disabled={uploading} />
              {uploading ? 'Uploading…' : '+ Choose Images'}
            </label>
          </div>

          {/* New files with role assignment */}
          {newFiles.length > 0 && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontFamily: 'var(--font-display)', color: 'var(--color-gold, #c8a96a)', fontSize: '0.85rem', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                New Images ({newFiles.length})
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.5rem' }}>
                {newFiles.map((item, i) => (
                  <div key={i} style={{
                    position: 'relative', borderRadius: '6px', overflow: 'hidden',
                    border: `1px solid ${item.role === 'HERO' ? 'rgba(200,169,106,0.6)' : item.role === 'SLIDESHOW' ? 'rgba(126,175,105,0.4)' : item.role === 'HOST_SLIDESHOW' ? 'rgba(100,149,237,0.5)' : 'rgba(255,255,255,0.08)'}`,
                    background: '#1a1510',
                  }}>
                    <div style={{ aspectRatio: '1', overflow: 'hidden' }}>
                      {item.preview && <img src={item.preview} alt={item.file.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
                    </div>
                    <button
                      type="button"
                      onClick={() => removeNewFile(i)}
                      style={{ position: 'absolute', top: '4px', right: '4px', width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(0,0,0,0.7)', color: '#c98a8a', border: 'none', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      aria-label="Remove"
                    >×</button>
                    <div style={{ padding: '4px' }}>
                      <p style={{ color: '#ccc', fontSize: '0.6rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '2px' }}>
                        {item.file.name}
                      </p>
                      <select
                        value={ROLE_PAGE_OPTIONS.findIndex((o) => o.role === item.role && o.page === item.page)}
                        onChange={(e) => setNewFileAssignment(i, parseInt(e.target.value))}
                        style={{ width: '100%', padding: '2px', fontSize: '0.65rem', background: 'rgba(255,255,255,0.06)', color: '#ccc', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '3px', cursor: 'pointer' }}
                      >
                        {ROLE_PAGE_OPTIONS.map((opt, idx) => (
                          <option key={idx} value={idx}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="btn-primary"
                onClick={handleMediaUpload}
                disabled={uploading}
                style={{ marginTop: '0.75rem' }}
              >
                {uploading ? 'Uploading…' : `Upload ${newFiles.length} Image${newFiles.length > 1 ? 's' : ''}`}
              </button>
            </div>
          )}

          {Object.entries(groupedMedia).map(([group, items]) => {
            const groupLabels: Record<string, string> = {
              hero: 'Hero Image',
              landingSlideshow: 'Landing Slideshow',
              guestSlideshow: 'Guest Page Slideshow',
              cameraSlideshow: 'Camera Page Slideshow',
              hostSlideshow: 'Host Page Slideshow',
              gallery: 'Gallery',
            };
            return (
              <div key={group} style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ fontFamily: 'var(--font-display)', color: 'var(--color-gold, #c8a96a)', fontSize: '0.85rem', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                  {groupLabels[group]} ({items.length})
                </h3>
                {items.length === 0 ? (
                  <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.8rem' }}>No media assigned.</p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '0.5rem' }}>
                    {items.map((m) => (
                      <div key={m.id} style={{ position: 'relative', borderRadius: '6px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', background: '#1a1510' }}>
                        <div style={{ aspectRatio: '1', overflow: 'hidden' }}>
                          <img src={m.media_url || `/api/media/${m.id}`} alt={m.original_filename} style={{ width: '100%', height: '100%', objectFit: 'cover' }} loading="lazy" />
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteMedia(m.id)}
                          style={{ position: 'absolute', top: '4px', right: '4px', width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(0,0,0,0.7)', color: '#c98a8a', border: 'none', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          aria-label="Remove"
                        >×</button>
                        <div style={{ padding: '4px' }}>
                          <p style={{ color: '#ccc', fontSize: '0.6rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '2px' }}>
                            {m.original_filename}
                          </p>
                          <select
                            value={getOptionIndex(m.media_role, m.page)}
                            onChange={(e) => handleRoleChange(m.id, parseInt(e.target.value))}
                            style={{ width: '100%', padding: '2px', fontSize: '0.65rem', background: 'rgba(255,255,255,0.06)', color: '#ccc', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '3px', cursor: 'pointer' }}
                          >
                            {ROLE_PAGE_OPTIONS.map((opt, idx) => (
                              <option key={idx} value={idx}>{opt.label}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </fieldset>
      </div>
    </AdminLayout>
  );
}
