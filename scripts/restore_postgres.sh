#!/bin/bash
set -euo pipefail

# Configurações
BACKUP_FILE="${1:-}"
DB_NAME="${DB_NAME:-quizapp}"
DB_USER="${DB_USER:-quizapp}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <arquivo_backup.sql.gz>"
    echo "Exemplo: $0 ./backups/quizapp_20260101_120000.sql.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[restore] Arquivo não encontrado: ${BACKUP_FILE}"
    exit 1
fi

echo "[restore] Restoring ${DB_NAME}@${DB_HOST}:${DB_PORT} from ${BACKUP_FILE}"

if [ -n "${PGPASSWORD:-}" ]; then
    export PGPASSWORD
fi

# Confirmação
echo "[restore] AVISO: Isso irá SUBSTITUIR o banco de dados ${DB_NAME}!"
read -p "[restore] Continuar? (s/N): " confirm
if [ "$confirm" != "s" ] && [ "$confirm" != "S" ]; then
    echo "[restore] Cancelado."
    exit 0
fi

# Mata conexões ativas e recria o banco
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '${DB_NAME}'
  AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${DB_NAME};
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
SQL

# Restaura
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    "$BACKUP_FILE"

echo "[restore] Restore completed: $(date)"
