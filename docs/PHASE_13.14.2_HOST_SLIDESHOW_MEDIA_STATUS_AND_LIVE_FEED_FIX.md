# PHASE 13.14.2 — HOST SLIDESHOW, MEDIA STATUS & LIVE FEED FIX

## Executive Summary

Three critical Host Console issues were identified, root-caused, and fixed:

1. **Host slideshow** only appeared on the Overview page → now appears on ALL Host Console pages via shared layout.
2. **Hide media** incorrectly set `REJECTED` status → now properly sets `HIDDEN` status via dedicated endpoint.
3. **Live page** displayed admin slideshow media → now displays approved guest memories from the public gallery.

All 11 E2E tests pass. TypeScript: 0 errors. Build: clean. Docker: 6/6 healthy.

---

## Issue 1 — Host Slideshow on All Pages

### Root Cause

The host slideshow was fetched and rendered only inside `HostOverviewPage.tsx`. The shared `HostLayout.tsx` had no slideshow component. Other pages (Gallery, Settings, Share, Export, Live) had blank backgrounds.

### Fix

Moved the slideshow into `HostLayout.tsx`:
- Fetches slideshow via `getPublicHostSlideshow(event.slug)` on mount
- Renders `ImageSlideshow` as a `position: fixed` background with `pointerEvents: none`
- All Host Console pages now automatically inherit the background slideshow
- Removed duplicate slideshow fetch/render from `HostOverviewPage.tsx`

### Verification

| Page | Slideshow Background | Status |
|------|---------------------|--------|
| Overview | Fixed | PASS |
| Gallery | Fixed | PASS |
| Settings | Fixed | PASS |
| Share | Fixed | PASS |
| Export | Fixed | PASS |
| Live | Fixed | PASS |

**Note:** Full visual verification requires browser testing. Code-level verification confirms the slideshow is now in the shared layout.

---

## Issue 2 — Hide Media Status Bug

### Root Cause

When a host clicked "Hide" on approved guest media:
1. Frontend sent `status='hidden'` to `setMediaStatus()`
2. `setMediaStatus()` called `hostRejectMedia()` for both `'hidden'` and `'pending'`
3. `hostRejectMedia()` set `MediaStatus.REJECTED`
4. `getGalleryMedia()` mapped REJECTED → `'pending'`

Result: Hidden media appeared as PENDING in the host gallery.

### Fix

**Backend:**
- Added `HIDDEN = "HIDDEN"` to `MediaStatus` enum
- Created Alembic migration `m5n6o7p8q9r0` to add the enum value to PostgreSQL
- Added `host_hide_media()` service: sets `status=HIDDEN`, `moderation_status=HIDDEN`
- Added `host_unhide_media()` service: sets `status=APPROVED`, `moderation_status=VISIBLE`
- Added `POST /api/host/events/{event_id}/media/{media_id}/hide` endpoint
- Added `POST /api/host/events/{event_id}/media/{media_id}/unhide` endpoint
- Added `moderation_status` to `MediaOut` schema and `_media_to_out()` serializer

**Frontend:**
- Added `hostHideMedia()` API function
- Updated `setMediaStatus()` to call `hostHideMedia()` for `'hidden'` status
- Fixed `getGalleryMedia()` status mapping: `HIDDEN` → `'hidden'` (not `'pending'`)

### Verification (E2E via API)

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Approve media | status=APPROVED | status=APPROVED | PASS |
| Gallery before hide | 1 item | 1 item | PASS |
| Hide media | status=HIDDEN, moderation=HIDDEN | status=HIDDEN, moderation=HIDDEN | PASS |
| Gallery after hide | 0 items | 0 items | PASS |
| Host gallery shows HIDDEN | status=HIDDEN | status=HIDDEN | PASS |
| Unhide media | status=APPROVED, moderation=VISIBLE | status=APPROVED, moderation=VISIBLE | PASS |
| Gallery after unhide | 1 item | 1 item | PASS |
| Overview counts | photos=1, total=1 | photos=1, total=1 | PASS |
| Cross-event hide | 404 Event not found | 404 Event not found | PASS |

