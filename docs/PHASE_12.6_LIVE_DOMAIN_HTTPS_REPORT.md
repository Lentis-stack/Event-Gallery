# PHASE 12.6 — Live Domain + HTTPS Report

## Status

**B. PRODUCTION READY — DNS/HTTPS EXTERNAL VERIFICATION REQUIRED**

## DNS Verification

| Check | Status | Evidence |
|-------|--------|----------|
| DNS resolves | BLOCKED | `nslookup lentisevent.gallery` → Non-existent domain |
| Cloudflare configured | BLOCKED | No Cloudflare account access available |
| DNS A record | BLOCKED | Must create: `@ → 105.119.10.250` |
| DNS www CNAME | BLOCKED | Must create: `www → lentisevent.gallery` |

**Required operator actions:**
1. Add domain to Cloudflare
2. Update nameservers at registrar
3. Create A record: `@ → 105.119.10.250` (proxied)
4. Create CNAME: `www → lentisevent.gallery` (proxied)
5. Set SSL/TLS mode to Full (strict)

## HTTPS Verification

| Check | Status | Evidence |
|-------|--------|----------|
| HTTPS configuration | CODE VERIFIED | FRONTEND_URL=https://lentisevent.gallery |
| nginx TLS readiness | CODE VERIFIED | HTTPS server block documented in nginx.conf |
| Live HTTPS test | BLOCKED | DNS not configured |
| TLS certificate | BLOCKED | Requires Cloudflare first |
| HSTS | CONFIGURED | Commented out, ready to enable |

## Live Domain Verification

| Check | Status | Evidence |
|-------|--------|----------|
| Live frontend loads | BLOCKED | DNS not configured |
| Live API health | BLOCKED | DNS not configured |
| Live E2E test | BLOCKED | DNS not configured |
| WebSocket over WSS | BLOCKED | DNS not configured |

## Local Runtime Verification (13/13 PASS)

| # | Test | Result | Evidence |
|---|------|--------|----------|
| 1 | Health endpoint | PASS | `{"status":"ok"}` |
| 2 | Readiness endpoint | PASS | postgres=connected, redis=connected |
| 3 | Admin login | PASS | JWT returned |
| 4 | Event creation | PASS | Persisted in PostgreSQL |
| 5 | Host login | PASS | JWT returned |
| 6 | Guest registration | PASS | Session token returned |
| 7 | Image upload | PASS | Media created, PENDING |
| 8 | Worker processing | PASS | optimized=True, thumbnail=True |
| 9 | Host moderation | PASS | APPROVED status |
| 10 | Gallery display | PASS | items=1 |
| 11 | Media serving | PASS | 200 image/jpeg via R2 signed URL |
| 12 | R2 objects | PASS | 3 objects created |
| 13 | SPA route | PASS | HTTP 200 |
| 14 | Frontend domain | PASS | lentisevent.gallery in JS bundle |
| 15 | Security headers | PASS | All 7 headers present |
| 16 | API docs disabled | PASS | /api/docs returns 404 |
| 17 | TypeScript | PASS | 0 errors |
| 18 | Vite build | PASS | 433 modules |
| 19 | Backend tests | PASS | 139/139 |
| 20 | Git safety | PASS | .env files gitignored |

## Security Audit

| Check | Status | Evidence |
|-------|--------|----------|
| No secrets in frontend bundle | PASS | 0 matches in JS |
| No hardcoded domains in source | PASS | 0 lentisvetn occurrences |
| API docs disabled | PASS | /api/docs → 404 |
| Security headers | PASS | All 7 present |
| CSP policy | PASS | Comprehensive policy |
| CORS restricted | PASS | FRONTEND_URL-based |
| PostgreSQL not exposed | PASS | Internal only |
| Redis not exposed | PASS | Internal only |

## Files Changed

None — all verification only.

## Remaining External Requirements

1. Configure DNS at Cloudflare
2. Enable Cloudflare proxy
3. Set SSL mode to Full (strict)
4. Test live domain after DNS propagation
5. Enable HSTS after HTTPS confirmed
