// ============================================================
// Lentis Gallery — Event Countdown Component
// ============================================================
// Reusable countdown component that displays time remaining
// until an event's scheduled date. Handles all lifecycle states:
// - Future event: shows countdown (DDd HHh MMm SSs)
// - Event day (not started): "EVENT DAY — READY TO BEGIN"
// - Live: "EVENT IS LIVE"
// - Ended: "EVENT ENDED"
// - Archived: no countdown (null render)
// ============================================================

import { useState, useEffect, useMemo } from 'react';

interface EventCountdownProps {
  /** Event date in YYYY-MM-DD format (from backend) */
  eventDate: string;
  /** Current event status */
  status: 'not_started' | 'live' | 'ended' | 'archived' | 'draft' | string;
  /** Compact mode for admin event cards */
  compact?: boolean;
  /** Custom className for styling variations */
  className?: string;
}

export default function EventCountdown({
  eventDate,
  status,
  compact = false,
  className = '',
}: EventCountdownProps) {
  const [now, setNow] = useState<Date>(new Date());

  // Update every second
  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Parse event date (assumes local date, treat as start of day in local timezone)
  const eventDateTime = useMemo(() => {
    if (!eventDate) return null;
    const parts = eventDate.split('-').map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) return null;
    const [year, month, day] = parts;
    // Create date at start of day (00:00:00) in local timezone
    return new Date(year, month - 1, day, 0, 0, 0);
  }, [eventDate]);

  const diffMs = eventDateTime ? eventDateTime.getTime() - now.getTime() : 0;

  // Determine display state
  if (!eventDateTime) {
    return null; // Invalid or missing date
  }

  const isFuture = diffMs > 0;
  const isEventDay = diffMs <= 0 && diffMs > -24 * 60 * 60 * 1000; // Within 24h of event date
  const isPast = diffMs <= -24 * 60 * 60 * 1000;

  let label = '';
  let value = '';
  let variant: 'countdown' | 'event-day' | 'live' | 'ended' | null = null;

  if (status === 'archived') {
    return null; // No countdown for archived events
  }

  if (status === 'live') {
    variant = 'live';
    label = compact ? 'LIVE' : 'EVENT IS LIVE';
  } else if (status === 'ended') {
    variant = 'ended';
    label = compact ? 'ENDED' : 'EVENT ENDED';
  } else if (isFuture) {
    variant = 'countdown';
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);

    if (compact) {
      const parts = [];
      if (days > 0) parts.push(`${days}d`);
      if (hours > 0 || days > 0) parts.push(`${String(hours).padStart(2, '0')}h`);
      parts.push(`${String(minutes).padStart(2, '0')}m`);
      parts.push(`${String(seconds).padStart(2, '0')}s`);
      value = parts.join(' ');
    } else {
      label = 'EVENT STARTS IN';
      value = `${String(days).padStart(2, '0')} : ${String(hours).padStart(2, '0')} : ${String(minutes).padStart(2, '0')} : ${String(seconds).padStart(2, '0')}`;
    }
  } else if (isEventDay) {
    variant = 'event-day';
    label = compact ? 'EVENT DAY' : 'EVENT DAY — READY TO BEGIN';
  } else if (isPast && status !== 'ended' && status !== 'archived') {
    // Event date has passed but status not updated yet
    variant = 'event-day';
    label = compact ? 'EVENT DAY' : 'EVENT DAY — READY TO BEGIN';
  }

  if (!variant) return null;

  const baseClass = compact
    ? 'event-countdown event-countdown--compact'
    : 'event-countdown';

  const variantClass = variant ? `event-countdown--${variant}` : '';

  return (
    <div className={`${baseClass} ${variantClass} ${className}`.trim()}>
      {label && <span className="event-countdown__label">{label}</span>}
      {value && <span className="event-countdown__value">{value}</span>}
      {label && !value && <span className="event-countdown__value event-countdown__value--text">{label}</span>}
    </div>
  );
}