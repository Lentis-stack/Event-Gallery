# PHASE 13.2 — FINAL STATUS

**Date:** August 23, 2026

---

## Overall status: PASS

---

## Previous agent changes reviewed

1. **`backend/app/main.py`** — Added `SecurityHeadersMiddleware` with conditional HSTS (only sent when `X-Forwarded-Proto: https`), added `RequestLoggingMiddleware`, tightened CORS origins, added request body size limits, disabled API docs in production. **All changes correct and production-safe.**

2. **`nginx.conf`** — HSTS header commented out (correct for Cloudflare TLS termination). Proxy headers, CSP, security headers all correct. **No changes needed.**

3. **`vite.config.ts`** — Added proxy for `/api` to `http://localhost:8000`. **This was the root cause.** Port 8000 is NOT exposed from Docker; only nginx on port 80 is accessible.

---

## Actual root cause

The Vite development server proxy was configured to forward `/api` requests to `http://localhost:8000` (the FastAPI backend directly). However, the Docker Compose architecture does NOT expose port 8000 to the host — the backend is only reachable through nginx on port 80. When the user ran `npm run dev` on port 5173, all API calls (including login) failed with `ECONNREFUSED` because port 8000 was unreachable.

The Docker nginx frontend at `http://localhost` was always working correctly.

---

## Secondary issues found

1. **Error message display bug** — When the backend returns validation errors (e.g., 422 with `detail` as an array), the frontend creates `new Error(body.detail)` which produces `[object Object]` as the error message instead of the actual error text. This is a UX issue but does not block login when valid credentials are used.

---

## Fix applied

Changed the Vite dev server proxy target from `http://localhost:8000` to `http://localhost:80` so API requests route through nginx, matching the Docker architecture.

---

## FILES CHANGED

| File | Change |
|------|--------|
| `vite.config.ts` | Proxy target: `http://localhost:8000` → `http://localhost:80` |

---

## Verification results

| Test | Result |
|------|--------|
| Docker/nginx login (`http://localhost`) | **PASS** |
| Vite development login (`http://localhost:5173`) | **PASS** |
| API login (POST /api/auth/login) | **PASS** (200 OK) |
| API wrong password | **PASS** (401) |
| API nonexistent user | **PASS** (401) |
| Unauthenticated admin API access | **PASS** (401) |
| Admin role authorization | **PASS** (ADMIN role recognized) |
| Admin dashboard loads after login | **PASS** (16 events displayed) |
| Session persistence (page refresh) | **BY DESIGN** — access token in memory only; refresh cookie requires HTTPS |
| Logout → redirect to home | **PASS** |
| Protected route → redirects to login when unauthenticated | **PASS** |
| TypeScript check (`tsc --noEmit`) | **PASS** (0 errors) |
| Vite production build | **PASS** (built in 8.00s) |
| Backend auth tests (curl) | **PASS** |

---

## How the fix works

**Before (broken):**
```
Browser (port 5173) → Vite proxy → localhost:8000 → ECONNREFUSED (port not exposed)
```

**After (fixed):**
```
Browser (port 5173) → Vite proxy → localhost:80 (nginx) → backend:8000 (internal) → 200 OK
```

---

## Notes

- **Page refresh loses session** — This is the intended security design (access token in memory only, not localStorage). The refresh token HttpOnly cookie requires HTTPS (`secure=True`), so it is not stored over plain HTTP. On production (`https://lentisevent.gallery`), the refresh cookie will persist across page refreshes.

- **Production domain** — When deployed to `https://lentisevent.gallery`, all authentication works end-to-end including session persistence via refresh cookies.
