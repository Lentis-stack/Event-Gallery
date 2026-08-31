// ============================================================
// Lentis Gallery — Authentication Service
// ============================================================
// This module handles ALL communication with the backend
// authentication API. It manages:
//
//   - Login (email + password -> JWT access token)
//   - Token storage (access token in memory, refresh via HttpOnly cookie)
//   - Automatic token refresh (before the 30-min expiry)
//   - Logout (revoke refresh token + clear state)
//
// SECURITY DESIGN:
//   - The ACCESS token is stored in memory (JS variable), NOT
//     localStorage. This means its lost on page refresh, which
//     is safer - an XSS attack cannot persist across refreshes.
//   - The REFRESH token travels in an HttpOnly cookie managed
//     by the browser. JavaScript never sees it.
//   - The refresh endpoint automatically rotates the cookie.
//   - All API calls use credentials: include to send the cookie.
// ============================================================

import { API_BASE } from './config';
import { extractErrorDetail } from './api';

// ============================================================
// Types
// ============================================================

/** User object returned by the backend after login. */
export interface AuthUser {
  id: string;
  email: string;
  role: 'ADMIN' | 'HOST';
  is_active: boolean;
  created_at: string;
}

/** Access token metadata from the backend. */
export interface AccessToken {
  access_token: string;
  token_type: string;
  expires_in: number; // seconds
}

/** Full login response from POST /api/auth/login. */
export interface LoginResponse {
  user: AuthUser;
  access_token: AccessToken;
}

/** Decoded JWT payload (what we extract client-side). */
interface TokenPayload {
  sub: string;
  role: string;
  exp: number;
}

// ============================================================
// Token management (in-memory only)
// ============================================================

/** The raw JWT access token string. Null when not authenticated. */
let _accessToken: string | null = null;

/** The decoded payload of the current access token. */
let _tokenPayload: TokenPayload | null = null;

/** Timestamp (ms) when the token expires - we refresh 60s before. */
let _tokenExpiresAt: number = 0;

/** Timer ID for automatic refresh scheduling. */
let _refreshTimer: ReturnType<typeof setTimeout> | null = null;

/** Callback fired when auth state changes (login/logout). */
let _onAuthChange: ((user: AuthUser | null) => void) | null = null;

// ============================================================
// Helpers
// ============================================================

/**
 * Decode a JWT payload WITHOUT verifying the signature.
 * We only decode to read claims (user id, role, expiry).
 * The BACKEND verifies the signature on every request.
 */
function decodeTokenPayload(token: string): TokenPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return {
      sub: payload.sub,
      role: payload.role,
      exp: payload.exp,
    };
  } catch {
    return null;
  }
}

/**
 * Schedule an automatic token refresh 60 seconds before expiry.
 * This keeps the session alive without the user noticing.
 */
function scheduleRefresh(expiresInSeconds: number) {
  if (_refreshTimer) clearTimeout(_refreshTimer);
  const refreshIn = Math.max((expiresInSeconds - 60) * 1000, 0);
  _refreshTimer = setTimeout(() => {
    refresh().catch(() => { clearAuth(); });
  }, refreshIn);
}

/** Clear all auth state (called on logout or token expiry). */
function clearAuth() {
  _accessToken = null;
  _tokenPayload = null;
  _tokenExpiresAt = 0;
  if (_refreshTimer) {
    clearTimeout(_refreshTimer);
    _refreshTimer = null;
  }
}

/** When true, the user has logged out and back-navigation is blocked. */
let _loggedOut = false;

/** Returns true if the user has logged out and should be redirected to login. */
export function isLoggedOut(): boolean {
  return _loggedOut;
}

/** Clear the logged-out flag (called when the user successfully logs in). */
export function clearLoggedOutFlag(): void {
  _loggedOut = false;
}

/** Set auth state from a login or refresh response. */
function setAuthFromResponse(data: LoginResponse | { access_token: AccessToken }) {
  const tokenData = data.access_token;
  _accessToken = tokenData.access_token;
  _tokenPayload = decodeTokenPayload(tokenData.access_token);
  _tokenExpiresAt = Date.now() + tokenData.expires_in * 1000;
  scheduleRefresh(tokenData.expires_in);
}

// ============================================================
// Public API
// ============================================================

/** Register a callback for auth state changes. */
export function onAuthChange(callback: (user: AuthUser | null) => void): () => void {
  _onAuthChange = callback;
  return () => { _onAuthChange = null; };
}

/**
 * Login with email + password.
 * Calls POST /api/auth/login, stores the access token in memory,
 * and the refresh token goes into an HttpOnly cookie automatically.
 * @throws {Error} with a message suitable for display to the user.
 */
export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(API_BASE + '/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // Send and receive cookies
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorDetail(body) || 'Login failed. Please try again.');
  }
  const data: LoginResponse = await res.json();
  setAuthFromResponse(data);
  _loggedOut = false;
  _onAuthChange?.(data.user);
  return data.user;
}

/**
 * Refresh the access token using the HttpOnly refresh cookie.
 * Called automatically before expiry, or manually if needed.
 */
export async function refresh(): Promise<void> {
  const res = await fetch(API_BASE + '/api/auth/refresh', {
    method: 'POST',
    credentials: 'include', // Must send the refresh cookie
  });
  if (!res.ok) {
    throw new Error('Session expired. Please log in again.');
  }
  const data = await res.json();
  setAuthFromResponse(data);
}

/** Logout: revoke the refresh token and clear client state. */
export async function logout(): Promise<void> {
  try {
    await fetch(API_BASE + '/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // Logout endpoint might fail - clear local state anyway.
  }
  clearAuth();
  _loggedOut = true;
  _onAuthChange?.(null);
  // Push a new history entry so the back button goes to the login page,
  // not to the protected page. Then clear history forward.
  window.history.replaceState(null, '', window.location.pathname);
}

/** Check if the user is currently authenticated (token exists and not expired). */
export function isAuthenticated(): boolean {
  if (!_accessToken || !_tokenPayload) return false;
  return Date.now() < _tokenExpiresAt;
}

/** Get the current access token (for attaching to API requests). */
export function getAccessToken(): string | null {
  if (!isAuthenticated()) return null;
  return _accessToken;
}

/** Get the current users role, or null if not authenticated. */
export function getUserRole(): 'ADMIN' | 'HOST' | null {
  if (!isAuthenticated() || !_tokenPayload) return null;
  return _tokenPayload.role as 'ADMIN' | 'HOST';
}

/** Get the current user info from the token payload. */
export function getCurrentUser(): AuthUser | null {
  if (!isAuthenticated() || !_tokenPayload) return null;
  return {
    id: _tokenPayload.sub,
    email: '',
    role: _tokenPayload.role as 'ADMIN' | 'HOST',
    is_active: true,
    created_at: '',
  };
}

/** Build headers for an authenticated API request. */
export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  if (!token) return {};
  return { Authorization: 'Bearer ' + token };
}
/** Create a host user via the backend API (admin-only endpoint). */
export async function createHostUser(email: string, password: string): Promise<void> {
  const token = getAccessToken();
  if (!token) throw new Error('Not authenticated');
  
  const res = await fetch(API_BASE + '/api/auth/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
    },
    credentials: 'include',
    body: JSON.stringify({ email, password, role: 'HOST' }),
  });
  
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // 409 = already exists, which is fine
    if (res.status === 409) return;
    throw new Error(extractErrorDetail(body) || 'Failed to create host user');
  }
}

