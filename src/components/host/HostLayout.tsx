// ============================================================
// Lentis Gallery — HostLayout
// ============================================================
// Shared layout shell for the Event Host Console.
// Renders a top bar with the event name + a nav row linking
// to the console sections (Overview, Gallery, Settings, Share,
// Live). Content is rendered in a scrollable area.
//
// SECURITY: The Exit button now calls the real backend logout
// endpoint, which revokes the refresh token and clears the
// HttpOnly cookie. Previously it just navigated to /.
// ============================================================

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import type { Event } from "../../types/event";
import SiteFooter from "../SiteFooter";
import ImageSlideshow from "../ImageSlideshow";
import { logout } from "../../services/auth";
import { clearHostEmail } from "../../services/mockHostService";
import { getPublicHostSlideshow } from "../../services/api";

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
  { to: "/host/console", label: "Overview", end: true },
  { to: "/host/console/gallery", label: "Gallery", end: false },
  { to: "/host/console/settings", label: "Settings", end: false },
  { to: "/host/console/share", label: "Share", end: false },
  { to: "/host/console/export", label: "Export", end: false },
  { to: "/host/console/slideshow", label: "Live", end: false },
];

/**
 * Console layout: top bar (event name + exit) + nav + content + footer.
 * Uses NavLink for active styling.
 */
export default function HostLayout({ event, children, hideFooter = false }: HostLayoutProps) {
  const navigate = useNavigate();
  const [hostSlides, setHostSlides] = useState<Array<{ src: string; alt: string; id: string }>>([]);

  // Apply the event theme to the page so CSS variables update.
  useEffect(() => {
    document.body.setAttribute("data-theme", event.theme);
    return () => document.body.removeAttribute("data-theme");
  }, [event.theme]);

  // Fetch host slideshow images for background
  useEffect(() => {
    if (event.slug) {
      getPublicHostSlideshow(event.slug)
        .then(setHostSlides)
        .catch(() => setHostSlides([]));
    }
  }, [event.slug]);

  /**
   * Handle logout: call the backend to revoke the refresh token,
   * clear client-side auth state, and redirect to the login page.
   */
  const handleLogout = async () => {
    clearHostEmail();
    await logout();
    navigate(event.slug ? `/e/${event.slug}` : "/");
  };

  return (
    <div className="host-console" style={{ position: 'relative' }}>
      {/* Host slideshow background — shared across all Host Console pages */}
      {hostSlides.length > 0 && (
        <div
          className="host-console__slideshow-bg"
          style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}
        >
          <ImageSlideshow images={hostSlides} />
        </div>
      )}

      <header className="host-console__bar" style={{ position: 'relative', zIndex: 1 }}>
        <div className="host-console__brand">
          <span className="host-console__platform">Lentis Gallery</span>
          <span className="host-console__event">{event.name}</span>
        </div>
        <button onClick={handleLogout} className="host-console__exit" aria-label="Logout and exit host console">
          Logout
        </button>
      </header>

      <nav className="host-console__nav" aria-label="Host console sections" style={{ position: 'relative', zIndex: 1 }}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              "host-console__nav-link" + (isActive ? " is-active" : "")
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <motion.main
        className="host-console__content"
        style={{ position: 'relative', zIndex: 1 }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        {children}
      </motion.main>

      <SiteFooter hidden={hideFooter} />
    </div>
  );
}
