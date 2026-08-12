// ============================================================
// Lentis Gallery — Host Settings Page
// ------------------------------------------------------------
// Editable event settings for the assigned event.
// Supports editing the event name, subtitle, and theme choice.
// Includes basic validation and a save action (frontend-only,
// updates module state via the mock host service).
// ============================================================

import { useState } from 'react';
import HostLayout from '../../components/host/HostLayout';
import {
  getAssignedEvent,
  updateAssignedEvent,
} from '../../services/mockHostService';
import type { ThemeChoice } from '../../types/event';

const THEME_OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: 'gold', label: 'Gold' },
  { value: 'blue', label: 'Blue' },
  { value: 'rose', label: 'Rose' },
  { value: 'emerald', label: 'Emerald' },
];

export default function HostSettingsPage() {
  const [event] = useState(() => getAssignedEvent());

  const [name, setName] = useState(event.name);
  const [subtitle, setSubtitle] = useState(event.subtitle);
  const [theme, setTheme] = useState<ThemeChoice>(event.theme);

  const [errors, setErrors] = useState<{ name?: string; subtitle?: string }>({});
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);

  const validate = () => {
    const next: { name?: string; subtitle?: string } = {};
    if (name.trim().length < 3) {
      next.name = 'Event name must be at least 3 characters.';
    }
    if (subtitle.trim().length < 5) {
      next.subtitle = 'Subtitle must be at least 5 characters.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;
    updateAssignedEvent({ name: name.trim(), subtitle: subtitle.trim(), theme });
    setSaved(true);
    setDirty(false);
    // Reset the "saved" indicator after a moment.
    window.setTimeout(() => setSaved(false), 2500);
  };

  return (
    <HostLayout event={event}>
      <div className="host-settings">
        <header className="host-settings__header">
          <div>
            <p className="host-settings__eyebrow">Event Settings</p>
            <h1 className="host-settings__title">Customize</h1>
          </div>
        </header>

        <form
          className="host-settings__form"
          onSubmit={(e) => {
            e.preventDefault();
            handleSave();
          }}
          noValidate
        >
          <div className="host-settings__field">
            <label className="guest-form__label" htmlFor="settings-name">
              Event Name
            </label>
            <input
              id="settings-name"
              className="guest-form__input"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setDirty(true);
              }}
              aria-invalid={errors.name ? true : undefined}
              aria-describedby={errors.name ? 'settings-name-error' : undefined}
            />
            {errors.name && (
              <p className="guest-form__error" id="settings-name-error" role="alert">
                {errors.name}
              </p>
            )}
          </div>

          <div className="host-settings__field">
            <label className="guest-form__label" htmlFor="settings-subtitle">
              Subtitle
            </label>
            <input
              id="settings-subtitle"
              className="guest-form__input"
              type="text"
              value={subtitle}
              onChange={(e) => {
                setSubtitle(e.target.value);
                setDirty(true);
              }}
              aria-invalid={errors.subtitle ? true : undefined}
              aria-describedby={errors.subtitle ? 'settings-subtitle-error' : undefined}
            />
            {errors.subtitle && (
              <p className="guest-form__error" id="settings-subtitle-error" role="alert">
                {errors.subtitle}
              </p>
            )}
          </div>

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
                    onChange={() => {
                      setTheme(opt.value);
                      setDirty(true);
                    }}
                  />
                  <span className={`host-settings__swatch host-settings__swatch--${opt.value}`} aria-hidden="true" />
                  {opt.label}
                </label>
              ))}
            </div>
          </fieldset>

          <div className="host-settings__actions">
            <button
              type="submit"
              className="btn-primary"
              disabled={!dirty}
            >
              Save Changes
            </button>
            {saved && <span className="host-settings__saved" role="status">Saved ✓</span>}
          </div>
        </form>
      </div>
    </HostLayout>
  );
}
