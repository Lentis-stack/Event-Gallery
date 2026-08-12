import type { ReactNode } from 'react';
import CinematicSlideshow from './CinematicSlideshow';

interface FilmShellProps {
  children: ReactNode;
  /** Use static background image instead of looping slideshow (e.g. camera page). */
  staticImage?: string;
  className?: string;
}

/**
 * Full-screen cinematic shell: a fixed photograph backdrop + overlay
 * with layered content on top. Keeps the same visual language on every page.
 */
export default function FilmShell({ children, staticImage, className = '' }: FilmShellProps) {
  return (
    <div className={`film-shell ${className}`.trim()}>
      <div className="film-backdrop" aria-hidden="true">
        {staticImage ? (
          <div className="film-backdrop__static">
            <img src={staticImage} alt="" />
          </div>
        ) : (
          <CinematicSlideshow />
        )}
        <div className="film-overlay" />
      </div>
      <div className="film-shell__content">{children}</div>
    </div>
  );
}
