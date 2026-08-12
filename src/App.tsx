import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import WelcomePage from './pages/WelcomePage';
import GuestPage from './pages/GuestPage';
import CameraPage from './pages/CameraPage';
import HostPage from './pages/HostPage';
import HostPlaceholderPage from './pages/HostPlaceholderPage';
import HostOverviewPage from './pages/host/HostOverviewPage';
import HostGalleryPage from './pages/host/HostGalleryPage';
import HostSettingsPage from './pages/host/HostSettingsPage';
import HostSharePage from './pages/host/HostSharePage';
import HostExportPage from './pages/host/HostExportPage';
import HostSlideshowPage from './pages/host/HostSlideshowPage';
import AdminLoginPage from './pages/admin/AdminLoginPage';
import AdminConsolePage from './pages/admin/AdminConsolePage';
import AdminCreateEventPage from './pages/admin/AdminCreateEventPage';

export default function App() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/guest" element={<GuestPage />} />
        <Route path="/guest/camera" element={<CameraPage />} />
        <Route path="/host" element={<HostPage />} />
        <Route path="/host/placeholder" element={<HostPlaceholderPage />} />
        <Route path="/host/console" element={<HostOverviewPage />} />
        <Route path="/host/console/gallery" element={<HostGalleryPage />} />
        <Route path="/host/console/settings" element={<HostSettingsPage />} />
        <Route path="/host/console/share" element={<HostSharePage />} />
        <Route path="/host/console/export" element={<HostExportPage />} />
        <Route path="/host/console/slideshow" element={<HostSlideshowPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin/console" element={<AdminConsolePage />} />
        <Route path="/admin/console/create" element={<AdminCreateEventPage />} />
        <Route path="*" element={<WelcomePage />} />
      </Routes>
    </AnimatePresence>
  );
}