---

## Issue 3 — Live Page Shows Guest Media

### Root Cause

`HostSlideshowPage.tsx` (the "Live" page) called `getHostSlideshowMedia(eventId)` which returned `HOST_SLIDESHOW` / `ADMIN` media. The page was designed to show admin-uploaded presentation media, not approved guest memories.

### Fix

Changed `HostSlideshowPage.tsx` to use `getPublicGallery(slug)` instead. The public gallery endpoint already filters correctly:
- `source = GUEST`
- `status IN (UPLOADED, APPROVED)`
- `moderation_status = VISIBLE`
- `media_role = GALLERY`

This ensures only approved guest photos/videos appear on the Live page.

### Verification

| Test | Status |
|------|--------|
| Public gallery endpoint returns only approved guest media | PASS |
| Host slideshow endpoint still returns HOST_SLIDESHOW media (for settings) | PASS |
| Live page uses correct endpoint | CODE VERIFIED |

**Note:** Full visual verification of the Live page requires browser testing.

---

## Files Changed

### Backend

| File | Change |
|------|--------|
| `backend/app/models/media.py` | Added `HIDDEN = "HIDDEN"` to `MediaStatus` enum |
| `backend/app/schemas/media.py` | Added `moderation_status` to `MediaOut`, imported `ModerationStatus` |
| `backend/app/services/media.py` | Added `host_hide_media()` and `host_unhide_media()` functions |
| `backend/app/api/routes/host_events.py` | Added `/hide` and `/unhide` endpoints, updated `_media_to_out()` to include `moderation_status` |
| `backend/alembic/versions/m5n6o7p8q9r0_add_hidden_media_status.py` | New migration to add HIDDEN to PostgreSQL enum |

### Frontend

| File | Change |
|------|--------|
| `src/components/host/HostLayout.tsx` | Added slideshow fetch + render as shared background |
| `src/pages/host/HostOverviewPage.tsx` | Removed duplicate slideshow (now in HostLayout) |
| `src/pages/host/HostSlideshowPage.tsx` | Changed from `getHostSlideshowMedia` to `getPublicGallery` |
| `src/services/api.ts` | Added `hostHideMedia()`, `hostUnhideMedia()`, `moderation_status` to `MediaItem` |
| `src/services/mockHostService.ts` | Fixed `setMediaStatus()` to use hide endpoint, fixed status mapping |

---

## TypeScript

```
npx tsc --noEmit
```

Result: **0 errors**

## Production Build

```
npx vite build
```

Result: **SUCCESS** (425.52 KB JS, 60.98 KB CSS)

## Docker

All 6 services healthy:
- gall-backend-1 ✓
- gall-frontend-1 ✓
- gall-postgres-1 ✓
- gall-redis-1 ✓
- gall-worker-1 ✓
- gall-backup-1 ✓

---

## Security Verification

| Test | Status |
|------|--------|
| Cross-event hide returns 404 | PASS |
| Hide endpoint requires host auth | CODE VERIFIED |
| Unhide endpoint requires host auth | CODE VERIFIED |
| Host cannot modify other host's events | PASS (existing) |

---

## Remaining Browser Verification

The following require visual browser testing:

1. Host slideshow appears on all 6 Host Console pages
2. Live page displays approved guest memories (not slideshow)
3. Hide button in Gallery correctly marks media as HIDDEN
4. HIDDEN filter in Gallery shows hidden media
5. No visual regressions on any Host page

---

## Final Status

**PHASE 13.14.2 STATUS: COMPLETE — CODE VERIFIED + API VERIFIED**

All three issues have been fixed, rebuilt, and verified via E2E API testing. Browser visual verification remains for the operator to confirm.
