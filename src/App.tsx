// ============================================================
// Lentis Gallery — App Router
// ============================================================
// Central routing for the entire SPA. Uses React Router v6.
//
// ARCHITECTURE (Phase 13.9):
//   /admin                    → Admin entry (redirects to login or console)
//   /admin/login              → Admin login form
//   /admin/console            → Admin console (protected)
//   /e/:slug                  → Event landing (guest + host entry)
//   /e/:slug/host             → Host login for specific event
//   /e/:slug/guest            → Guest name entry
//   /e/:slug/camera           → Camera / upload
//   /host/console             → Host console (protected, legacy)
//
// SECURITY: Admin and Host console routes are wrapped in
// ProtectedRoute, which checks for a valid JWT before rendering.
// The backend independently enforces auth on every protected API endpoint.
// ============================================================

import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";

// Public pages (no auth required)
import WelcomePage from "./pages/WelcomePage";
import GuestPage from "./pages/GuestPage";
import PrivateGuestLoginPage from "./pages/PrivateGuestLoginPage";
import CameraPage from "./pages/CameraPage";
import EventPage from "./pages/EventPage";

// Login pages (no auth required — these ARE the login forms)
import HostEventLoginPage from "./pages/HostEventLoginPage";
import AdminLoginPage from "./pages/admin/AdminLoginPage";

// Protected pages (auth required)
import ProtectedRoute from "./components/ProtectedRoute";
import HostOverviewPage from "./pages/host/HostOverviewPage";
import HostGalleryPage from "./pages/host/HostGalleryPage";
import HostSettingsPage from "./pages/host/HostSettingsPage";
import HostSharePage from "./pages/host/HostSharePage";
import HostExportPage from "./pages/host/HostExportPage";
import HostSlideshowPage from "./pages/host/HostSlideshowPage";
import AdminConsolePage from "./pages/admin/AdminConsolePage";
import AdminCreateEventPage from "./pages/admin/AdminCreateEventPage";
import AdminEventsPage from "./pages/admin/AdminEventsPage";
import AdminEditEventPage from "./pages/admin/AdminEditEventPage";
import AdminArchivePage from "./pages/admin/AdminArchivePage";

// Auth helper for /admin redirect
import { isAuthenticated, getUserRole } from "./services/auth";

/**
 * /admin entry point: redirects to console if authenticated,
 * otherwise to login page.
 */
function AdminEntry() {
  if (isAuthenticated() && getUserRole() === "ADMIN") {
    return <Navigate to="/admin/console" replace />;
  }
  return <Navigate to="/admin/login" replace />;
}

export default function App() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* === PUBLIC ROUTES === */}
        <Route path="/" element={<WelcomePage />} />
        <Route path="/e/:slug" element={<EventPage />} />
        <Route path="/e/:slug/guest" element={<GuestPage />} />
        <Route path="/e/:slug/guest-login" element={<PrivateGuestLoginPage />} />
        <Route path="/e/:slug/camera" element={<CameraPage />} />

        {/* === ADMIN ENTRY (permanent) === */}
        <Route path="/admin" element={<AdminEntry />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />

        {/* === HOST EVENT-SPECIFIC LOGIN === */}
        <Route path="/e/:slug/host" element={<HostEventLoginPage />} />

        {/* === PROTECTED: HOST CONSOLE === */}
        <Route path="/host/console" element={
          <ProtectedRoute requiredRole="HOST">
            <HostOverviewPage />
          </ProtectedRoute>
        } />
        <Route path="/host/console/gallery" element={
          <ProtectedRoute requiredRole="HOST">
            <HostGalleryPage />
          </ProtectedRoute>
        } />
        <Route path="/host/console/settings" element={
          <ProtectedRoute requiredRole="HOST">
            <HostSettingsPage />
          </ProtectedRoute>
        } />
        <Route path="/host/console/share" element={
          <ProtectedRoute requiredRole="HOST">
            <HostSharePage />
          </ProtectedRoute>
        } />
        <Route path="/host/console/export" element={
          <ProtectedRoute requiredRole="HOST">
            <HostExportPage />
          </ProtectedRoute>
        } />
        <Route path="/host/console/slideshow" element={
          <ProtectedRoute requiredRole="HOST">
            <HostSlideshowPage />
          </ProtectedRoute>
        } />

        {/* === PROTECTED: ADMIN CONSOLE === */}
        <Route path="/admin/console" element={
          <ProtectedRoute requiredRole="ADMIN">
            <AdminConsolePage />
          </ProtectedRoute>
        } />
        <Route path="/admin/console/events" element={
          <ProtectedRoute requiredRole="ADMIN">
            <AdminEventsPage />
          </ProtectedRoute>
        } />
        <Route path="/admin/console/events/:eventId/edit" element={
          <ProtectedRoute requiredRole="ADMIN">
            <AdminEditEventPage />
          </ProtectedRoute>
        } />
        <Route path="/admin/console/create" element={
          <ProtectedRoute requiredRole="ADMIN">
            <AdminCreateEventPage />
          </ProtectedRoute>
        } />
        <Route path="/admin/console/archive" element={
          <ProtectedRoute requiredRole="ADMIN">
            <AdminArchivePage />
          </ProtectedRoute>
        } />

        {/* === LEGACY: /host redirects to event entry === */}
        <Route path="/host" element={<Navigate to="/" replace />} />

        {/* === FALLBACK === */}
        <Route path="*" element={<WelcomePage />} />
      </Routes>
    </AnimatePresence>
  );
}
