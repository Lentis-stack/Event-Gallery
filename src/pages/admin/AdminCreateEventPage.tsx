// ============================================================
// Lentis Gallery — Admin Create Event Page
// ============================================================
// Creates a REAL event in PostgreSQL via the backend API.
// After event creation, uploads selected images to object storage.
// Shows QR code for the new event's public URL.
// ============================================================

import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { QRCodeCanvas } from 'qrcode.react';
import { motion } from 'framer-motion';
import AdminLayout from '../../components/admin/AdminLayout';
import { createEvent, uploadFilesToEvent, slugify } from '../../services/mockAdminService';
import { addInvitedGuest, removeInvitedGuest } from '../../services/api';
import type { MediaRole, MediaPage, InvitedGuest } from '../../services/api';
import { getPublicBaseUrl } from '../../services/config';
import type { Event, ThemeChoice } from '../../types/event';

const THEME_OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: 'gold', label: 'Gold' },
  { value: 'blue', label: 'Blue' },
  { value: 'rose', label: 'Rose' },
  { value: 'emerald', label: 'Emerald' },
];

interface FormErrors {
  name?: string;
  subtitle?: string;
  hostName?: string;
  hostEmail?: string;
  hostPassword?: string;
  eventDate?: string;
  slug?: string;
}

type CreateStep = 'form' | 'creating' | 'uploading' | 'done' | 'error';

interface UploadResult {
  file: string;
  success: boolean;
  error?: string;
}

interface SelectedFile {
  file: File;
  preview: string;
  role: MediaRole;
  page: MediaPage | null;
  label: string;
}

const ROLE_PAGE_OPTIONS: { role: MediaRole; page: MediaPage | null; label: string }[] = [
  { role: 'HERO', page: 'LANDING', label: 'Hero / Cover' },
  { role: 'SLIDESHOW', page: 'LANDING', label: 'Landing Slideshow' },
  { role: 'SLIDESHOW', page: 'GUEST', label: 'Guest Page Slideshow' },
  { role: 'SLIDESHOW', page: 'CAMERA', label: 'Camera Page Slideshow' },
  { role: 'HOST_SLIDESHOW', page: 'HOST', label: 'Host Page Slideshow' },
  { role: 'GALLERY', page: null, label: 'Gallery' },
];

