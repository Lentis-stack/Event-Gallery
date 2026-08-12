// ============================================================
// Lentis Gallery — Host StatCard
// ------------------------------------------------------------
// A single summary card used on the Host Overview dashboard.
// Displays a label, a large figure, and an optional hint.
// Matches the cinematic gold/dark design language.
// ============================================================

import type { ReactNode } from 'react';

interface StatCardProps {
  /** Card label, e.g. "Total Uploads". */
  label: string;
  /** Large numeric figure. */
  value: ReactNode;
  /** Optional small icon (inline SVG or emoji). */
  icon?: ReactNode;
  /** Optional footnote, e.g. "estimate". */
  hint?: string;
  /** Optional accent class for special cards. */
  accent?: boolean;
}

/**
 * A glassy summary card with a gold accent. Used in grids.
 */
export default function StatCard({ label, value, icon, hint, accent = false }: StatCardProps) {
  return (
    <div className={`stat-card${accent ? ' stat-card--accent' : ''}`}>
      {icon && <div className="stat-card__icon" aria-hidden="true">{icon}</div>}
      <div className="stat-card__value">{value}</div>
      <div className="stat-card__label">{label}</div>
      {hint && <div className="stat-card__hint">{hint}</div>}
    </div>
  );
}
