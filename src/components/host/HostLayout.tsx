// ============================================================
// Lentis Gallery — HostLayout
// ------------------------------------------------------------
// Shared layout shell for the Event Host Console.
// Renders a top bar with the event name + a nav row linking
// to the console sections (Overview, Gallery, Settings, Share,
// Live). Content is rendered in a scrollable area.
//
// This keeps every host page consistent and avoids duplicating
// the header/nav on each page.
// ============================================================

import type { ReactNode } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { Event } from '../../types/event';
import SiteFooter from '../SiteFooter';

interface HostLayoutProps {
  event: Event;
  /** Active nav item label (used for mobile/compact display if needed). */
  children: ReactNode;
  /**
   * When true, the SiteFooter is hidden — used during the full-screen
   * Live slideshow so it does not distract from the event display.
   */
  hideFooter?: boolean;
}

const NAV_ITEMS = [
  { to: '/host/console', label: 'Overview', end: true },
  { to: '/host/console/gallery', label: 'Gallery', end: false },
  { to: '/host/console/settings', label: 'Settings', end: false },
  { to: '/host/console/share', label: 'Share', end: false },
  { to: '/host/console/export', label: 'Export', end: false },
  { to: '/host/console/slideshow', label: 'Live', end: false },
];

/**
 * Console layout: top bar (event name + exit) + nav + content + footer.
 * Uses NavLink for active styling.
 */
export default function HostLayout({ event, children, hideFooter = false }: HostLayoutProps) {
  return (
    <div className="host-console">
      <header className="host-console__bar">
        <div className="host-console__brand">
          <span className="host-console__platform">Lentis Gallery</span>
          <span className="host-console__event">{event.name}</span>
        </div>
        <Link to="/" className="host-console__exit" aria-label="Exit host console">
          Exit
        </Link>
      </header>

      <nav className="host-console__nav" aria-label="Host console sections">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `host-console__nav-link${isActive ? ' is-active' : ''}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

<motion.main
        className="host-console__content"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      >
        {children}
      </motion.main>

      <SiteFooter hidden={hideFooter} />
    </div>
  );
}
