# PHASE 12.3 — HTTPS/TLS + LIVE PRODUCTION DOMAIN REPORT

## Status

**B. COMPLETE — EXTERNAL VERIFICATION REMAINING**

## Production Domain

**lentisevent.gallery**

## Verification Summary

| Area | Status | Evidence |
|------|--------|----------|
| Domain in frontend build | PASS | `https://lentisevent.gallery` found in JS bundle |
| FRONTEND_URL configured | PASS | `.env.production` |
| VITE_PUBLIC_URL configured | PASS | `.env.production` |
| CORS accepts domain | PASS | `access-control-allow-origin: https://lentisevent.gallery` |
| Backend health | PASS | status=ok, pg=connected, redis=connected |
| Admin login | PASS | JWT obtained |
| Create event | PASS | Persisted in PostgreSQL |
| Guest registration | PASS | Session token returned |
| Image upload to R2 | PASS | Media record created |
| Video upload to R2 | PASS | Media record created |
| Worker processing | PASS | 6.7s for video |
| Host moderation | PASS | status=APPROVED |
| Gallery display | PASS | gallery_total=1 |
| R2 objects | PASS | 20 objects in bucket |
| TypeScript | PASS | 0 errors |
| Vite build | PASS | Built successfully |
| Security audit | PASS | No secrets in tracked files |
| Git safety | PASS | .env files gitignored |
| DNS resolution | BLOCKED | Domain not yet configured |
| HTTPS certificate | BLOCKED | Requires DNS + Cloudflare |
| Live domain test | BLOCKED | Requires DNS + server |

## What Was Actually Verified

All server-side infrastructure was tested through actual Docker containers:

1. **Domain embedding**: `https://lentisevent.gallery` is correctly embedded in the frontend JavaScript bundle
2. **CORS**: Backend accepts requests from `https://lentisevent.gallery`
3. **Full E2E flow**: Admin → event → guest → upload → R2 → process → moderate → gallery
4. **R2 storage**: 20 objects stored in real Cloudflare R2 bucket
5. **Security**: No secrets in source, images, or frontend bundle

## What Remains Blocked

| Item | Blocker | How to Unblock |
|------|---------|----------------|
| DNS resolution | No DNS records | Configure A/CNAME record pointing to server |
| HTTPS certificate | No DNS | Cloudflare proxy (recommended) or Let's Encrypt |
| Live domain test | No DNS | After DNS configured |
| Camera physical test | No device + no HTTPS | Physical device + HTTPS required |
| WebSocket live test | No DNS | After DNS configured |

## DNS Configuration Required

To make `lentisevent.gallery` live:

### Option A: Cloudflare (Recommended)

1. Add domain `lentisevent.gallery` to Cloudflare
2. Create A record: `lentisevent.gallery → <server-ip>`
3. Enable proxy (orange cloud)
4. Set SSL/TLS mode to **Full (strict)**
5. Add Cloudflare origin certificate to nginx (or use Full mode with self-signed)

### Option B: Direct DNS

1. Create A record: `lentisevent.gallery → <server-ip>`
2. Install Let's Encrypt: `certbot certonly --webroot -w /var/www/html -d lentisevent.gallery`
3. Configure nginx with TLS certificates

## HTTPS Architecture

```
Browser → https://lentisevent.gallery
               |
               v
         Cloudflare (TLS termination)
               |
               v (HTTP internally)
         nginx (:80)
               |
    +----------+----------+
    |                     |
    v                     v
  React SPA           /api/*
                         |
                         v
                    FastAPI (:8000)
                         |
                    +---------+
                    |         |
                    v         v
               PostgreSQL   Redis
                               |
                               v
                             Worker
                               |
                               v
                         Cloudflare R2
```

Cloudflare handles TLS at the edge. nginx listens on port 80 internally. This is the simplest and most secure architecture.

## nginx Configuration

The nginx.conf already includes:
- SPA fallback routing
- `/api/` proxy to FastAPI
- WebSocket upgrade headers
- Security headers
- Large upload support (600MB)
- Request timeouts (600s)

For HTTPS behind Cloudflare, nginx only needs to listen on port 80. Cloudflare handles TLS termination.

