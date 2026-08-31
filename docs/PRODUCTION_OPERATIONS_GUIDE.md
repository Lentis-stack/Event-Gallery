# Lentis Gallery — Production Operations Guide

## 1. Starting Production

```bash
docker compose --env-file .env.production up -d --build
```

## 2. Stopping Production

```bash
docker compose --env-file .env.production down
```

Data persists in Docker volumes (`postgres_data`, `redis_data`, `shared_storage`, `lentis_backups`).

## 3. Restarting Services

```bash
# Restart all services
docker compose --env-file .env.production restart

# Restart a specific service
docker compose --env-file .env.production restart backend
docker compose --env-file .env.production restart worker
docker compose --env-file .env.production restart frontend

# Restart with rebuild (after code changes)
docker compose --env-file .env.production up -d --build backend
```

## 4. Checking Health

```bash
# Health (is the app running?)
curl http://localhost/api/health
# Expected: {"status":"ok","app":"Lentis Gallery API","uptime_seconds":...}

# Readiness (can it serve requests?)
curl http://localhost/api/health/ready
# Expected: {"status":"ok","dependencies":{"postgres":"connected","redis":"connected"}}

# Container status
docker compose --env-file .env.production ps

# Docker health status
docker inspect --format='{{.Name}} {{.State.Health.Status}}' $(docker ps -q)
```

## 5. Reading Logs

```bash
# All services
docker compose --env-file .env.production logs

# Follow a specific service
docker compose --env-file .env.production logs -f backend
docker compose --env-file .env.production logs -f worker
docker compose --env-file .env.production logs -f frontend
docker compose --env-file .env.production logs -f postgres
docker compose --env-file .env.production logs -f redis
docker compose --env-file .env.production logs -f backup

# Last 100 lines
docker compose --env-file .env.production logs --tail=100 backend

# Since a specific time
docker compose --env-file .env.production logs --since=30m backend
```

## 6. Running Migrations

```bash
# Run all pending migrations
docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app alembic upgrade head'

# Check current migration
docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app alembic current'

# Check migration history
docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app alembic history'

# Rollback one migration (CAUTION)
docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app alembic downgrade -1'
```

## 7. Creating Backups

```bash
# Manual backup
docker exec gall-backup-1 /scripts/backup_postgres.sh

# List backups
docker exec gall-backup-1 ls -la /backups/

# Verify backup integrity
docker exec gall-backup-1 gunzip -t /backups/lentis_YYYY-MM-DD_HH-MM-SS.sql.gz
```

## 8. Restoring Backups

```bash
# Stop writes (backend and worker)
docker compose stop backend worker

# Restore (will prompt for confirmation — type RESTORE)
docker compose run --rm backup /scripts/restore_postgres.sh /backups/lentis_YYYY-MM-DD_HH-MM-SS.sql.gz

# Run migrations if needed
docker compose run --rm backend sh -c 'cd /app && PYTHONPATH=/app alembic upgrade head'

# Restart services
docker compose up -d backend worker
```

## 9. Rotating Secrets

### JWT Secret

1. Generate new secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. Update `.env.production`:
   ```
   JWT_SECRET_KEY=<new_secret>
   ```

3. Restart backend and worker:
   ```bash
   docker compose --env-file .env.production restart backend worker
   ```

4. **Warning:** All existing JWT tokens will be invalidated. Users must re-login.

### Application Secret

1. Generate new secret:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. Update `.env.production`:
   ```
   SECRET_KEY=<new_secret>
   ```

3. Restart backend and worker.

### Database Password

1. Update password in PostgreSQL:
   ```bash
   docker compose exec postgres psql -U lentis -c "ALTER USER lentis PASSWORD 'new_password';"
   ```

2. Update `.env.production`:
   ```
   POSTGRES_PASSWORD=new_password
   DATABASE_URL=postgresql+psycopg://lentis:new_password@postgres:5432/lentis_gallery
   REDIS_URL=redis://:new_password@redis:6379/0
   ```

3. Restart all services:
   ```bash
   docker compose --env-file .env.production up -d
   ```

### Redis Password

1. Update in `.env.production`:
   ```
   REDIS_PASSWORD=new_password
   REDIS_URL=redis://:new_password@redis:6379/0
   ```

2. Restart Redis and services that use it:
   ```bash
   docker compose --env-file .env.production up -d
   ```

### R2 Credentials

1. Generate new R2 API token in Cloudflare Dashboard.
2. Update `.env.production` with new `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY`.
3. Restart backend and worker:
   ```bash
   docker compose --env-file .env.production restart backend worker
   ```

## 10. Updating Application

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild and restart
docker compose --env-file .env.production up -d --build

# 3. Run migrations
docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app alembic upgrade head'

# 4. Verify health
curl http://localhost/api/health/ready
```

## 11. Recovering from Failed Worker

```bash
# Check worker logs
docker compose --env-file .env.production logs --tail=50 worker

# Restart worker
docker compose --env-file .env.production restart worker

# Check if pending jobs exist
docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app python3 -c "
from app.db.session import SessionLocal
from app.models.media import Media, MediaStatus
db = SessionLocal()
pending = db.query(Media).filter(Media.status == MediaStatus.PENDING).count()
print(f\"Pending media: {pending}\")
db.close()
"'
```

## 12. Recovering from Database Failure

```bash
# Check PostgreSQL health
docker compose exec postgres pg_isready

# Check PostgreSQL logs
docker compose --env-file .env.production logs --tail=50 postgres

# If PostgreSQL won't start, check volume
docker volume inspect gall_postgres_data

# Restore from backup (see Section 8)
```

## 13. Recovering from Redis Failure

```bash
# Check Redis health
docker compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Check Redis logs
docker compose --env-file .env.production logs --tail=50 redis

# Restart Redis
docker compose --env-file .env.production restart redis

# Note: Rate limiting state is lost. Processing queue may need manual check.
```

## 14. R2 Credential Rotation

1. Log in to Cloudflare Dashboard.
2. Go to R2 → Manage R2 API Tokens.
3. Create a new token with read/write permissions.
4. Copy the new Access Key ID and Secret Access Key.
5. Update `.env.production`:
   ```
   R2_ACCESS_KEY_ID=<new_key>
   R2_SECRET_ACCESS_KEY=<new_secret>
   ```
6. Restart backend and worker:
   ```bash
   docker compose --env-file .env.production restart backend worker
   ```
7. Verify media upload works.
8. Optionally revoke the old token.

## 15. Incident Response Basics

### Application Down

1. Check: `docker compose --env-file .env.production ps`
2. Check logs: `docker compose --env-file .env.production logs`
3. Restart failed services
4. Check health: `curl http://localhost/api/health/ready`

### Database Connection Lost

1. Check PostgreSQL: `docker compose exec postgres pg_isready`
2. Check logs: `docker compose --env-file .env.production logs postgres`
3. Restart PostgreSQL: `docker compose restart postgres`
4. If data corruption: restore from backup

### High Error Rate

1. Check backend logs: `docker compose --env-file .env.production logs -f backend`
2. Check nginx logs: `docker compose --env-file .env.production logs frontend`
3. Check worker: `docker compose --env-file .env.production logs -f worker`
4. Look for: connection failures, OOM, disk space

### Security Incident

1. Check for unauthorized access in logs
2. Rotate all secrets (JWT, application, database, Redis, R2)
3. Review authentication logs
4. Consider revoking all guest sessions
5. Update `.env.production` and restart
