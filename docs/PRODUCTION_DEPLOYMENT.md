# Lentis Gallery — Production Deployment Guide

## Architecture

```
                    Internet
                       │
                       ▼
                    nginx (:80)         ← public entrypoint
                    │         │
                    ▼         ▼
               React SPA   /api → FastAPI
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
                 PostgreSQL          Redis
               (internal only)    (internal only)
                                     │
                                     ▼
                               Media Worker
                                     │
                                     ▼
                              Cloudflare R2
```

## Prerequisites

- Docker and Docker Compose v2+
- A production PostgreSQL database (or use the Docker container)
- A production Redis instance (or use the Docker container)
- Cloudflare R2 bucket for media storage
- A domain name with DNS configured
- (Optional) Cloudflare proxy for TLS

---

## First Deployment

### 1. Configure Environment

```bash
cp .env.production.example .env.production
```

Edit `.env.production` with real values. **Every required field must be set.**

The backend will **refuse to start** if production configuration is insecure.

### 2. Configure Operator Credentials

```bash
cp .env.operator.example .env.operator.local
```

Fill in admin and host test credentials. This file is **gitignored** and never committed.

### 3. Configure Cloudflare R2 (Production Storage)

For production, media is stored in Cloudflare R2 (S3-compatible object storage).

1. **Create an R2 bucket** in the Cloudflare Dashboard → R2 Object Storage
2. **Create an R2 API token** with read/write permissions for the bucket
3. **Add to `.env.production`:**

```env
STORAGE_PROVIDER=r2
R2_ACCESS_KEY_ID=your_access_key_id
R2_SECRET_ACCESS_KEY=your_secret_access_key
R2_ENDPOINT=https://your_account_id.r2.cloudflarestorage.com
R2_BUCKET_NAME=your_bucket_name
```

The backend will **fail to start** if `STORAGE_PROVIDER=r2` but R2 credentials are missing.

For local development, use `STORAGE_PROVIDER=local` (no R2 needed).

### 4. Start the Docker Stack

```bash
docker compose --env-file .env.production up -d --build
```

This starts:
- **frontend** (nginx) — public entrypoint on port 80
- **backend** (FastAPI) — API server
- **worker** (media processing) — background jobs
- **postgres** (PostgreSQL 16) — internal only
- **redis** (Redis 7) — internal only

### 5. Run Database Migrations

```bash
docker compose exec backend alembic upgrade head
```

This is a **separate step**. The application does not run migrations automatically.

### 6. Verify Health

```bash
# Liveness (is the app running?)
curl http://localhost/api/health

# Readiness (can it serve requests?)
curl http://localhost/api/health/ready
```

Expected response:
```json
{
  "status": "ok",
  "dependencies": {
    "postgres": "connected",
    "redis": "connected"
  }
}
```

### 7. Create Admin Account

If this is a fresh database, you need to create an admin user. Connect to the backend container and use the application's user creation mechanism, or insert directly via Alembic/SQL.

### 8. Configure DNS

Point your domain to the server running Docker Compose.

If using **Cloudflare** (recommended):
1. Add your domain to Cloudflare
2. Set DNS A record pointing to your server IP
3. Enable Cloudflare proxy (orange cloud)
4. Set SSL/TLS mode to "Full" or "Full (Strict)"

If using **Let's Encrypt** directly:
1. Install certbot on the host
2. Obtain certificates: `certbot certonly --webroot -w /var/www/html -d your-domain.com`
3. Uncomment the HTTPS server block in `nginx.conf`
4. Rebuild: `docker compose --env-file .env.production up -d --build`

### 9. Verify the Application

1. Open `http://your-domain.com` — should show the Lentis landing page
2. Open `http://your-domain.com/admin` — should show admin login
3. Log in with admin credentials
4. Create a test event
5. Open the public event link
6. Test guest upload
7. Verify QR code works

---

## Updating an Existing Deployment

### Safe Update Sequence

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild images
docker compose --env-file .env.production build

# 3. Run any new migrations
docker compose exec backend alembic upgrade head

# 4. Restart services (rolling restart)
docker compose --env-file .env.production up -d

