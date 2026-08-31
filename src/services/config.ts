// ============================================================
// Lentis Gallery — API Configuration
// ============================================================
// Central place for the backend API base URL.
//
// In development, Vite proxies /api to localhost:8000 (see
// vite.config.ts), so we can use an empty string as the base.
// In production, set VITE_API_BASE to the full backend URL.
//
// SECURITY: This value is embedded in the built JS bundle.
// Never put secrets here — only public URLs.
// ============================================================

/** Base URL for all backend API calls. */
export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? "";

/**
 * Public base URL for generating guest-facing event links.
 *
 * Resolution order:
 *   1. VITE_PUBLIC_URL (embedded at build time by Vite)
 *   2. Runtime-injected placeholder (replaced by docker-entrypoint.sh)
 *   3. window.location.origin (works in dev and same-origin prod)
 *
 * For Docker deployments, set VITE_PUBLIC_URL at build time:
 *   docker build --build-arg VITE_PUBLIC_URL=https://lentis.gallery
 *
 * Or at runtime via the entrypoint script.
 */
export function getPublicBaseUrl(): string {
  // Check Vite build-time env var
  const configured = (import.meta as any).env?.VITE_PUBLIC_URL;
  if (configured && configured !== '__VITE_PUBLIC_URL__') {
    return configured.replace(/\/$/, '');
  }
  // Fallback: use the current page origin
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin;
  }
  return '';
}
