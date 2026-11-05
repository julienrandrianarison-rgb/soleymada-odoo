#!/usr/bin/env bash
# Sauvegarde .zip (dump SQL + filestore), restaurable via le menu "Gestionnaire de bases" d'Odoo
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
OUT="backups/${DB_NAME}_$(date +%F_%H%M).zip"
curl -sS -X POST -F "master_pwd=${MASTER_PASSWORD}" -F "name=${DB_NAME}" -F "backup_format=zip" \
     -o "$OUT" http://localhost:8069/web/database/backup
echo "Sauvegarde écrite : $OUT ($(du -h "$OUT" | cut -f1))"
