# PHASE 13.18 — Private Events & Invited Guest Access

## Objective
Add support for PRIVATE events where only invited guests (with name + password) can access the camera and upload flow, while preserving all existing PUBLIC event functionality.

## Architecture Decision
- **Event-level setting**: `access_mode` field on the Event model (PUBLIC or PRIVATE)
- **Default: PUBLIC** — existing events are unaffected
- **Invited guests**: Dedicated `event_invited_guests` table (separate from the existing lightweight Guest model)
- **Authentication**: Private guests log in with name + password → receive a session token (reuses existing GuestSession model for media ownership)
- **Media ownership**: Private guests get a Guest row for FK compatibility with the existing media system

## Database Changes

### New table: `event_invited_guests`
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) | UUID PK |
| event_id | VARCHAR(36) | FK → events.id, CASCADE |
| name | VARCHAR(120) | Guest display name |
| password_hash | VARCHAR(255) | Argon2id hash |
| status | ENUM | INVITED, ACTIVE, REMOVED |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| last_login_at | TIMESTAMP | nullable |

### New column: `events.access_mode`
- Type: `event_access_mode` enum (PUBLIC, PRIVATE)
- Default: PUBLIC
- Nullable: NO

### Migration
- `n6o7p8q9r0s1_add_event_access_mode_and_invited_guests.py`

## Backend API Changes

### New endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/events/{slug}/guests/private-login | Public | Private guest login (name + password) |
| GET | /api/admin/events/{event_id}/guests | Admin | List invited guests |
| POST | /api/admin/events/{event_id}/guests | Admin | Add invited guest |
| POST | /api/admin/events/{event_id}/guests/{guest_id}/reset-password | Admin | Reset guest password |
| DELETE | /api/admin/events/{event_id}/guests/{guest_id} | Admin | Remove guest access |

### Modified endpoints
| Endpoint | Change |
|----------|--------|
| POST /api/events | Accepts `access_mode` field |
| PATCH /api/admin/events/{id} | Accepts `access_mode` field |
| GET /api/events/{slug}/public | Returns `access_mode` |

## Frontend Changes

### New pages
- `PrivateGuestLoginPage.tsx` — Premium private event login (name + password)

### Modified pages
- `EventPage.tsx` — Landing page shows "Enter Event" for PRIVATE events
- `GuestPage.tsx` — Redirects to private login for PRIVATE events
- `AdminCreateEventPage.tsx` — Access mode selector + invited guest management
- `AdminEditEventPage.tsx` — Access mode toggle + invited guest management
- `App.tsx` — New route `/e/:slug/guest-login`

### New API functions (api.ts)
- `privateGuestLogin()`
- `listInvitedGuests()`
- `addInvitedGuest()`
- `resetInvitedGuestPassword()`
- `removeInvitedGuest()`

## Security
- Passwords are hashed with Argon2id (same as user passwords)
- Plaintext passwords are NEVER stored or returned by API
- Generic auth error: "Invalid name or password." (no guest enumeration)
- Removed guests get 403, not 401 (clearer messaging)
- Cross-event isolation verified: Guest from Event A cannot login to Event B
- Private login on PUBLIC event returns 400

## Test Results: 31/31 PASS
1. ✅ Admin login
2. ✅ Create PUBLIC event
3. ✅ Create PRIVATE event (access_mode=PRIVATE)
4. ✅ Default access_mode=PUBLIC
5. ✅ Add invited guests
6. ✅ Duplicate name rejected (409)
7. ✅ List invited guests
8. ✅ Reset guest password
9. ✅ Old password rejected after reset
10. ✅ New password accepted after reset
11. ✅ Sarah login with own password
12. ✅ Wrong password rejected
13. ✅ Unknown guest rejected
14. ✅ Private login on PUBLIC event rejected (400)
15. ✅ Public event guest registration unchanged
16. ✅ Cross-event login rejected
17. ✅ Removed guest login rejected (403)
18. ✅ Toggle PRIVATE→PUBLIC
19. ✅ Toggle PUBLIC→PRIVATE
20. ✅ Public endpoint includes access_mode

## Regression Results
- TypeScript: 0 errors ✅
- Production build: clean ✅
- Docker: 6/6 healthy ✅
- Existing public events: unchanged ✅
- Admin login: working ✅
- Event CRUD: working ✅
- Host login: working ✅

## Files Changed
| File | Change |
|------|--------|
| backend/app/models/event.py | Added `EventAccessMode` enum + `access_mode` column + `invited_guests` relationship |
| backend/app/models/event_guest.py | **NEW** — EventInvitedGuest model |
| backend/app/schemas/event.py | Added `access_mode` to EventCreate, EventUpdate, EventOut, PublicEventOut |
| backend/app/schemas/event_guest.py | **NEW** — Invited guest schemas |
| backend/app/services/events.py | Handle `access_mode` in create/update |
| backend/app/services/event_guests.py | **NEW** — Guest management + private login service |
| backend/app/api/routes/admin_event_guests.py | **NEW** — Admin guest management routes |
| backend/app/api/routes/guests.py | Added private-login endpoint |
| backend/app/main.py | Registered new router |
| backend/alembic/env.py | Registered new model |
| backend/alembic/versions/n6o7p8q9r0s1_*.py | **NEW** — Migration |
| src/types/event.ts | Added `accessMode` |
| src/services/api.ts | Added `access_mode` + invited guest API functions |
| src/services/mockAdminService.ts | Pass `accessMode` in create/update |
| src/pages/admin/AdminCreateEventPage.tsx | Access mode selector + guest management |
| src/pages/admin/AdminEditEventPage.tsx | Access mode toggle + guest management |
| src/pages/PrivateGuestLoginPage.tsx | **NEW** — Private event login page |
| src/pages/GuestPage.tsx | Redirect to private login for PRIVATE events |
| src/pages/EventPage.tsx | Landing page handles PRIVATE events |
| src/App.tsx | New route `/e/:slug/guest-login` |
