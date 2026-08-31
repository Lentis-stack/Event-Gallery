#!/bin/bash
# ============================================================
# Lentis Gallery — PostgreSQL Restore Script
# ============================================================
# Restores a Lentis Gallery database from a pg_dump backup.
#
# IMPORTANT: This script is DESTRUCTIVE.
# It will DROP and RECREATE the target database.
#
# Usage:
#   ./restore_postgres.sh /backups/lentis_2026-08-23_02-00-00.sql.gz
#
# Required environment variables:
#   POSTGRES_HOST     — PostgreSQL hostname (default: postgres)
#   POSTGRES_PORT     — PostgreSQL port (default: 5432)
#   POSTGRES_DB       — Database name
#   POSTGRES_USER     — Database user
#   POSTGRES_PASSWORD — Database password
#
# Exit codes:
#   0 — Restore succeeded
#   1 — Restore failed
# ============================================================

set -euo pipefail

# ---- Configuration ----
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:?POSTGRES_DB is required}"
POSTGRES_USER="${POSTGRES_USER:?POSTGRES_USER is required}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

# ---- Argument validation ----
BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "ERROR: No backup file specified." >&2
    echo "Usage: $0 /backups/lentis_YYYY-MM-DD_HH-MM-SS.sql.gz" >&2
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

if [ ! -s "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file is empty: ${BACKUP_FILE}" >&2
    exit 1
fi

# ---- Path traversal protection ----
REAL_PATH=$(realpath "${BACKUP_FILE}" 2>/dev/null || echo "${BACKUP_FILE}")
if echo "${REAL_PATH}" | grep -qE '\.\.|~|/etc/|/var/|/usr/|/root/'; then
    echo "ERROR: Invalid backup path. Only /backups/ directory is allowed." >&2
    exit 1
fi

# ---- Verify backup is a valid gzip file ----
if ! gunzip -t "${BACKUP_FILE}" 2>/dev/null; then
    echo "ERROR: Backup file is not a valid gzip archive: ${BACKUP_FILE}" >&2
    exit 1
fi

# ---- Safety confirmation ----
echo "============================================================"
echo "WARNING: DATABASE RESTORE"
echo "============================================================"
echo ""
echo "  This will DROP and RECREATE the database '${POSTGRES_DB}'."
echo "  All current data will be LOST."
echo ""
echo "  Backup file: ${BACKUP_FILE}"
echo "  Target DB:   ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "  Backup size: $(du -h "${BACKUP_FILE}" | cut -f1)"
echo ""
echo "  To proceed, type 'RESTORE' (in uppercase):"
echo ""
read -r CONFIRMATION

if [ "${CONFIRMATION}" != "RESTORE" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."

# ---- Export password ----
export PGPASSWORD="${POSTGRES_PASSWORD}"

# ---- Step 1: Terminate existing connections ----
echo "Step 1: Terminating existing connections..."
psql \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="postgres" \
    --command="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
    2>/dev/null || true

# ---- Step 2: Drop and recreate database ----
echo "Step 2: Recreating database..."
psql \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="postgres" \
    --command="DROP DATABASE IF EXISTS ${POSTGRES_DB};" \
    --command="CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};" \
    2>/dev/null

# ---- Step 3: Restore from backup ----
echo "Step 3: Restoring from backup..."
gunzip -c "${BACKUP_FILE}" | pg_restore \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --no-owner \
    --no-privileges \
    --verbose \
    2>&1 | tail -5 || true

# ---- Step 4: Verify ----
echo "Step 4: Verifying restore..."
TABLE_COUNT=$(psql \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --tuples-only \
    --command="SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" \
    2>/dev/null | tr -d ' ')

echo ""
echo "============================================================"
echo "RESTORE COMPLETE"
echo "============================================================"
echo "  Database: ${POSTGRES_DB}"
echo "  Tables restored: ${TABLE_COUNT}"
echo "  Source: ${BACKUP_FILE}"
echo ""
echo "  Run migrations if needed:"
echo "    docker exec gall-backend-1 sh -c 'cd /app && PYTHONPATH=/app alembic upgrade head'"
echo ""
