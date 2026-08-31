# PHASE 13.16.1 — Host Password Authentication Fix

## 1. Root Cause

Two separate bugs prevented host passwords from working:

### Bug A — Admin Edit Event: Password silently dropped
The `AdminEditEventPage` passed `host_password` (snake_case) to `mockAdminService.updateEvent()`, but the function checked `patch.hostPassword` (camelCase). The password was **never sent to the API**.

```typescript
// AdminEditEventPage.tsx sends:
...(newHostPassword ? { host_password: newHostPassword } : {})

// mockAdminService.updateEvent() checks:
...(patch.hostPassword ? { host_password: patch.hostPassword } : {})
//                                  ^^^^^^^^^^^^^^^^^^^^^^^^
//                    patch.hostPassword is undefined → password dropped!
```

### Bug B — Frontend/backend password validation mismatch
- Frontend validated minimum **8 characters** for password
- Backend `validate_password_strength()` enforced minimum **10 characters**
- Passwords between 8–9 characters would pass frontend validation but fail at the backend with a confusing error

### Bug C — Backend schema min_length=8 conflicted with validate_password_strength(min=10)
The Pydantic `EventCreate` and `EventUpdate` schemas had `min_length=8` on `host_password`, but the business logic enforced `len >= 10` via `validate_password_strength()`. This inconsistency was confusing.

## 2. Authentication Architecture

The system uses a **single User record** per email:

```
User (email → password_hash → role=HOST)
  ↑
  │ host_id
Event (1 event per host_id, but one user can host multiple events)
```

When the admin creates a new event for an existing host email:
- `_resolve_host()` finds the existing user
- If a new password is provided → updates the password hash
- Returns the existing user ID

**Important implication**: When the same email is used for multiple events, the password is shared. The latest password set (via create or edit) is what all events for that host use.

## 3. Files Changed

| File | Change |
|------|--------|
| `src/services/mockAdminService.ts` | Fixed `updateEvent()` to check both `host_password` and `hostPassword` |
| `src/pages/admin/AdminCreateEventPage.tsx` | Changed password min from 8 to 10 chars, updated placeholder |
| `src/pages/admin/AdminEditEventPage.tsx` | Changed password min from 8 to 10 chars, updated placeholder |
| `backend/app/schemas/event.py` | Removed `min_length=8` from `EventCreate.host_password` and `EventUpdate.host_password` — validation handled by `validate_password_strength()` in the service layer |

## 4. Password Flow (After Fix)

### Event Creation
```
Admin → Create Event form → host_password: "MyCustomPass123!"
  ↓
mockAdminService.createEvent() → apiCreateEvent(payload)
  ↓
POST /api/events { host_email, host_password }
  ↓
_resolve_host() → validate_password_strength() → hash_password() → store hash
  ↓
Event created with host_id linked to the user
```

### Password Reset (Admin Edit)
```
Admin → Edit Event form → New Password: "NewResetPass999!"
  ↓
mockAdminService.updateEvent() → checks patch.host_password || patch.hostPassword
  ↓
PATCH /api/admin/events/{event_id} { host_password: "NewResetPass999!" }
  ↓
update_event() → validate_password_strength() → hash_password() → update hash
  ↓
Old password invalidated immediately
```

### Host Login
```
Host → /e/:slug/host → email + password
  ↓
POST /api/auth/login { email, password }
  ↓
authenticate_user() → verify_password(entered, stored_hash)
  ↓
Access token issued with HOST role
```

## 5. Test Results

| # | Test | Result |
|---|------|--------|
| 1 | Admin login | ✅ PASS |
| 2 | Create event with custom password | ✅ PASS |
| 3 | Host login with correct custom password | ✅ PASS |
| 4 | Wrong password → rejected | ✅ PASS |
| 5 | Adekunle25 → rejected | ✅ PASS |
| 6 | Admin PATCH password reset | ✅ PASS |
| 7 | Old password fails after reset | ✅ PASS |
| 8 | New password works after reset | ✅ PASS |
| 9 | Empty password edit → password unchanged | ✅ PASS |
| 10 | Password persists after non-password edit | ✅ PASS |
| 11 | Second host (different email) | ✅ PASS |
| 12 | Cross-event isolation | ✅ PASS |
| 13 | Same email, new password → updates | ✅ PASS |
| 14 | New password works after same-email update | ✅ PASS |
| 15 | Previous password invalidated after same-email update | ✅ PASS |

## 6. Regression Tests

| Test | Result |
|------|--------|
| Health check | ✅ PASS |
| Admin login | ✅ PASS |
| Public event | ✅ PASS |
| Public media | ✅ PASS |
| Guest registration | ✅ PASS |
| TypeScript (npx tsc --noEmit) | ✅ 0 errors |
| Production build (npx vite build) | ✅ Clean |
| Docker (6/6 containers) | ✅ All healthy |
| Backend rebuild (schema changed) | ✅ Rebuilt + healthy |

## 7. Security Verification

- Passwords stored as Argon2id hashes — no plaintext in database
- `Adekunle25` fully rejected for all test accounts
- Wrong passwords return generic "Invalid email or password." (no account enumeration)
- Cross-event host access blocked (host only sees their own events)
- Password hash never exposed in API responses
- Empty password fields during edit do not overwrite existing password

## 8. Build Status

| Check | Result |
|-------|--------|
| TypeScript | 0 errors |
| Vite build | Clean |
| Docker backend | Rebuilt + healthy |
| Docker frontend | Rebuilt + healthy |
| All 6 containers | Healthy |
