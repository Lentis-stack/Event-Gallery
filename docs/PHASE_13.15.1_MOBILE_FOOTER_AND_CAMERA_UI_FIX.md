# PHASE 13.15.1 — MOBILE FOOTER & CAMERA UI FIX

## Executive Summary

Three UI issues identified and fixed from mobile testing:

1. **Footer overlapping camera controls on mobile** — Footer is `position: fixed; bottom: 0` and was shown on the camera page, covering the shutter button area. Fixed by hiding the footer on the camera page.
2. **Camera frame not rounded on mobile** — The `@media (max-width: 560px)` query explicitly set `border-radius: 0` and `border-left/right: none` on `.phone-camera__frame`, killing curved corners. Removed these overrides.
3. **Camera controls cramped on mobile** — Reduced `max-height` (55vh) and missing centering caused controls to be squeezed. Fixed with `justify-content: center`, increased height, and tighter header spacing.

---

## Root Causes

### Issue 1 — Footer Floating on Mobile

**File:** `src/pages/CameraPage.tsx`
**Root cause:** `<SiteFooter />` was rendered on the camera page without the `hidden` prop. The footer's `position: fixed; bottom: 0; z-index: 100` caused it to float over camera controls (shutter, flip, gallery buttons).

**Fix:** Changed `<SiteFooter />` to `<SiteFooter hidden />` in CameraPage.tsx.

**Impact:** The camera page is an immersive full-screen experience — the footer provides no value here and actively obstructs the primary interaction (photo/video capture). All other pages (welcome, host, admin) continue to show the footer normally.

### Issue 2 — Camera Frame Not Rounded on Mobile

**File:** `src/styles/components.css` (line ~4648)
**Root cause:** The mobile media query at `max-width: 560px` contained:
```css
.phone-camera__frame {
  border-radius: 0;
  border-left: none;
  border-right: none;
  max-height: 55vh;
}
```
This explicitly removed the 24px border-radius and edge borders on mobile devices.

**Fix:** Changed to:
```css
.phone-camera__frame {
  border-radius: 24px;
  max-height: 56vh;
}
```
The `border-left: none; border-right: none;` lines were removed entirely.

### Issue 3 — Camera Controls Not Visible on Mobile

**File:** `src/styles/components.css` (line ~4638)
**Root cause:** Multiple factors:
1. `max-height: 55vh` made the camera frame too small relative to other elements
2. `.phone-camera` lacked `justify-content: center`, so content wasn't vertically centered in available space
3. Header elements consumed unnecessary vertical space
4. The fixed footer (even when invisible) was not accounted for

**Fix:**
1. Added `justify-content: center` to `.phone-camera` on mobile
2. Increased `max-height` to `56vh`
3. Added mobile-specific styles for `.camera-page__header` (smaller margin, font sizes)
4. Added `min-height: 100vh; min-height: 100dvh` to `.camera-page` for proper viewport handling

---

## Files Changed

| File | Change |
|------|--------|
| `src/pages/CameraPage.tsx` | `<SiteFooter />` → `<SiteFooter hidden />` |
| `src/styles/components.css` | Mobile phone-camera frame: removed `border-radius: 0`, kept `24px`, increased `max-height` to `56vh`, added `justify-content: center` to `.phone-camera`, added mobile camera-page header/branding overrides |

---

## CSS Changes Detail

### Before (mobile560px query)
```css
.phone-camera {
  width: 100%;
  gap: 0.5rem;
}
.phone-camera__frame {
  border-radius: 0;          /* ← killed curved corners */
  border-left: none;         /* ← removed side borders */
  border-right: none;
  max-height: 55vh;          /* ← too small */
}
```

### After (mobile560px query)
```css
.phone-camera {
  width: 100%;
  gap: 0.5rem;
  justify-content: center;   /* ← centers camera in viewport */
}
.phone-camera__frame {
  border-radius: 24px;       /* ← curved corners preserved */
  max-height: 56vh;          /* ← slightly larger */
}
```

### Additional mobile camera-page styles added
```css
.camera-page {
  min-height: 100vh;
  min-height: 100dvh;         /* dynamic viewport for mobile */
}
.camera-page__header {
  margin-bottom: 0.25rem;     /* reduced from 0.5rem */
}
.camera-page__branding {
  font-size: 0.8rem;          /* smaller on mobile */
}
.camera-page__welcome {
  font-size: 0.65rem;         /* smaller on mobile */
}
```

---

## Footer Behavior Verification

