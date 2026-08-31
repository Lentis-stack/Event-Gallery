// ============================================================
// Lentis Gallery — AdminLayout
// ============================================================
// Shared layout shell for the Lentis Admin Console.
// Renders a distinct platform header (with "Lentis Admin"
// branding + logout) and a nav row linking to the admin
// sections (Overview, Events, Create Event).
//
// SECURITY: The Logout button calls the real backend logout
// endpoint, which revokes the refresh token and clears the
// HttpOnly cookie.
// ============================================================

import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { logout } from "../../services/auth";

interface AdminLayoutProps {
  children: ReactNode;
  /** Optional page title shown in the header. */
  title?: string;
}

const NAV_ITEMS = [
  { to: "/admin/console", label: "Overview", end: true },
  { to: "/admin/console/events", label: "Events", end: false },
  { to: "/admin/console/create", label: "New Event", end: false },
  { to: "/admin/console/archive", label: "Archive", end: false },
];

/**
 * Admin console layout: platform header + nav + content.
 */
export default function AdminLayout({ children, title }: AdminLayoutProps) {
  const navigate = useNavigate();

  /**
   * Handle logout: call the backend to revoke the refresh token,
   * clear client-side auth state, and redirect to the home page.
   */
  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="admin-console">
      {/* Subtle Lentis logo background watermark */}
      <div className="admin-console__bg">
        <img src="/assets/event/LentisLogo.png" alt="" className="admin-console__bg-logo" />
      </div>

      <header className="admin-console__bar">
        <div className="admin-console__brand">
          <img src="/assets/event/LentisLogo.png" alt="Lentis" className="admin-console__logo" />
          <span className="admin-console__platform">ADMIN</span>
          {title && <span className="admin-console__title">{title}</span>}
        </div>
        <button onClick={handleLogout} className="admin-console__exit" aria-label="Logout and exit admin console">
          Logout
        </button>
      </header>

      <nav className="admin-console__nav" aria-label="Admin console sections">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              "admin-console__nav-link" + (isActive ? " is-active" : "")
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
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        {children}
      </motion.main>
    </div>
  );
}
