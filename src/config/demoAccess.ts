// ============================================================
// Lentis Gallery — Demo Access Configuration
// ------------------------------------------------------------
// DEVELOPMENT-ONLY mock credentials for the Phase 1 frontend.
// These values are NOT secure and must never be used as real
// production credentials.
//
// FUTURE: Real authentication will be handled by the Python
// backend (hashed passwords, sessions/tokens, rate limiting).
// This file exists only so the login flows can be tested
// before the backend is available.
// ============================================================

export const demoAccess = {
  /** Demo password for the Event Host console. */
  hostPassword: 'lentis-hostdemo',
  /** Demo password for the Lentis Admin console. */
  adminPassword: 'lentis-admindemo',
} as const;
