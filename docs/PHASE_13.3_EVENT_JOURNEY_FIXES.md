# Phase 13.3 — Event Journey Fixes

**Date**: 2026-08-24  
**Status**: ✅ Complete  
**Issues Fixed**: 4 functional issues in the event journey

---

## Summary

Fixed 4 functional issues preventing the complete event journey from working:
1. Slideshow media role selection in admin event creation
2. Broken admin delete button
3. Broken guest navigation (inline modal instead of dedicated page)
4. Wrong generated event link (used localhost instead of production domain)

---

## Issue 1: Slideshow Media Role Selection

**Root Cause**: `uploadFilesToEvent()` defaulted all uploads to `GALLERY` role. No role selection UI existed in the create event form.

**Fix**:
- Added per-file `fileRoles` state to `AdminCreateEventPage.tsx`
- Added role selector dropdown (Hero/Slideshow/Gallery) for each uploaded image
- Default role is Gallery; admin explicitly selects Hero and Slideshow
- Updated `uploadFilesToEvent()` in `mockAdminService.ts` to accept per-file roles
- Added visual indicators: gold border for Hero, green for Slideshow, neutral for Gallery
- Added role legend below image previews

**Files Modified**:
- `src/pages/admin/AdminCreateEventPage.tsx` — Role selector UI, per-file role state
- `src/services/mockAdminService.ts` — `uploadFilesToEvent()` accepts `fileRoles` parameter

---

## Issue 2: Admin Delete Button

**Root Cause**: `deleteEvent()` in `mockAdminService.ts` literally threw `"Event deletion is not supported. Use archive instead."` — no backend DELETE endpoint existed.

**Fix**:
- Added `DELETE /api/admin/events/{event_id}` endpoint (soft-delete/archive)
- Added `DELETE /api/admin/events/{event_id}/permanent` endpoint (irreversible)
- Added `permanent_delete_event()` in `events.py` service
- Updated `deleteEvent()` in `mockAdminService.ts` to call backend API
- Added `deleteEvent()` and `permanentDeleteEvent()` functions in `api.ts`
- Updated confirmation dialog message to reflect soft-delete behavior

**Files Modified**:
- `backend/app/services/events.py` — Added `permanent_delete_event()` function
- `backend/app/api/routes/admin_events.py` — Added DELETE endpoints
- `src/services/api.ts` — Added `deleteEvent()` and `permanentDeleteEvent()` functions
- `src/services/mockAdminService.ts` — Fixed `deleteEvent()` to call backend
- `src/pages/admin/AdminConsolePage.tsx` — Updated dialog message

---

## Issue 3: Guest Navigation

**Root Cause**: EventPage "Share Your Memories" button opened inline upload modal (`setShowUpload(true)`) instead of navigating to `/e/:slug/guest`.

**Fix**:
- Changed button to navigate to `/e/${slug}/guest` using React Router
- Removed inline upload modal (guest name entry, file upload, camera capture)
- Removed unused state variables and handlers
- Removed `CameraCapture` component import (no longer needed on EventPage)
- Kept gallery display and lightbox functionality

**Flow**: EventPage → `/e/:slug/guest` → Name Entry → Guest Session → Camera → Upload

**Files Modified**:
- `src/pages:EventPage.tsx` — Removed inline modal, added navigation to GuestPage

---

## Issue 4: Wrong Generated Event Link

**Root Cause**: `publicUrl` in `AdminCreateEventPage.tsx` used `window.location.origin` which returns `http://localhost:5173` in Vite dev mode.

**Fix**:
- Changed `publicUrl` to use `getPublicBaseUrl()` from `config.ts`
- `getPublicBaseUrl()` reads `VITE_PUBLIC_URL` env var (set to `https://lentisevent.gallery` in production)
- In Docker production: returns `https://lentisevent.gallery`
- In Vite dev: falls back to `window.location.origin` (acceptable for dev testing)

**Files Modified**:
- `src/pages/admin/AdminCreateEventPage.tsx` — Uses `getPublicBaseUrl()` for event URL

---

## Verification Results

| Test | Result |
|------|--------|
| TypeScript check | ✅ Pass |
| Production build | ✅ Pass |
| Docker rebuild | ✅ Pass (all 6 services healthy) |
| Admin login | ✅ Pass |
| Delete button + confirmation dialog | ✅ Pass (shows soft-delete message) |
| Guest navigation | ✅ Pass (navigates to `/e/:slug/guest`) |
| Guest name entry form | ✅ Pass |
| Create event page | ✅ Pass (form loads with all fields) |
| Event URL generation | ✅ Uses `getPublicBaseUrl()` |

---

## Files Changed

### Backend
- `backend/app/services/events.py` — Added `permanent_delete_event()`
- `backend/app/api/routes/admin_events.py` — Added DELETE endpoints

### Frontend
- `src/pages/EventPage.tsx` — Removed inline modal, added GuestPage navigation
- `src/pages/admin/AdminCreateEventPage.tsx` — Added role selector, fixed event URL
- `src/services/api.ts` — Added `deleteEvent()`, `permanentDeleteEvent()`
- `src/services/mockAdminService.ts` — Fixed `deleteEvent()`, updated `uploadFilesToEvent()`
- `src/pages/admin/AdminConsolePage.tsx` — Updated delete dialog message
