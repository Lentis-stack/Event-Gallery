# Phase 13.11.1 — Archive Restore & Permanent Event Deletion Fix

**Date:** 2026-08-26  
**Status:** COMPLETE

---

## Summary

Fixed the Admin Archive system so administrators can:
1. **View archived events** with proper controls (via `/admin/console/archive`)
2. **Restore archived events** back to active status (CREATED/NOT_STARTED)
3. **Permanently delete archived events** with confirmation dialog
4. **Proper database and R2 storage cleanup** on permanent deletion

**Root Cause:** The previous implementation had TWO places showing archived events:
- **AdminEventsPage** (`/admin/console/events`) with "Archived" tab — used `EventCard` component showing active event controls (Edit, Set Live, End, Archive) — **WRONG UI**
- **AdminArchivePage** (`/admin/console/archive`) — had correct Restore/Permanent Delete buttons but users were landing on the wrong page

**Fix:** Removed the misleading "Archived" tab from AdminEventsPage, making AdminArchivePage the single source of truth for archived event management.

---

## Files Changed

### Frontend (3 files)
| File | Change |
|------|--------|
| `src/pages/admin/AdminEventsPage.tsx` | Removed "Archived" tab and filter logic; now only shows active events (All, Upcoming, Live, Ended) |
| `src/pages/admin/AdminArchivePage.tsx` | Already had correct implementation with Restore/Permanent Delete buttons, confirmation dialogs, inline error handling |
| `src/components/admin/EventCard.tsx` | Already had conditional `onDelete` prop (only rendered on Archive page) |

### Backend (2 files - already existed)
| File | Endpoint |
|------|----------|
| `backend/app/api/routes/admin_events.py` | `POST /{event_id}/restore` — restores ARCHIVED → CREATED |
| `backend/app/api/routes/admin_events.py` | `DELETE /{event_id}/permanent` — permanent deletion with R2 cleanup |

### Database (1 migration - already applied)
| File | Change |
|------|--------|
| `backend/alembic/versions/l4m5n6o7p8q9_add_created_event_status.py` | Added `CREATED` to `event_status` enum; allowed ARCHIVED → CREATED transition |

---

## Verification Results

### Browser E2E Testing (Desktop)

| Test | Result |
|------|--------|
| **Archive page loads** | ✅ `/admin/console/archive` shows all archived events |
| **Restore button visible** | ✅ Every archived event shows "RESTORE" button |
| **Permanent Delete button visible** | ✅ Every archived event shows "PERMANENT DELETE" button |
| **Restore confirmation dialog** | ✅ Shows event name, explains status becomes "Created" |
| **Restore executes** | ✅ Event removed from Archive, appears in active events with "NOT STARTED" status |
| **Restore survives refresh** | ✅ Event remains in active list after browser refresh |
| **Permanent Delete confirmation dialog** | ✅ Shows event name, warns "ALL its media, guests, and data will be permanently deleted. This action CANNOT be undone." |
| **Cancel on Permanent Delete** | ✅ Event remains in Archive |
| **Confirm Permanent Delete** | ✅ Event immediately removed from Archive |
| **Permanent Delete survives refresh** | ✅ Event remains gone after browser refresh |
| **Public URL returns 404** | ✅ `GET /api/events/:slug/public` returns `{"detail":"Event not found."}` |

### Mobile Testing (375px viewport)

| Test | Result |
|------|--------|
| Archive page loads | ✅ |
| RESTORE buttons visible | ✅ |
| PERMANENT DELETE buttons visible | ✅ |
| No horizontal overflow | ✅ |
| Buttons accessible (touch targets) | ✅ |
| Lentis logo background doesn't interfere | ✅ (pointer-events: none) |
| Confirmation dialogs usable | ✅ (stacked buttons on mobile) |

### Build & Infrastructure

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` | **0 errors** |
| `npm run build` | **Success** (413 KB JS / 55 KB CSS) |
| Docker services | **All healthy** (backend, frontend, postgres, redis, worker, backup) |
| Backend health | **OK** (`/api/health` returns `{"status":"ok"}`) |

---

## Archive Lifecycle Implementation

```
┌─────────────────┐     Archive      ┌──────────────────┐
│   ACTIVE EVENT  │ ─────────────────▶ │  ARCHIVED EVENT  │
│  (LIVE/CREATED/ │   (soft-delete)   │  (hidden from    │
│    ENDED)       │                   │   active list)   │
└─────────────────┘                   └────────┬─────────┘
                                                │
                    ┌───────────────────────────┴───────────────────────────┐
                    ▼                                                       ▼
            ┌───────────────┐                                       ┌──────────────────┐
            │    RESTORE    │                                       │  PERMANENT DELETE│
            │ ARCHIVED→CREATED│                                      │ (irreversible)   │
            └───────┬───────┘                                       └────────┬─────────┘
                    │                                                    │
                    ▼                                                    ▼
            ┌─────────────────┐                                ┌──────────────────┐
            │  ACTIVE EVENT   │                                │   EVENT REMOVED  │
            │  (NOT_STARTED)  │                                │  (DB + R2 cleanup)│
            └─────────────────┘                                └──────────────────┘
```

---

## Permanent Deletion Behavior

1. **Requires Admin authentication** (Bearer token + ADMIN role)
2. **Only works on ARCHIVED events** (UI only shows button on Archive page)
3. **Removes from PostgreSQL:**
   - Event record
   - All associated Media records
   - All associated Guest records
4. **Removes from R2 storage:**
   - Original file (`storage_key`)
   - Optimized variant (`optimized_key`)
   - Thumbnail (`thumbnail_key`)
   - Poster (`poster_key`)
5. **Best-effort R2 cleanup** — logs warnings if any deletion fails, continues with DB cleanup
6. **Returns 204 No Content** on success
7. **Public event link `/e/:slug` returns 404** after deletion

---

## Acceptance Checklist

- [x] Archived tab visibly shows Restore buttons
- [x] Archived tab visibly shows Permanent Delete buttons
- [x] Archived events no longer show inappropriate active-event controls
- [x] Restore works through the browser UI
- [x] Restored event returns to active events
- [x] Restore survives page refresh
- [x] Permanent Delete requires confirmation
- [x] Cancel does not delete the event
- [x] Confirm permanently deletes the event
- [x] Event disappears from Archive immediately
- [x] Event remains deleted after browser refresh
- [x] Deleted public event URL is inaccessible (404)
- [x] Event database record is removed
- [x] Event-related database records are handled correctly
- [x] Event media is removed according to existing R2 architecture
- [x] Other events and media remain untouched
- [x] Errors are human-readable (inline error display, not `alert()`)
- [x] No `[object Object]` errors
- [x] Archive UI works on mobile (375px, 390px, 768px, Desktop)
- [x] TypeScript has 0 errors
- [x] Production build succeeds
- [x] Docker services are healthy
- [x] Acceptance report exists
- [x] `Lentis.cre` remains gitignored

---

**Phase 13.11.1 Complete** ✅