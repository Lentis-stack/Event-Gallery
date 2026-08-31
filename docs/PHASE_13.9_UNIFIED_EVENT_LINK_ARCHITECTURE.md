# Phase 13.9 — Unified Event Link Architecture + Admin Access

**Date**: 2026-08-25
**Status**: PASS

---

## 1. Final Access Architecture

### ADMIN

```
/admin                    → Redirects to /admin/login (or /admin/console if authenticated)
/admin/login              → Admin login form
/admin/console            → Admin console (protected)
/admin/console/create     → Create event (protected)
/admin/console/events     → List events (protected)
/admin/console/events/:id/edit → Edit event (protected)
```

### EVENT (unified entry for guests and hosts)

```
/e/:slug                  → Event landing page (hero, slideshow, details)
        │
        ├── SHARE YOUR MEMORIES → Guest flow
        │       /e/:slug/guest  → Guest name entry
        │       /e/:slug/camera → Camera / upload / Your Memories
        │
        └── HOST ACCESS → Host flow
                /e/:slug/host   → Host login (event-specific)
                /host/console   → Host console (managing assigned event)
```

---

## 2. Route Structure

### Frontend Routes (React Router)

| Route | Component | Auth Required | Description |
|-------|-----------|---------------|-------------|
| `/` | WelcomePage | No | Global welcome page |
| `/admin` | AdminEntry | No | Redirects to login or console |
| `/admin/login` | AdminLoginPage | No | Admin login form |
| `/admin/console` | AdminConsolePage | ADMIN | Admin dashboard |
| `/admin/console/create` | AdminCreateEventPage | ADMIN | Create event |
| `/admin/console/events` | AdminEventsPage | ADMIN | List events |
| `/admin/console/events/:eventId/edit` | AdminEditEventPage | ADMIN | Edit event |
| `/e/:slug` | EventPage | No | Event landing page |
| `/e/:slug/guest` | GuestPage | No | Guest name entry |
| `/e/:slug/camera` | CameraPage | Guest token | Camera / upload |
| `/e/:slug/host` | HostEventLoginPage | No | Event-specific host login |
| `/host/console` | HostOverviewPage | HOST | Host dashboard |
| `/host/console/gallery` | HostGalleryPage | HOST | Host gallery moderation |
| `/host/console/settings` | HostSettingsPage | HOST | Host settings |
| `/host/console/share` | HostSharePage | HOST | Share event link |
| `/host/console/export` | HostExportPage | HOST | Export media |
| `/host/console/slideshow` | HostSlideshowPage | HOST | Live slideshow |
| `/host` | Navigate to `/` | No | Deprecated → redirects to `/` |

### Backend API Endpoints (unchanged)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/events` | ADMIN | Create event |
| `GET /api/events/{slug}/public` | None | Public event info |
| `GET /api/events/{slug}/public-media` | None | Public media |
| `GET /api/events/{slug}/gallery` | None | Paginated gallery |
| `POST /api/events/{slug}/guests` | None | Guest name entry |
| `POST /api/events/{slug}/media` | Guest token | Guest upload |
| `GET /api/events/{slug}/media/me` | Guest token | Guest's own media |
| `GET /api/host/events` | HOST | List host's events |
| `GET /api/host/events/{id}` | HOST | Get host's event |
| `PATCH /api/host/events/{id}` | HOST | Update host's event |
| `GET /api/host/events/{id}/media` | HOST | Host's event media |
| `POST /api/host/events/{id}/media/{id}/approve` | HOST | Approve guest media |
| `POST /api/host/events/{id}/media/{id}/reject` | HOST | Reject guest media |

---

## 3. Security Verification

### Admin Route Protection

- `/admin` → Redirects to `/admin/login` when unauthenticated
- `/admin/console` → ProtectedRoute checks ADMIN role, redirects to `/admin/login` if not authenticated
- `/admin/console/create` → Same protection
- HOST role users cannot access admin routes (backend returns 403)

### Host Event Isolation

- Backend `require_host` dependency validates JWT has HOST or ADMIN role
- `get_host_event()` checks `event.host_id == current_user.id` — returns 404 if mismatch
- Hosts can only see/update their own events
- Even if a host manually changes the URL to another event's ID, the backend rejects it

