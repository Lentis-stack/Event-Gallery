# Lentis Gallery — Backup and Recovery Guide

## Overview

Lentis Gallery includes an automated PostgreSQL backup system that runs as a dedicated Docker service.

### Architecture

```
backup service (cron)
       │
       ▼
  PostgreSQL (internal)
       │
       ▼
  /backups volume (persistent)
       │
       ▼
  lentis_YYYY-MM-DD_HH-MM-SS.sql.gz
```

The backup service:
- Runs independently from the backend and worker
- Uses PostgreSQL's `pg_dump` for reliable backups
- Compresses backups with gzip
- Automatically removes backups older than the configured retention period
- Does not expose any ports
- Does not require root access

---

## Automatic Backups

The backup service runs on a cron schedule inside the Docker Compose stack.

### Default Schedule

Daily at 02:00 UTC.

Configurable via `BACKUP_SCHEDULE` in `.env.production`:

```env
BACKUP_SCHEDULE=0 2 * * *
```

### Backup Naming

```
lentis_2026-08-23_02-00-00.sql.gz
```

All timestamps are UTC.

### Retention Policy

Backups older than `BACKUP_RETENTION_DAYS` are automatically deleted.

Default: 7 days.

Configurable in `.env.production`:

```env
BACKUP_RETENTION_DAYS=7
```

---

## Manual Backup

### Using Docker Compose

```bash
# Execute the backup script inside the running backup container
docker compose exec backup /scripts/backup_postgres.sh
```

### Running a one-off backup (without the scheduled service)

```bash
# Run backup directly using the postgres image
docker compose exec -T postgres pg_dump \
    -U ${POSTGRES_USER:-lentis} \
    -d ${POSTGRES_DB:-lentis_gallery} \
    --format=custom \
    --compress=6 \
    | gzip > "lentis_$(date -u +%Y-%m-%d_%H-%M-%S).sql.gz"
```

---

## Verify Backup

### Check backup file exists and is non-empty

```bash
docker compose exec backup ls -la /backups/lentis_*.sql.gz
```

### Check backup integrity

```bash
docker compose exec backup gunzip -t /backups/lentis_YYYY-MM-DD_HH-MM-SS.sql.gz
```

A zero exit code means the file is valid.

### Check backup size

```bash
docker compose exec backup du -h /backups/lentis_*.sql.gz
```

A typical backup for a small-to-medium Lentis instance is 10-100 KB.

---

## List Backups

```bash
# List all backups with sizes and dates
docker compose exec backup ls -lht /backups/lentis_*.sql.gz
```

---

## Restore Procedure

**WARNING: Restoring overwrites the current database. All existing data is lost.**

### Step 1: Stop the backend and worker (prevent writes during restore)

```bash
docker compose stop backend worker
```

### Step 2: Run the restore script

```bash
# The script will ask for confirmation before proceeding
docker compose run --rm backup /scripts/restore_postgres.sh /backups/lentis_YYYY-MM-DD_HH-MM-SS.sql.gz
```

You must type `RESTORE` to confirm.

### Step 3: Run migrations (if the backup is from an older schema version)

```bash
docker compose run --rm backend sh -c 'cd /app && PYTHONPATH=/app alembic upgrade head'
```

### Step 4: Restart services

```bash
docker compose up -d backend worker
```

### Step 5: Verify

```bash
# Health check
curl http://localhost/api/health

# Verify event data exists
curl http://localhost/api/admin/events -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Disaster Recovery Procedure

If the database is completely lost:

### 1. Stop all services

```bash
docker compose down
```

### 2. Start only PostgreSQL and backup service

```bash
docker compose up -d postgres
```

Wait for PostgreSQL to be healthy:

```bash
docker compose exec postgres pg_isready
```

### 3. Restore from the most recent backup

Find the latest backup:

```bash
docker compose run --rm \
    -v lentis_backups:/backups \
    postgres ls -lt /backups/lentis_*.sql.gz | head -1
```

Restore:

```bash
docker compose run --rm \
    -v lentis_backups:/backups \
    --env-file .env.production \
    postgres /scripts/restore_postgres.sh /backups/lentis_MOST_RECENT.sql.gz
```

### 4. Start all services

```bash
docker compose --env-file .env.production up -d
```

### 5. Run migrations

```bash
docker compose exec backend sh -c 'cd /app && PYTHONPATH=/app alembic upgrade head'
```

### 6. Verify

```bash
curl http://localhost/api/health/ready
```

---

## Backup Failure Troubleshooting

### Backup fails with "pg_dump: error: connection to server failed"

- PostgreSQL may not be accepting connections.
- Check PostgreSQL health: `docker compose exec postgres pg_isready`
- Verify credentials in `.env.production`.

### Backup file is empty (0 bytes)

- The database may be empty, or pg_dump failed silently.
- Check backup service logs: `docker compose logs backup`
- Verify PostgreSQL has data: `docker compose exec postgres psql -U lentis -d lentis_gallery -c "\dt"`

### Backup fails with "FATAL: password authentication failed"

- Verify `POSTGRES_PASSWORD` is set correctly in `.env.production`.
- The backup service uses the same password as the backend.

### Disk space exhausted

- Check available space on the Docker volume.
- Reduce `BACKUP_RETENTION_DAYS` to keep fewer backups.
- Manually remove old backups: `docker compose exec backup rm /backups/lentis_OLD*.sql.gz`

### Backup service not running

```bash
# Check status
docker compose ps backup

# Check logs
docker compose logs backup

# Restart
docker compose restart backup
```

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_SCHEDULE` | `0 2 * * *` | Cron schedule (UTC) |
| `BACKUP_RETENTION_DAYS` | `7` | Days to keep backups |
| `BACKUP_DIR` | `/backups` | Backup directory inside container |

These variables are configured in `.env.production`.

---

## Important Notes

1. **Backups contain sensitive data.** The backup files include hashed passwords and all event data. Store them securely.

2. **R2 media is NOT included in PostgreSQL backups.** Media files are stored in Cloudflare R2. Database backups only include metadata (file paths, sizes, processing status). To restore media, you must also restore from R2.

3. **Backups use `pg_dump --format=custom`** for efficient compression and reliable restoration.

4. **The backup service is independent** from the backend. It can run backups even if the backend is down (as long as PostgreSQL is healthy).

5. **Test your backups regularly.** Restore into a test database to verify backup integrity.
