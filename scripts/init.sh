#!/usr/bin/env bash
# Crée la base "soleymada", installe les modules, charge les données (long : lancer avec nohup si SCALE=1.0)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

docker compose up -d db
sleep 8

echo ">>> 1/3 Installation d'Odoo ${ODOO_VERSION} + modules"
docker compose run --rm odoo odoo -d "$DB_NAME" \
  -i base,contacts,sale_management,account,purchase,fleet,crm,soley_logistics \
  --without-demo=all --load-language=fr_FR --stop-after-init

echo ">>> 2/3 Chargement des données (clients, commandes, factures, paiements)"
docker compose run --rm -T odoo odoo shell -d "$DB_NAME" --no-http < scripts/seed_odoo.py

echo ">>> 3/3 Démarrage"
docker compose up -d odoo
echo "Terminé -> http://localhost:8069  (login: admin / mot de passe: $ADMIN_PASSWORD)"
