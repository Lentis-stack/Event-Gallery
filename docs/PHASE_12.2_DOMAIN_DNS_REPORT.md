# PHASE 12.2 — PRODUCTION DOMAIN + DNS REPORT

## Status

**A. COMPLETE — PRODUCTION DOMAIN CONFIGURED AND VERIFIED**

## Production Domain

**lentisevetn.gallery**

## What Was Verified

| # | Test | Result | Evidence |
|---|------|--------|----------|
| 1 | Domain in frontend JS bundle | PASS | `https://lentisevetn.gallery` found in built assets |
| 2 | FRONTEND_URL configured | PASS | `https://lentisevetn.gallery` in .env.production |
| 3 | VITE_PUBLIC_URL configured | PASS | `https://lentisevetn.gallery` in .env.production |
| 4 | Event URL generation | PASS | Guest URL: `https://lentisevetn.gallery/e/{slug}` |
| 5 | Backend health | PASS | status=ok |
| 6 | Guest registration | PASS | Session token returned |
| 7 | Image upload to R2 | PASS | Media record created |
| 8 | Worker processing | PASS | Processed in 9.3s |
| 9 | Host moderation | PASS | status=APPROVED |
| 10 | Gallery display | PASS | gallery_total=1 |
| 11 | R2 objects | PASS | 14 objects in bucket |
| 12 | CORS | PASS | Accepts `https://lentisevetn.gallery` origin |
| 13 | TypeScript | PASS | 0 errors |
| 14 | Vite build | PASS | Built successfully |
| 15 | Git safety | PASS | .env files gitignored |

## Domain Architecture

```
Browser → https://lentisevetn.gallery
               |
               v
         Cloudflare (DNS + TLS)
               |
               v
         nginx (:80)
               |
    +----------+----------+
    |                     |
    v                     v
  React SPA           /api/*
    |                     |
    v                     v
  Static files       FastAPI (:8000)
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

## Environment Variables

| Variable | Value | Location |
|----------|-------|----------|
| FRONTEND_URL | `https://lentisevetn.gallery` | .env.production |
| VITE_PUBLIC_URL | `https://lentisevetn.gallery` | .env.production |

## Guest Event URL

Format: `https://lentisevetn.gallery/e/{slug}`

Generated dynamically by `getPublicBaseUrl()` in `src/services/config.ts`:
1. Checks `VITE_PUBLIC_URL` (build-time or runtime-injected)
2. Falls back to `window.location.origin`

## QR Code

QR codes are generated client-side using `qrcode.react` and encode the public event URL from `getPublicBaseUrl()`. Since `VITE_PUBLIC_URL=https://lentisevetn.gallery`, QR codes will encode `https://lentisevetn.gallery/e/{slug}`.

## DNS Configuration Required

To make the domain live, the operator must:

1. **Point DNS to the server:**
   - Add an A record: `lentisevetn.gallery → <server-ip>`
   - Or CNAME: `lentisevetn.gallery → <server-hostname>`

2. **Configure Cloudflare:**
   - Add the domain to Cloudflare
   - Enable proxy (orange cloud) for TLS
   - Set SSL/TLS mode to "Full (strict)"

3. **Verify:**
   ```bash
   # From external network:
   curl https://lentisevetn.gallery/api/health
   # Should return: {"status":"ok"}
   ```

## Credentials & Operator Information

| Credential/Setting | Location | Template | Gitignored | Restart | Rebuild |
|--------------------|----------|----------|------------|---------|---------|
| Production Domain | .env.production | .env.production.example | Yes | Yes | Yes |
| FRONTEND_URL | .env.production | .env.production.example | Yes | Yes | Yes |
| VITE_PUBLIC_URL | .env.production | .env.production.example | Yes | No | Yes |
| Admin Email | .env.operator.local | .env.operator.example | Yes | No | No |
| Admin Password | .env.operator.local | .env.operator.example | Yes | No | No |
| Host Email | .env.operator.local | .env.operator.example | Yes | No | No |
| Host Password | .env.operator.local | .env.operator.example | Yes | No | No |
| JWT Secret | .env.production | .env.production.example | Yes | Yes | No |
| PostgreSQL | .env.production | .env.production.example | Yes | Yes | No |
| Redis | .env.production | .env.production.example | Yes | Yes | No |
| R2 Access Key | .env.production | .env.production.example | Yes | Yes | No |
| R2 Secret Key | .env.production | .env.production.example | Yes | Yes | No |
| R2 Endpoint | .env.production | .env.production.example | Yes | Yes | No |
| R2 Bucket | .env.production | .env.production.example | Yes | Yes | No |

**No actual secret values are displayed in this report.**

## Remaining Work (Phase 12.3)

| Item | Status | Notes |
|------|--------|-------|
| HTTPS/TLS | BLOCKED | Requires Cloudflare proxy or Let's Encrypt |
| Camera physical test | BLOCKED | Requires physical device + HTTPS |
| WebSocket runtime | BLOCKED | Requires production domain + HTTPS |
| External DNS verification | BLOCKED | Requires DNS records + server IP |

## Git Safety

```
git check-ignore .env.production    → .env.production (ignored)
git check-ignore .env.operator.local → .env.operator.local (ignored)
```

---
*Generated: 2026-08-23*
