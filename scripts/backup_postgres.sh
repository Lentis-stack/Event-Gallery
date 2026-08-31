#!/bin/bash
# ============================================================
# Lentis Gallery — PostgreSQL Backup Script
# ============================================================
# Performs a compressed pg_dump of the Lentis Gallery database.
# Designed to run inside a Docker container on a cron schedule.
#
# Required environment variables:
#   POSTGRES_HOST     — PostgreSQL hostname (default: postgres)
#   POSTGRES_PORT     — PostgreSQL port (default: 5432)
#   POSTGRES_DB       — Database name
#   POSTGRES_USER     — Database user
#   POSTGRES_PASSWORD — Database password
#
# Optional environment variables:
#   BACKUP_DIR        — Where to write backups (default: /backups)
#   BACKUP_RETENTION_DAYS — Days to keep backups (default: 7)
#
# Exit codes:
#   0 — Backup succeeded
#   1 — Backup failed (missing env, pg_dump error, etc.)
# ============================================================

set -euo pipefail

# ---- Configuration ----
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:?POSTGRES_DB is required}"
POSTGRES_USER="${POSTGRES_USER:?POSTGRES_USER is required}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

# ---- Derived ----
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/lentis_${TIMESTAMP}.sql.gz"
LOG_PREFIX="[backup ${TIMESTAMP}]"

# ---- Helper functions ----
log() {
    echo "${LOG_PREFIX} $*"
}

fail() {
    echo "${LOG_PREFIX} ERROR: $*" >&2
    exit 1
}

# ---- Validate environment ----
log "Starting PostgreSQL backup"

if ! command -v pg_dump >/dev/null 2>&1; then
    fail "pg_dump not found. Install postgresql-client."
fi

if [ -z "${POSTGRES_PASSWORD}" ]; then
    fail "POSTGRES_PASSWORD is empty"
fi

# ---- Create backup directory ----
mkdir -p "${BACKUP_DIR}" || fail "Cannot create backup directory: ${BACKUP_DIR}"

# ---- Run pg_dump ----
log "Dumping database '${POSTGRES_DB}' from ${POSTGRES_HOST}:${POSTGRES_PORT}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

pg_dump \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --format=custom \
    --compress=6 \
    --verbose \
    --no-owner \
    --no-privileges \
    2>/dev/null \
    | gzip > "${BACKUP_FILE}"

DUMP_EXIT=${PIPESTATUS[0]}

if [ ${DUMP_EXIT} -ne 0 ]; then
    rm -f "${BACKUP_FILE}"
    fail "pg_dump failed with exit code ${DUMP_EXIT}"
fi

if [ ! -s "${BACKUP_FILE}" ]; then
    rm -f "${BACKUP_FILE}"
    fail "Backup file is empty"
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# ---- Cleanup old backups ----
log "Removing backups older than ${BACKUP_RETENTION_DAYS} days"

DELETED_COUNT=0
find "${BACKUP_DIR}" -name "lentis_*.sql.gz" -type f -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete 2>/dev/null | while read -r OLD_FILE; do
    log "Deleted old backup: $(basename "${OLD_FILE}")"
    DELETED_COUNT=$((DELETED_COUNT + 1))
done

REMAINING=$(find "${BACKUP_DIR}" -name "lentis_*.sql.gz" -type f | wc -l)
log "Retention cleanup complete. ${REMAINING} backup(s) remaining."

# ---- Verify backup integrity ----
log "Verifying backup integrity"

if gunzip -t "${BACKUP_FILE}" 2>/dev/null; then
    log "Backup integrity check: PASSED"
else
    fail "Backup integrity check: FAILED — file may be corrupted"
fi

# ---- Summary ----
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
log "Backup complete successfully"
log "  File: ${BACKUP_FILE}"
log "  Size: ${BACKUP_SIZE}"
log "  Total backup directory: ${TOTAL_SIZE}"
log "  Retention: ${BACKUP_RETENTION_DAYS} days"