# 5. Verify health
curl http://localhost/api/health/ready
```

### Rollback

If something goes wrong:

```bash
# Check which image was previously running
docker compose images

# Roll back to a specific image tag (if using tags)
# Or revert the code and rebuild
git checkout <previous-commit>
docker compose --env-file .env.production up -d --build
```

**Database rollback**: If a migration needs to be reversed:
```bash
docker compose exec backend alembic downgrade -1
```

---

## Credential Locations

| Credential | Location | Notes |
|-----------|----------|-------|
| Admin login | `.env.operator.local` → ADMIN_EMAIL/PASSWORD | Local-only, gitignored |
| Host login | `.env.operator.local` → HOST_EMAIL/PASSWORD | Local-only, gitignored |
| JWT secret | `.env.production` → JWT_SECRET_KEY | Must be >= 32 chars |
| App secret | `.env.production` → SECRET_KEY | Must be >= 32 chars |
| Database | `.env.production` → POSTGRES_PASSWORD, DATABASE_URL | PostgreSQL container |
| Redis | `.env.production` → REDIS_PASSWORD, REDIS_URL | Redis container |
| R2 storage | `.env.production` → R2_* | Cloudflare R2 |
| Frontend URL | `.env.production` → FRONTEND_URL, VITE_PUBLIC_URL | Public domain(s) |

---

## Important Commands

```bash
# Start the stack
docker compose --env-file .env.production up -d --build

# Stop the stack
docker compose down

# View logs
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Run migrations
docker compose exec backend alembic upgrade head

# Open a shell in the backend
docker compose exec backend bash

# Check health
curl http://localhost/api/health
curl http://localhost/api/health/ready

# Restart a specific service
docker compose restart backend
docker compose restart worker
```

---

## Environment Variables Reference

### Required in Production

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Must be `production` | `production` |
| `JWT_SECRET_KEY` | JWT signing secret (>= 32 chars) | *(generated)* |
| `SECRET_KEY` | Application secret (>= 32 chars) | *(generated)* |
| `POSTGRES_PASSWORD` | PostgreSQL password | *(strong password)* |
| `REDIS_PASSWORD` | Redis password | *(strong password)* |
| `FRONTEND_URL` | CORS allowed origins (HTTPS) | `https://your-domain.com` |
| `VITE_PUBLIC_URL` | Public URL for guest event links | `https://lentisevent.gallery` |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key | *(from R2 dashboard)* |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key | *(from R2 dashboard)* |
| `R2_ENDPOINT` | R2 API endpoint | `https://xxx.r2.cloudflarestorage.com` |

### Optional (have sane defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_PROVIDER` | `r2` | `r2` or `local` |
| `ENABLE_DOCS` | `false` | Enable /docs endpoint |
| `RATE_LIMIT_GUEST_REGISTRATION` | `10` | Per IP per hour |
| `RATE_LIMIT_EVENT_MEDIA_UPLOAD` | `30` | Per event per IP per hour |
| `MAX_REQUEST_BODY_BYTES` | `629145600` | 600 MB |

---

## Camera & HTTPS Requirements

The camera capture feature requires a **secure context** (HTTPS) on most browsers:

- **iPhone Safari**: Requires HTTPS for camera access
- **Android Chrome**: Requires HTTPS for camera access
- **Desktop browsers**: May work on localhost for development

### Production Requirements

1. **HTTPS must be configured** — Camera will not work over plain HTTP
2. **Cloudflare recommended** — Handles TLS termination at the edge
3. **VITE_PUBLIC_URL must match** — Set to your HTTPS domain
4. **FRONTEND_URL must match** — Set to your HTTPS domain for CORS

### Development

- `localhost` is considered a secure context by browsers
- Camera should work on `http://localhost:5173` during development
- If camera doesn't work, check browser console for security errors

---

## Security Notes

- The backend runs as a **non-root** user inside its container
- PostgreSQL and Redis are **never exposed** to the host
- The backend is only reachable through nginx
- All secrets come from environment variables — never from source code
- `.env.operator.local` is **gitignored** and never committed
- Production startup **rejects** insecure defaults (weak JWT secret, localhost database, etc.)
- Rate limiting is applied to public guest endpoints
- API documentation is **disabled** by default in production
