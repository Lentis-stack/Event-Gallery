# Lentis Gallery — Production Readiness Checklist

## Infrastructure

| Item | Status | Evidence |
|------|--------|----------|
| Docker Compose config validates | [VERIFIED] | `yaml.safe_load()` parseable; 5 required vars enforced via `?` syntax |
| Backend Dockerfile builds (multi-stage) | [NOT VERIFIED] | Docker not available in test environment |
| Frontend Dockerfile builds (multi-stage) | [NOT VERIFIED] | Docker not available in test environment |
| Backend runs as non-root (lentis user) | [VERIFIED] | `USER lentis` in Dockerfile; `groupadd` + `useradd` present |
| Frontend serves from nginx | [VERIFIED] | `FROM nginx:1.27-alpine`; health check present |
| nginx proxies /api/ to backend | [VERIFIED] | `upstream backend { server backend:8000; }`; `proxy_pass http://backend` |
| WebSocket support in nginx | [VERIFIED] | `Upgrade` and `Connection` headers configured in `/api/ws/` location |
| PostgreSQL not exposed to host | [VERIFIED] | No `ports:` on postgres service; only `lentis-internal` network |
| Redis not exposed to host | [VERIFIED] | No `ports:` on redis service; only `lentis-internal` network |
| Backend not publicly exposed | [VERIFIED] | No `ports:` on backend service; nginx proxies to it |
| Only nginx (port 80) publicly exposed | [VERIFIED] | Single `ports: "${LISTEN_PORT:-80}:80"` on frontend service |
| Redis authentication required | [VERIFIED] | `--requirepass ${REDIS_PASSWORD}` in redis command |
| PostgreSQL credentials externalized | [VERIFIED] | `POSTGRES_PASSWORD` required via `?` syntax |
| Named volumes for persistence | [VERIFIED] | `postgres_data` and `redis_data` named volumes |
| Health checks on all services | [VERIFIED] | postgres: `pg_isready`; redis: `redis-cli ping`; backend: `curl /api/health`; frontend: `wget` |
| Worker service for media processing | [VERIFIED] | Separate `worker` service in docker-compose.yml |
| No secrets in Docker images | [VERIFIED] | Grep of Dockerfiles shows 0 matches for SECRET_KEY/password/JWT/R2 |
| `.env` files not copied into images | [VERIFIED] | `.dockerignore` excludes `.env*` |
| `.git` not copied into images | [VERIFIED] | `.dockerignore` excludes `.git` |
| No `--reload` in production | [VERIFIED] | CMD uses `uvicorn --workers 2` without `--reload` |
| Runtime env injection for VITE_PUBLIC_URL | [VERIFIED] | `docker-entrypoint.sh` sed-replaces placeholder in built JS |
| Gzip compression enabled | [VERIFIED] | `gzip on;` in nginx.conf |
| nginx body size limit | [VERIFIED] | `client_max_body_size 600m;` in nginx.conf |
| Rate limiting in nginx | [VERIFIED] | `limit_req_zone` for guest_register and guest_upload |

## Security

