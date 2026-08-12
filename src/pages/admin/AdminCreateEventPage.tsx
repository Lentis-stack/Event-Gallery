// ============================================================
// Lentis Gallery — Admin Create Event Page
// ------------------------------------------------------------
// Lets the Lentis Admin create a new event.
// Includes:
//   - Name, subtitle, host name, date
//   - Theme choice
//   - Auto-generated slug (editable)
//   - Slideshow image selection from available assets
//   - Validation + create action (frontend-only, mock service)
//
// After creation, navigates to the admin console.
// ============================================================

import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../../components/admin/AdminLayout';
import { createEvent, slugify } from '../../services/mockAdminService';
import type { EventSlide, ThemeChoice } from '../../types/event';

const THEME_OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: 'gold', label: 'Gold' },
  { value: 'blue', label: 'Blue' },
  { value: 'rose', label: 'Rose' },
  { value: 'emerald', label: 'Emerald' },
];

/** Available slideshow images (from the public assets folder). */
const AVAILABLE_SLIDES: EventSlide[] = [
  { src: '/assets/event/Slideshow1.jpg', alt: 'Slideshow option 1' },
  { src: '/assets/event/Slideshow2.jpg', alt: 'Slideshow option 2' },
  { src: '/assets/event/Slideshow3.jpg', alt: 'Slideshow option 3' },
  { src: '/assets/event/Slideshow4.jpg', alt: 'Slideshow option 4' },
];

interface FormErrors {
  name?: string;
  subtitle?: string;
  hostName?: string;
  eventDate?: string;
  slug?: string;
  slides?: string;
}

export default function AdminCreateEventPage() {
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [hostName, setHostName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [slug, setSlug] = useState('');
  const [theme, setTheme] = useState<ThemeChoice>('gold');
  const [selectedSlides, setSelectedSlides] = useState<string[]>([]);

  const [errors, setErrors] = useState<FormErrors>({});
  const [creating, setCreating] = useState(false);

  // Auto-generate slug from the name (only if the user hasn't typed one).
  const autoSlug = useMemo(() => (name.trim() ? slugify(name) : ''), [name]);

  const effectiveSlug = slug.trim() ? slug.trim() : autoSlug;

  const toggleSlide = (src: string) => {
    setSelectedSlides((prev) =>
      prev.includes(src) ? prev.filter((s) => s !== src) : [...prev, src]
    );
  };

  const validate = (): boolean => {
    const next: FormErrors = {};
    if (name.trim().length < 3) next.name = 'Event name is required (min 3 characters).';
    if (subtitle.trim().length < 5) next.subtitle = 'Subtitle is required (min 5 characters).';
    if (hostName.trim().length < 2) next.hostName = 'Host name is required.';
    if (!eventDate) next.eventDate = 'Event date is required.';
    if (!effectiveSlug) next.slug = 'Slug is required.';
    if (selectedSlides.length === 0) next.slides = 'Select at least one slideshow image.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setCreating(true);
    const slides = AVAILABLE_SLIDES.filter((s) => selectedSlides.includes(s.src));

    createEvent({
      name: name.trim(),
      subtitle: subtitle.trim(),
      hostName: hostName.trim(),
      eventDate,
      slug: effectiveSlug,
      theme,
      slides,
    });

    // Simulate a short creation delay, then go to the console.
    window.setTimeout(() => navigate('/admin/console'), 600);
  };

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
          {/* Name */}
          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-name">Event Name</label>
            <input
              id="create-name"
              className="guest-form__input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. TARAGOLD 2026"
              aria-invalid={errors.name ? true : undefined}
              aria-describedby={errors.name ? 'create-name-error' : undefined}
            />
            {errors.name && (
              <p className="guest-form__error" id="create-name-error" role="alert">{errors.name}</p>
            )}
          </div>

          {/* Subtitle */}
          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-subtitle">Subtitle</label>
            <input
              id="create-subtitle"
              className="guest-form__input"
              type="text"
              value={subtitle}
              onChange={(e) => setSubtitle(e.target.value)}
              placeholder="A short, emotional one-liner…"
              aria-invalid={errors.subtitle ? true : undefined}
              aria-describedby={errors.subtitle ? 'create-subtitle-error' : undefined}
            />
            {errors.subtitle && (
              <p className="guest-form__error" id="create-subtitle-error" role="alert">{errors.subtitle}</p>
            )}
          </div>

          {/* Host name */}
          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-host">Host Name</label>
            <input
              id="create-host"
              className="guest-form__input"
              type="text"
              value={hostName}
              onChange={(e) => setHostName(e.target.value)}
              placeholder="Assigned host"
              aria-invalid={errors.hostName ? true : undefined}
              aria-describedby={errors.hostName ? 'create-host-error' : undefined}
            />
            {errors.hostName && (
              <p className="guest-form__error" id="create-host-error" role="alert">{errors.hostName}</p>
            )}
          </div>

          {/* Event date */}
          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-date">Event Date</label>
            <input
              id="create-date"
              className="guest-form__input"
              type="date"
              value={eventDate}
              onChange={(e) => setEventDate(e.target.value)}
              aria-invalid={errors.eventDate ? true : undefined}
              aria-describedby={errors.eventDate ? 'create-date-error' : undefined}
            />
            {errors.eventDate && (
              <p className="guest-form__error" id="create-date-error" role="alert">{errors.eventDate}</p>
            )}
          </div>

          {/* Slug */}
          <div className="admin-create__field">
            <label className="guest-form__label" htmlFor="create-slug">Slug (guest link)</label>
            <input
              id="create-slug"
              className="guest-form__input"
              type="text"
              value={effectiveSlug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="auto-generated from name"
              aria-invalid={errors.slug ? true : undefined}
              aria-describedby={errors.slug ? 'create-slug-error' : undefined}
            />
            <p className="admin-create__field-hint">Guest link: https://lentis.gallery/{effectiveSlug || '…'}</p>
            {errors.slug && (
              <p className="guest-form__error" id="create-slug-error" role="alert">{errors.slug}</p>
            )}
          </div>

          {/* Theme */}
          <fieldset className="admin-create__field">
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
          </fieldset>

          {/* Slideshow images */}
          <fieldset className="admin-create__field">
            <legend className="guest-form__label">Slideshow Images</legend>
            <div className="admin-create__slides">
              {AVAILABLE_SLIDES.map((s) => {
                const checked = selectedSlides.includes(s.src);
                return (
                  <label key={s.src} className={`admin-create__slide${checked ? ' is-selected' : ''}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleSlide(s.src)}
                      className="sr-only"
                    />
                    <img src={s.src} alt={s.alt} loading="lazy" />
                    <span className="admin-create__slide-check" aria-hidden="true">
                      {checked ? '✓' : ''}
                    </span>
                  </label>
                );
              })}
            </div>
            {errors.slides && (
              <p className="guest-form__error" role="alert">{errors.slides}</p>
            )}
          </fieldset>

          <div className="admin-create__actions">
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? 'Creating…' : 'Create Event'}
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