## Cookie / Auth Security

Production authentication uses JWT tokens (not cookies for state). The frontend stores the access token in memory and sends it via `Authorization: Bearer` header. The refresh token uses an HttpOnly cookie.

When Cloudflare proxies HTTPS to nginx port 80:
- `X-Forwarded-Proto: https` is set by Cloudflare
- FastAPI receives the correct protocol information
- CORS uses `https://lentisevent.gallery` as the allowed origin

## Security Audit Results

| Check | Status |
|-------|--------|
| No secrets in source code | PASS (config/validation references only) |
| No secrets in Docker images | PASS |
| No secrets in frontend bundle | PASS |
| No hardcoded production domain in code | PASS (only in test/mock placeholders) |
| CORS correctly configured | PASS |
| .env files gitignored | PASS |
| R2 bucket private | PASS |
| Signed URLs with expiry | PASS |
| Network isolation | PASS |

## Production Deployment Commands

```bash
# 1. Configure DNS (A record → server IP)

# 2. Configure Cloudflare
#    - Add lentisevent.gallery
#    - Enable proxy
#    - SSL mode: Full (strict)

# 3. Build and start
docker compose --env-file .env.production up -d --build

# 4. Run migrations
docker exec gall-backend-1 sh -c 'cd /app && PYTHONPATH=/app alembic upgrade head'

# 5. Verify
curl https://lentisevent.gallery/api/health
curl https://lentisevent.gallery/api/health/ready

# 6. Open in browser
# https://lentisevent.gallery
```

## Credentials & Operator Information

| Setting | Location | Template | Gitignored | Restart | Rebuild |
|---------|----------|----------|------------|---------|---------|
| Production Domain | .env.production | .env.production.example | Yes | Yes | Yes |
| FRONTEND_URL | .env.production | .env.production.example | Yes | Yes | Yes |
| VITE_PUBLIC_URL | .env.production | .env.production.example | Yes | No | Yes |
| JWT Secret | .env.production | .env.production.example | Yes | Yes | No |
| SECRET_KEY | .env.production | .env.production.example | Yes | Yes | No |
| PostgreSQL | .env.production | .env.production.example | Yes | Yes | No |
| Redis | .env.production | .env.production.example | Yes | Yes | No |
| R2 Access Key | .env.production | .env.production.example | Yes | Yes | No |
| R2 Secret Key | .env.production | .env.production.example | Yes | Yes | No |
| R2 Endpoint | .env.production | .env.production.example | Yes | Yes | No |
| R2 Bucket | .env.production | .env.production.example | Yes | Yes | No |
| Admin Email | .env.operator.local | .env.operator.example | Yes | No | No |
| Host Email | .env.operator.local | .env.operator.example | Yes | No | No |

**No actual secret values are displayed in this report.**

## Files Changed

| File | Change |
|------|--------|
| `.env.production` | Fixed domain typo: lentisevetn → lentisevent |
| `docs/PHASE_12.3_HTTPS_TLS_PRODUCTION_REPORT.md` | NEW |

## Production Readiness

| Component | Status |
|-----------|--------|
| Application code | READY |
| Docker stack | READY |
| PostgreSQL | READY |
| Redis | READY |
| R2 storage | READY |
| nginx | READY |
| Worker | READY |
| FFmpeg | READY |
| Domain config | READY |
| DNS | NOT CONFIGURED |
| HTTPS | NOT CONFIGURED (requires DNS) |
| Camera | NOT TESTED (requires HTTPS + device) |

## Final Verdict

### B. COMPLETE — EXTERNAL VERIFICATION REMAINING

The application is fully configured for `lentisevent.gallery` with HTTPS behind Cloudflare. All server-side components work correctly. The domain cannot be tested live because DNS records have not been configured yet.

**To complete production deployment:**
1. Configure DNS A record for `lentisevent.gallery`
2. Add domain to Cloudflare
3. Enable Cloudflare proxy
4. Set SSL mode to Full (strict)
5. Start the Docker stack
6. Verify: `curl https://lentisevent.gallery/api/health`

---
*Generated: 2026-08-23*
