// ============================================================
// Lentis Gallery — AdminLayout
// ------------------------------------------------------------
// Shared layout shell for the Lentis Admin Console.
// Renders a distinct platform header (with "Lentis Admin"
// branding + exit) and a nav row linking to the admin
// sections (Overview, Events, Create Event).
//
// This gives the admin console a distinct feel from the
// host console while sharing the cinematic gold/dark language.
// ============================================================

import type { ReactNode } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { motion } from 'framer-motion';

interface AdminLayoutProps {
  children: ReactNode;
  /** Optional page title shown in the header. */
  title?: string;
}

const NAV_ITEMS = [
  { to: '/admin/console', label: 'Overview', end: true },
  { to: '/admin/console/events', label: 'Events', end: false },
  { to: '/admin/console/create', label: 'New Event', end: false },
];

/**
 * Admin console layout: platform header + nav + content.
 */
export default function AdminLayout({ children, title }: AdminLayoutProps) {
  return (
    <div className="admin-console">
      <header className="admin-console__bar">
        <div className="admin-console__brand">
          <span className="admin-console__platform">LENTIS ADMIN</span>
          {title && <span className="admin-console__title">{title}</span>}
        </div>
        <Link to="/" className="admin-console__exit" aria-label="Exit admin console">
          Exit
        </Link>
      </header>

      <nav className="admin-console__nav" aria-label="Admin console sections">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `admin-console__nav-link${isActive ? ' is-active' : ''}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <motion.main
        className="admin-console__content"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      >
{children}
      </motion.main>
    </div>
  );
}