export default function AdminCreateEventPage() {
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [hostName, setHostName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [slug, setSlug] = useState('');
  const [theme, setTheme] = useState<ThemeChoice>('gold');
  const [hostEmail, setHostEmail] = useState('');
  const [hostPassword, setHostPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [landingMessage, setLandingMessage] = useState('');
  const [accessMode, setAccessMode] = useState<'PUBLIC' | 'PRIVATE'>('PUBLIC');
  const [invitedGuests, setInvitedGuests] = useState<InvitedGuest[]>([]);
  const [guestName, setGuestName] = useState('');
  const [guestPassword, setGuestPassword] = useState('');
  const [guestError, setGuestError] = useState('');

  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);

  const [step, setStep] = useState<CreateStep>('form');
  const [errors, setErrors] = useState<FormErrors>({});
  const [createdEvent, setCreatedEvent] = useState<Event | null>(null);
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const [globalError, setGlobalError] = useState('');

  const autoSlug = useMemo(() => (name.trim() ? slugify(name) : ''), [name]);
  const effectiveSlug = slug.trim() ? slug.trim() : autoSlug;

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newItems: SelectedFile[] = files.map((file) => ({
      file,
      preview: '',
      role: 'GALLERY' as MediaRole,
      page: null,
      label: 'Gallery',
    }));
    newItems.forEach((item, i) => {
      const reader = new FileReader();
      reader.onload = () => {
        setSelectedFiles((prev) => {
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
    setSelectedFiles((prev) => [...prev, ...newItems]);
    e.target.value = '';
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const setFileAssignment = (index: number, optionIndex: number) => {
    const opt = ROLE_PAGE_OPTIONS[optionIndex];
    setSelectedFiles((prev) => prev.map((f, i) => i === index ? { ...f, role: opt.role, page: opt.page, label: opt.label } : f));
  };

  // Invited guest management (only used after event is created)
  const generatePassword = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%';
    let pw = '';
    const arr = new Uint8Array(12);
    crypto.getRandomValues(arr);
    for (let i = 0; i < 12; i++) pw += chars[arr[i] % chars.length];
    return pw;
  };

  const handleAddGuest = async () => {
    if (!createdEvent || !guestName.trim() || !guestPassword) return;
    setGuestError('');
    try {
      const g = await addInvitedGuest(createdEvent.id, guestName.trim(), guestPassword);
      setInvitedGuests((prev) => [g, ...prev]);
      setGuestName('');
      setGuestPassword('');
    } catch (err: any) {
      setGuestError(err.message || 'Failed to add guest.');
    }
  };

  const handleRemoveGuest = async (guestId: string) => {
    if (!createdEvent) return;
    try {
      await removeInvitedGuest(createdEvent.id, guestId);
      setInvitedGuests((prev) => prev.filter((g) => g.id !== guestId));
    } catch (err: any) {
      setGuestError(err.message || 'Failed to remove guest.');
    }
  };

  const validate = (): boolean => {
    const next: FormErrors = {};
    if (name.trim().length < 3) next.name = 'Event name is required (min 3 characters).';
    if (subtitle.trim().length < 3) next.subtitle = 'Subtitle is required (min 3 characters).';
    if (hostName.trim().length < 2) next.hostName = 'Host name is required.';
    if (!hostEmail.trim() || !hostEmail.includes('@')) next.hostEmail = 'Valid host email is required.';
    if (hostPassword.length < 10) next.hostPassword = 'Host password must be at least 10 characters.';
    else if (hostPassword !== confirmPassword) next.hostPassword = 'Passwords do not match.';
    if (!eventDate) next.eventDate = 'Event date is required.';
    if (!effectiveSlug) next.slug = 'Slug is required.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setStep('creating');
    setGlobalError('');

    try {
      const newEvent = await createEvent({
        name: name.trim(),
        subtitle: subtitle.trim(),
        hostName: hostName.trim(),
        hostEmail: hostEmail.trim(),
        hostPassword,
        eventDate,
        slug: effectiveSlug,
        theme,
        accessMode,
        landingMessage: landingMessage.trim() || undefined,
      });
      setCreatedEvent(newEvent);

      if (selectedFiles.length > 0) {
        setStep('uploading');
        const roles = selectedFiles.map((f) => f.role);
        const pages = selectedFiles.map((f) => f.page ?? undefined);
        const results = await uploadFilesToEvent(newEvent.id, selectedFiles.map((f) => f.file), 'GALLERY', roles, pages);
        setUploadResults(results);
      }

      setStep('done');
    } catch (err: any) {
      setGlobalError(err.message || 'Failed to create event. Please try again.');
      setStep('error');
    }
  };

  const successCount = uploadResults.filter((r) => r.success).length;
  const failCount = uploadResults.filter((r) => !r.success).length;

  const publicUrl = createdEvent
    ? `${getPublicBaseUrl()}/e/${createdEvent.slug}`
    : '';

  if (step === 'done' && createdEvent) {
    return (
      <AdminLayout title="Event Created">
        <div className="admin-create">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            style={{ maxWidth: '600px', margin: '2rem auto', textAlign: 'center' }}
          >
            <div style={{
              width: '64px', height: '64px', borderRadius: '50%',
              background: 'rgba(126, 175, 105, 0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 1.5rem', fontSize: '1.8rem', color: '#7eaf69',
            }}>✓</div>

            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(1.3rem, 3vw, 1.8rem)',
              color: 'var(--color-gold, #c8a96a)',
              letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '0.5rem',
            }}>Event Created Successfully</h1>

            <p style={{ color: 'var(--color-text, #e8e0d4)', fontSize: '1.1rem', marginBottom: '0.3rem' }}>
              {createdEvent.name}
            </p>

            {uploadResults.length > 0 && (
              <div style={{ margin: '1.5rem 0', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Media Upload</p>
                {successCount > 0 && <p style={{ color: '#7eaf69', fontSize: '0.9rem' }}>✓ {successCount} uploaded successfully</p>}
                {failCount > 0 && <p style={{ color: '#c98a8a', fontSize: '0.9rem' }}>✗ {failCount} failed to upload</p>}
                {uploadResults.filter((r) => !r.success).map((r, i) => (
                  <p key={i} style={{ color: '#c98a8a', fontSize: '0.8rem', marginTop: '0.3rem' }}>{r.file}: {r.error}</p>
                ))}
              </div>
            )}

            <div style={{ margin: '1.5rem 0', padding: '1rem', background: 'rgba(200, 169, 106, 0.06)', borderRadius: '8px', border: '1px solid rgba(200, 169, 106, 0.12)' }}>
              <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.8rem', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Public Event URL</p>
              <p style={{ color: 'var(--color-gold, #c8a96a)', fontSize: '0.95rem', wordBreak: 'break-all' }}>{publicUrl}</p>
            </div>

            <div style={{ margin: '1.5rem 0' }}>
              <div style={{ display: 'inline-block', padding: '1rem', background: '#0a0806', borderRadius: '8px', border: '1px solid rgba(200, 169, 106, 0.15)' }}>
                <QRCodeCanvas value={publicUrl} size={180} bgColor="#0a0806" fgColor="#c8a96a" level="M" aria-label={`QR code for ${createdEvent.name}`} />
              </div>
            </div>

            {accessMode === 'PRIVATE' && (
              <div style={{ margin: '1.5rem 0', padding: '1rem', background: 'rgba(200, 169, 106, 0.06)', borderRadius: '8px', border: '1px solid rgba(200, 169, 106, 0.12)', textAlign: 'left' }}>
                <p style={{ color: 'var(--color-gold, #c8a96a)', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Invited Guests</p>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                  <input className="guest-form__input" type="text" placeholder="Guest name" value={guestName} onChange={(e) => setGuestName(e.target.value)} style={{ flex: 1, minWidth: '120px', fontSize: '0.85rem' }} />
                  <input className="guest-form__input" type="text" placeholder="Password" value={guestPassword} onChange={(e) => setGuestPassword(e.target.value)} style={{ flex: 1, minWidth: '120px', fontSize: '0.85rem' }} />
                  <button type="button" className="btn-ghost" onClick={() => setGuestPassword(generatePassword())} style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>Generate</button>
                  <button type="button" className="btn-primary" onClick={handleAddGuest} disabled={!guestName.trim() || !guestPassword} style={{ fontSize: '0.8rem' }}>Add</button>
                </div>
                {guestError && <p style={{ color: '#c98a8a', fontSize: '0.8rem', marginBottom: '0.5rem' }}>{guestError}</p>}
                {invitedGuests.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
                    {invitedGuests.map((g) => (
                      <div key={g.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0.6rem', background: 'rgba(255,255,255,0.03)', borderRadius: '4px' }}>
                        <span style={{ color: 'var(--color-text, #e8e0d4)', fontSize: '0.85rem' }}>{g.name}</span>
                        <button type="button" onClick={() => handleRemoveGuest(g.id)} style={{ background: 'none', border: 'none', color: '#c98a8a', cursor: 'pointer', fontSize: '0.8rem' }}>Remove</button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.8rem', marginTop: '0.5rem' }}>No guests added yet. Add invited guests above.</p>
                )}
                <p style={{ color: 'var(--color-muted, #8a7e72)', fontSize: '0.75rem', marginTop: '0.5rem' }}>You can also manage guests later from the Edit Event page.</p>
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap', marginTop: '1.5rem' }}>
              <button type="button" className="btn-primary" onClick={() => navigator.clipboard.writeText(publicUrl)}>Copy Link</button>
              <button type="button" className="btn-ghost" onClick={() => {
                const canvas = document.querySelector('canvas');
                if (canvas) { const url = canvas.toDataURL('image/png'); const a = document.createElement('a'); a.href = url; a.download = `${createdEvent.slug}-qr.png`; a.click(); }
              }}>Download QR</button>
              <button type="button" className="btn-ghost" onClick={() => window.open(publicUrl, '_blank')}>View Event</button>
              <button type="button" className="btn-ghost" onClick={() => navigate('/admin/console')}>Back to Dashboard</button>
            </div>
          </motion.div>
        </div>
      </AdminLayout>
    );
  }

  if (step === 'creating' || step === 'uploading') {
    return (
      <AdminLayout title="Creating Event">
        <div className="admin-create">
          <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              style={{ width: '40px', height: '40px', border: '2px solid rgba(200,169,106,0.2)', borderTopColor: '#c8a96a', borderRadius: '50%', margin: '0 auto 1.5rem' }}
            />
            <p style={{ color: 'var(--color-gold, #c8a96a)', fontSize: '1.1rem' }}>
              {step === 'creating' ? 'Creating event in database…' : `Uploading ${selectedFiles.length} images…`}
            </p>
          </div>
        </div>
      </AdminLayout>
    );
  }

  if (step === 'error') {
    return (
      <AdminLayout title="Event Creation Failed">
        <div className="admin-create">
          <div style={{ textAlign: 'center', padding: '3rem 1rem', maxWidth: '500px', margin: '0 auto' }}>
            <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(201, 138, 138, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', fontSize: '1.8rem', color: '#c98a8a' }}>✗</div>
            <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--color-gold, #c8a96a)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '1rem' }}>Creation Failed</h2>
            <p style={{ color: '#c98a8a', marginBottom: '1.5rem' }}>{globalError}</p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button type="button" className="btn-primary" onClick={() => setStep('form')}>Try Again</button>
              <button type="button" className="btn-ghost" onClick={() => navigate('/admin/console')}>Cancel</button>
            </div>
          </div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="New Event">
      <div className="admin-create">
        <header className="admin-create__header">
          <div>
            <p className="admin-create__eyebrow">Create Event</p>
            <h1 className="admin-create__title">New Event</h1>
          </div>
        </header>

        <form className="admin-create__form" onSubmit={handleSubmit} noValidate>
          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-name">Event Name</label>
            <input id="create-name" className="guest-form__input" type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Adebayo & Amara" aria-invalid={errors.name ? true : undefined} />
            {errors.name && <p className="guest-form__error" role="alert">{errors.name}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-subtitle">Subtitle</label>
            <input id="create-subtitle" className="guest-form__input" type="text" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} placeholder="A short, emotional one-liner…" aria-invalid={errors.subtitle ? true : undefined} />
            {errors.subtitle && <p className="guest-form__error" role="alert">{errors.subtitle}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-host">Host Name</label>
            <input id="create-host" className="guest-form__input" type="text" value={hostName} onChange={(e) => setHostName(e.target.value)} placeholder="Assigned host" aria-invalid={errors.hostName ? true : undefined} />
            {errors.hostName && <p className="guest-form__error" role="alert">{errors.hostName}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-host-email">Host Email (for login)</label>
            <input id="create-host-email" className="guest-form__input" type="email" value={hostEmail} onChange={(e) => setHostEmail(e.target.value)} placeholder="host@lentis.gallery" aria-invalid={errors.hostEmail ? true : undefined} />
            {errors.hostEmail && <p className="guest-form__error" role="alert">{errors.hostEmail}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-host-password">Host Password</label>
            <input id="create-host-password" className="guest-form__input" type="password" value={hostPassword} onChange={(e) => setHostPassword(e.target.value)} placeholder="Min 10 characters" aria-invalid={errors.hostPassword ? true : undefined} />
            <label className="guest-form__label" htmlFor="create-host-password-confirm" style={{ marginTop: '0.5rem' }}>Confirm Password</label>
            <input id="create-host-password-confirm" className="guest-form__input" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Repeat password" autoComplete="new-password" />
            {errors.hostPassword && <p className="guest-form__error" role="alert">{errors.hostPassword}</p>}
            <p className="admin-create__field-hint">The host will use this email + password to log in and manage the event.</p>
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-date">Event Date</label>
            <input id="create-date" className="guest-form__input" type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)} aria-invalid={errors.eventDate ? true : undefined} />
            {errors.eventDate && <p className="guest-form__error" role="alert">{errors.eventDate}</p>}
          </div>

          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-slug">Slug (guest link)</label>
            <input id="create-slug" className="guest-form__input" type="text" value={effectiveSlug} onChange={(e) => setSlug(e.target.value)} placeholder="auto-generated from name" aria-invalid={errors.slug ? true : undefined} />
            <p className="admin-create__field-hint">Guest link: {getPublicBaseUrl()}/e/{effectiveSlug || '…'}</p>
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
            <label className="guest-form__label" htmlFor="create-landing-message">Landing Page Message</label>
            <textarea
              id="create-landing-message"
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

          <fieldset className="admin-create__field">
            <legend className="guest-form__label">Event Media</legend>
            <p className="admin-create__field-hint">
              Upload images and assign each to a page and role. The assignment controls where each image appears.
            </p>

            {selectedFiles.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem', marginTop: '0.75rem' }}>
                {selectedFiles.map((item, i) => (
                  <div key={i} style={{
                    position: 'relative', borderRadius: '6px', overflow: 'hidden',
                    border: `1px solid ${item.role === 'HERO' ? 'rgba(200,169,106,0.6)' : item.role === 'SLIDESHOW' ? 'rgba(126,175,105,0.4)' : item.role === 'HOST_SLIDESHOW' ? 'rgba(100,149,237,0.5)' : 'rgba(255,255,255,0.08)'}`,
                    background: '#1a1510',
                  }}>
                    <div style={{ aspectRatio: '1', overflow: 'hidden' }}>
                      <img src={item.preview} alt={item.file.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFile(i)}
                      style={{ position: 'absolute', top: '4px', right: '4px', width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(0,0,0,0.7)', color: '#c98a8a', border: 'none', cursor: 'pointer', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      aria-label={`Remove ${item.file.name}`}
                    >×</button>
                    <div style={{ padding: '6px' }}>
                      <p style={{ color: '#ccc', fontSize: '0.65rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '4px' }}>
                        {item.file.name}
                      </p>
                      <select
                        value={ROLE_PAGE_OPTIONS.findIndex((o) => o.role === item.role && o.page === item.page)}
                        onChange={(e) => setFileAssignment(i, parseInt(e.target.value))}
                        style={{ width: '100%', padding: '3px 4px', fontSize: '0.7rem', background: 'rgba(255,255,255,0.06)', color: '#ccc', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '4px', cursor: 'pointer' }}
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

            <label style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              marginTop: '0.75rem', padding: '0.6rem 1.2rem',
              background: 'rgba(200, 169, 106, 0.08)',
              border: '1px dashed rgba(200, 169, 106, 0.3)',
              borderRadius: '6px', cursor: 'pointer',
              color: 'var(--color-gold, #c8a96a)', fontSize: '0.85rem',
            }}>
              <input type="file" accept="image/*" multiple onChange={handleFileSelect} style={{ display: 'none' }} />
              + Choose Images
            </label>

            {selectedFiles.length > 0 && (
              <div style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-muted, #8a7e72)' }}>
                  <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'rgba(200,169,106,0.6)', marginRight: '4px', verticalAlign: 'middle' }} />
                  Hero
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-muted, #8a7e72)' }}>
                  <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'rgba(126,175,105,0.4)', marginRight: '4px', verticalAlign: 'middle' }} />
                  Landing Slideshow
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-muted, #8a7e72)' }}>
                  <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'rgba(100,149,237,0.5)', marginRight: '4px', verticalAlign: 'middle' }} />
                  Host Slideshow
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-muted, #8a7e72)' }}>
                  <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'rgba(255,255,255,0.12)', marginRight: '4px', verticalAlign: 'middle' }} />
                  Gallery
                </span>
              </div>
            )}
          </fieldset>

          <div className="admin-create__actions">
            <button type="submit" className="btn-primary" disabled={step !== 'form'}>
              Create Event
            </button>
            <button type="button" className="btn-ghost" onClick={() => navigate('/admin/console')}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </AdminLayout>
  );
}