| Item | Status | Evidence |
|------|--------|----------|
| JWT secret validation (production) | [VERIFIED] | `test_production_config.py`: 3 tests for default/short/empty secret rejection |
| SECRET_KEY validation (production) | [VERIFIED] | `test_production_config.py`: rejects "change-me" in production |
| Database credential validation (production) | [VERIFIED] | `test_production_config.py`: rejects localhost default in production |
| Redis URL validation (production) | [VERIFIED] | `test_production_config.py`: rejects localhost default in production |
| CORS validation (production) | [VERIFIED] | `test_production_config.py`: rejects wildcard `*` in production |
| R2 credential validation (production) | [VERIFIED] | `test_production_config.py`: rejects missing credentials with `STORAGE_PROVIDER=r2` |
| Guest registration rate limiting | [VERIFIED] | Code review: `check_guest_registration_rate_limit()` in guests route |
| Media upload rate limiting | [VERIFIED] | Code review: `check_media_upload_rate_limit()` in media route |
| Login rate limiting | [VERIFIED] | Code review: `check_login_rate_limit()` in auth service |
| API docs disabled by default | [VERIFIED] | `ENABLE_DOCS: bool = False` in config; `docs_url` set to None when disabled |
| CORS no wildcards in production | [VERIFIED] | `validate_frontend_url` raises ValueError for `*` in production |
| Secure cookies (HttpOnly, SameSite, Secure) | [VERIFIED] | `httponly=True, samesite="lax", secure=not is_dev` in auth.py |
| CSP headers | [VERIFIED] | `SecurityHeadersMiddleware` in main.py |
| X-Content-Type-Options | [VERIFIED] | Set in both FastAPI middleware and nginx.conf |
| X-Frame-Options DENY | [VERIFIED] | Set in both FastAPI middleware and nginx.conf |
| HSTS in production | [VERIFIED] | `Strict-Transport-Security: max-age=31536000` when ENVIRONMENT=production |
| Request body size limit | [VERIFIED] | `MAX_REQUEST_BODY_BYTES` middleware + nginx `client_max_body_size` |
| create_all() removed from startup | [VERIFIED] | `app/main.py` lifespan only logs, no `Base.metadata.create_all()` |
| Password policy (>= 10 chars) | [VERIFIED] | `validate_password_strength` in security.py; login schema `min_length=10` |
| No passwords in API responses | [VERIFIED] | `SafeUserOut` excludes `password_hash`; verified in schemas |
| No XSS vectors (dangerouslySetInnerHTML) | [VERIFIED] | Grep of `src/` returns 0 matches |
| No SQL injection (f-strings in queries) | [VERIFIED] | Grep of SQLAlchemy queries with f-strings returns 0 matches |
| FFmpeg subprocess safety (no shell=True) | [VERIFIED] | `video.py` uses argument arrays; `shell=True` never used |
| Path traversal protection | [VERIFIED] | `file_path.resolve().startswith(base_path)` check in media serving |
| Image decompression bomb protection | [VERIFIED] | `MAX_IMAGE_PIXELS` check in `process_image()` |
| No secrets in frontend bundle | [VERIFIED] | Grep of `dist/` shows only legitimate form field names |
| No secrets in git-tracked files | [VERIFIED] | Only comments reference "password" and "secret" |
| `.env.operator.local` gitignored | [VERIFIED] | `git check-ignore` confirms |
| `.env.production` gitignored | [VERIFIED] | `git check-ignore` confirms |

## Database

| Item | Status | Evidence |
|------|--------|----------|
| Migrations chain is complete | [VERIFIED] | 8 migrations, each with correct `down_revision` |
| Schema managed by Alembic only | [VERIFIED] | No `create_all()` in app startup |
| Performance indexes exist | [VERIFIED] | `h0i1j2k3l4m5` migration adds `ix_media_processing_status`, `ix_media_event_role_status`, `ix_media_event_status_created` |
| Media role index | [VERIFIED] | `g7h8i9j0k1l2` migration adds `ix_media_event_role_position` |
| Storage accounting atomic | [VERIFIED] | Phase 4: `Event.storage_used_bytes = Event.storage_used_bytes + N` SQL |

## Media

| Item | Status | Evidence |
|------|--------|----------|
| Image processing (Pillow) | [VERIFIED] | `processors/image.py`: optimized + thumbnail generation |
| Video processing (FFmpeg) | [VERIFIED] | `processors/video.py`: optimized MP4 + poster frame |
| Background worker (Redis Queue) | [VERIFIED] | `workers/media_worker.py` |
| Media roles (HERO/SLIDESHOW/GALLERY) | [VERIFIED] | Phase 3: `MediaRole` enum in model |
| Slideshow ordering (position) | [VERIFIED] | Phase 3: `position` column on media table |
| Guest upload → PENDING status | [VERIFIED] | Phase 3: guest uploads created with `MediaStatus.PENDING` |
| Host approve/reject | [VERIFIED] | Phase 3: `host_approve_media()`, `host_reject_media()` |
| Storage limit enforcement | [VERIFIED] | Phase 4: atomic check with `storage_used_bytes >= file_size` guard |
| Media cleanup utility | [VERIFIED] | `services/media_cleanup.py`: orphan detection, stale processing reset |

