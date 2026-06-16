#!/bin/bash
set -euo pipefail

# Configurações
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_NAME="${DB_NAME:-quizapp}"
DB_USER="${DB_USER:-quizapp}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting backup of ${DB_NAME}@${DB_HOST}:${DB_PORT}"

if [ -n "${PGPASSWORD:-}" ]; then
    export PGPASSWORD
fi

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_FILE"

echo "[backup] Backup saved: ${BACKUP_FILE}"
echo "[backup] Size: $(du -h "$BACKUP_FILE" | cut -f1)"

# Limpeza — remove backups mais antigos que RETENTION_DAYS
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -delete
echo "[backup] Removed backups older than ${RETENTION_DAYS} days"

# Log do resultado
echo "[backup] Backup completed: $(date)"