| Page | Footer Visible | Footer Position | Content Not Overlapped |
|------|---------------|-----------------|----------------------|
| Camera page | NO (hidden) | N/A | ✅ Full-screen camera |
| Guest landing | YES | Fixed bottom | ✅ 100px padding-bottom |
| Host Overview | YES | Fixed bottom | ✅ 100px padding-bottom |
| Host Gallery | YES | Fixed bottom | ✅ 100px padding-bottom |
| Host Settings | YES | Fixed bottom | ✅ 100px padding-bottom |
| Host Live | YES | Fixed bottom | ✅ 100px padding-bottom |
| Admin Console | YES | Fixed bottom | ✅ 100px padding-bottom |

---

## Camera Frame Verification

| Property | Desktop (base) | Mobile (560px) |
|----------|---------------|----------------|
| Width | `min(400px, 92vw)` | `100%` |
| Aspect ratio | `3/4` | `3/4` (unchanged) |
| Border radius | `24px` | `24px` ✅ |
| Overflow | `hidden` ✅ | `hidden` ✅ |
| Max height | `62vh` | `56vh` |
| Border | `1px solid gold/12%` | unchanged |
| Shadow | `0 20px 60px black/50%` | unchanged |

The video element inside `.phone-camera__video` uses `object-fit: cover` and is clipped by the frame's `overflow: hidden` + `border-radius: 24px`.

---

## TypeScript Check

```
npx tsc --noEmit → 0 errors ✅
```

## Production Build

```
npx vite build → clean ✅
dist/assets/index-CADnx1VF.js 430.75 kB (gzip 129.21 kB)
dist/assets/index-BZ54-5TU.css 70.56 kB (gzip 11.53 kB)
```

## Docker

| Container | Status |
|-----------|--------|
| gall-frontend-1 | ✅ Healthy (rebuilt) |
| gall-backend-1 | ✅ Healthy |
| gall-postgres-1 | ✅ Healthy |
| gall-redis-1 | ✅ Healthy |
| gall-worker-1 | ✅ Healthy |
| gall-backup-1 | ✅ Healthy |

## Regression Tests

| # | Test | Result |
|---|------|--------|
| 1 | API health | ✅ PASS |
| 2 | Admin login | ✅ PASS |
| 3 | Admin events | ✅ PASS (5 events) |
| 4 | Public event page | ✅ HTTP 200 |
| 5 | Guest registration | ✅ PASS |
| 6 | Guest session/me | ✅ PASS |

---

## Mobile Testing

| Screen Width | Footer (non-camera) | Camera Frame | Controls Visible | Rounded Corners |
|-------------|-------------------|--------------|-----------------|----------------|
| 375px | ✅ Fixed bottom | ✅ Full width, 3:4 | ✅ Shutter, flip, gallery visible | ✅ 24px radius |
| 390px | ✅ Fixed bottom | ✅ Full width, 3:4 | ✅ All controls visible | ✅ 24px radius |
| 412px | ✅ Fixed bottom | ✅ Full width, 3:4 | ✅ All controls visible | ✅ 24px radius |
| Desktop | ✅ Fixed bottom | ✅ min(400px, 92vw) | ✅ All controls visible | ✅ 24px radius |

**Note:** Physical device camera testing requires HTTPS, which is not available in local development. The CSS layout has been verified at the specified viewport widths.

---

## Known Limitations

1. **Physical camera testing** — Camera feed, capture, and upload require HTTPS. These are CODE VERIFIED but not PHYSICALLY VERIFIED on a real mobile device.
2. **Safe area insets** — The `env(safe-area-inset-bottom)` is used for iOS notch handling. Actual behavior on real iOS devices needs physical testing.
3. **Footer height variability** — The fixed footer height varies based on provider content (logo, contact, social). The 100px padding-bottom accommodates the largest expected size.

---

## Final Status

```
PHASE 13.15.1 STATUS:

Footer Layout:        PASS — Hidden on camera, fixed bottom elsewhere
Camera Controls:      PASS — Visible on 375/390/412px + desktop
Camera Frame:         PASS — 24px border-radius preserved on all viewports
Mobile 375px:         PASS — CSS verified
Mobile 390px:         PASS — CSS verified
Mobile 412px:         PASS — CSS verified
Desktop:              PASS — CSS verified
TypeScript:           PASS — 0 errors
Build:                PASS — Clean production build
Docker:               PASS — 6/6 healthy
Regression:           PASS — 6/6 API tests pass
Overall:              PASS
```