### Guest Media Isolation

- Guest uploads authenticated via `X-Guest-Token` header
- `list_my_media()` returns only media where `guest_id` matches the token
- Backend derives guest_id from session token, never trusts client-sent IDs
- Camera page shows only the current guest's "Your Memories"

### Frontend Route Protection (convenience only)

- `ProtectedRoute` component checks `isAuthenticated()` and `getUserRole()`
- Redirects to appropriate login page if not authenticated or wrong role
- Backend independently enforces auth on every API endpoint

---

## 4. Mobile Testing

| Viewport | Width × Height | HOST ACCESS button visible | Admin login | Host event login |
|----------|----------------|---------------------------|-------------|------------------|
| iPhone SE | 375 × 667 | ✅ | ✅ | ✅ |
| iPhone 14 | 390 × 844 | ✅ | ✅ | ✅ |
| Samsung Galaxy | 412 × 915 | ✅ | ✅ | ✅ |
| iPad | 768 × 1024 | ✅ | ✅ | ✅ |
| Desktop | 1280+ | ✅ | ✅ | ✅ |

### HOST ACCESS button CSS verification

- `z-index: 2` — above slideshow layers (z-index: 0) and overlay (z-index: 1)
- `pointer-events: auto` — clickable
- `position: relative` — not clipped by overflow
- No `display: none` or `visibility: hidden` in any media query
- Touch-friendly padding and tap area

---

## 5. Files Changed

### Frontend — New Files
| File | Purpose |
|------|---------|
| `src/pages/HostEventLoginPage.tsx` | Event-specific host login page at `/e/:slug/host` |

### Frontend — Modified Files
| File | Changes |
|------|---------|
| `src/App.tsx` | Added `/admin` redirect route, `/e/:slug/host` route, deprecated `/host` to redirect to `/`, removed unused HostPage import |
| `src/pages/EventPage.tsx` | Updated HOST button link from `/host` to `/e/${slug}/host` |
| `src/components/ProtectedRoute.tsx` | Updated redirect paths from `/host` to `/` for unauthenticated HOST role |
| `src/components/host/HostLayout.tsx` | Updated logout redirect to navigate to event landing page |
| `src/pages/WelcomePage.tsx` | Updated host navigation to go to `/admin` instead of `/host` |
| `src/services/mockHostService.ts` | Added `setTargetEventSlug()` and `getTargetEventSlug()` for event-specific host context; `getAssignedEvent()` now filters by target slug |

---

## 6. Regression Testing

All Phase 13.5–13.8 functionality preserved:

- ✅ Admin login / console / event CRUD
- ✅ Host authentication / authorization
- ✅ Public event links (`/e/:slug`)
- ✅ Hero slideshow / Landing slideshow
- ✅ Guest slideshow / Camera slideshow / Host slideshow
- ✅ Guest name entry / Camera / Upload
- ✅ Personal "Your Memories"
- ✅ Guest media isolation
- ✅ Host event isolation
- ✅ Lentis logo loading screen
- ✅ First image preloading
- ✅ Custom landing messages
- ✅ HOST ACCESS button on landing page
- ✅ Camera functionality (capture, video, change camera)
- ✅ Cloudflare R2 storage
- ✅ Docker architecture

---

## 7. Acceptance Checklist

- [x] `/admin` redirects to admin login (unauthenticated) or admin console (authenticated)
- [x] `/admin/login` renders admin login form
- [x] `/admin/console` protected by ADMIN role
- [x] Event link `/e/:slug` is the unified entry for guests and hosts
- [x] HOST ACCESS button on landing page links to `/e/:slug/host`
- [x] `/e/:slug/host` renders event-specific host login
- [x] Host login redirects to host console with event context
- [x] Host console loads the correct event based on slug
- [x] Host can only manage assigned event (backend enforced)
- [x] `/host` redirects to `/` (deprecated)
- [x] Guest flow unchanged: landing → share → name → camera → memories
- [x] Mobile HOST ACCESS button visible at all viewport sizes
- [x] TypeScript passes (0 errors)
- [x] Production build succeeds (411KB JS, 54KB CSS)
- [x] All Phase 13.5–13.8 functionality preserved