## Observability

| Item | Status | Evidence |
|------|--------|----------|
| Liveness endpoint | [VERIFIED] | `GET /api/health` returns `{"status": "ok", "uptime_seconds": ...}` |
| Readiness endpoint | [VERIFIED] | `GET /api/health/ready` checks PG + Redis; returns 503 if degraded |
| Structured request logging | [VERIFIED] | `RequestLoggingMiddleware`: method, path, status, duration_ms, user_type, IP |
| Audit trail for mutations | [VERIFIED] | POST/PUT/PATCH/DELETE logged at INFO level |
| Slow request detection | [VERIFIED] | Requests > 5000ms logged at WARNING |
| No secrets in logs | [VERIFIED] | Log entries use `user_type` not tokens; no JWT/secret/password logging |
| Error logging (no stack traces to client) | [VERIFIED] | `logger.error()` for operators; generic messages for clients |

## Deployment

| Item | Status | Evidence |
|------|--------|----------|
| `.env.production.example` complete | [VERIFIED] | Documents all required/optional variables |
| `.env.operator.example` (safe template) | [VERIFIED] | Placeholders only, no real values |
| `.env.operator.local` (gitignored) | [VERIFIED] | `git check-ignore` confirms |
| Production startup rejects insecure config | [VERIFIED] | 12 tests in `test_production_config.py` |
| Alembic migration is separate step | [VERIFIED] | Documented in `PRODUCTION_DEPLOYMENT.md` |
| Domain configurable via env vars | [VERIFIED] | `FRONTEND_URL`, `VITE_PUBLIC_URL` |
| No hardcoded production URLs | [VERIFIED] | `getPublicBaseUrl()` uses runtime injection |

## Recovery

| Item | Status | Evidence |
|------|--------|----------|
| PostgreSQL backup documented | [BLOCKED] | No pg_dump test possible (no PG in test env) |
| PostgreSQL restore documented | [BLOCKED] | No restore test possible |
| R2 recovery | [BLOCKED] | No R2 in test env |
| Redis loss tolerance | [VERIFIED] | Redis is cache/queue only; PostgreSQL is source of truth |
| Rollback procedure documented | [VERIFIED] | `PRODUCTION_DEPLOYMENT.md` documents rollback steps |
| Guest session cleanup | [VERIFIED] | `cleanup_expired_guest_sessions()` in `media_cleanup.py` |
| Media cleanup for orphaned objects | [VERIFIED] | `find_broken_media_records()`, `cleanup_broken_processing()` |

## Test Results

| Test Suite | Status | Evidence |
|-----------|--------|----------|
| Frontend TypeScript compilation | [VERIFIED] | `npx tsc --noEmit` — exit 0, no errors |
| Frontend production build | [VERIFIED] | `npx vite build` — 431 modules, 7.08s, no warnings |
| Backend imports | [VERIFIED] | 38 routes loaded successfully |
| Backend test suite (auth/guests/events/config) | [VERIFIED] | 92 passed, 18 warnings |
| No secrets in frontend bundle | [VERIFIED] | Grep of dist/ shows only form field names |
| No XSS in frontend source | [VERIFIED] | 0 matches for dangerouslySetInnerHTML |
| No SQL injection | [VERIFIED] | 0 f-string SQL queries; all queries use parameterized SQLAlchemy |
| No shell injection | [VERIFIED] | subprocess.run with argument arrays only |

## Summary

- **VERIFIED**: 62 items
- **NOT VERIFIED**: 2 items (Docker image builds — Docker unavailable)
- **BLOCKED**: 3 items (PostgreSQL backup/restore, R2 recovery — infrastructure unavailable)
- **0 ISSUES FOUND** during this validation
