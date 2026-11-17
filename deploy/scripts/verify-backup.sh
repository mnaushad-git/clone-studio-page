#!/usr/bin/env bash
# Proves a backup restores, without touching any running stack: restores both databases
# into a throwaway PostgreSQL container with no network, reports row counts, and checks the
# archives. Compare the counts with the source before trusting the backup.
#
#   deploy/scripts/verify-backup.sh <backup-directory>
set -euo pipefail

DIR="${1:?usage: verify-backup.sh <backup-directory>}"
[[ -f "$DIR/SHA256SUMS" ]] || { echo "not a backup directory: $DIR" >&2; exit 2; }
(cd "$DIR" && sha256sum --quiet -c SHA256SUMS)

NAME="tb-restore-verify-$$"
trap 'docker rm -f "$NAME" > /dev/null 2>&1 || true' EXIT
docker run -d --name "$NAME" --network none -e POSTGRES_HOST_AUTH_METHOD=trust postgres:16 > /dev/null

for _ in $(seq 1 60); do
  docker exec "$NAME" pg_isready -h 127.0.0.1 -U postgres > /dev/null 2>&1 && break
  sleep 1
done

sql() { docker exec -i "$NAME" psql -U postgres -v ON_ERROR_STOP=1 -At -d "$1" -c "$2"; }

for db in app odoo; do
  sql postgres "CREATE DATABASE restored_$db"
  docker exec -i "$NAME" pg_restore -U postgres -d "restored_$db" --no-owner --no-privileges --exit-on-error < "$DIR/$db.dump"
done

# Assigned first, not inside echo: a failed query then stops the script under set -e
# instead of printing an empty count and still reporting success.
products=$(sql restored_app 'select count(*) from catalogue_products')
variants=$(sql restored_app 'select count(*) from catalogue_product_variants')
orders=$(sql restored_app 'select count(*) from orders')
outbox=$(sql restored_app 'select count(*) from order_outbox_events')
odoo_templates=$(sql restored_odoo 'select count(*) from product_template')
odoo_variants=$(sql restored_odoo 'select count(*) from product_product')
odoo_sale_orders=$(sql restored_odoo 'select count(*) from sale_order')
echo "app:  products=$products variants=$variants orders=$orders outbox=$outbox"
echo "odoo: templates=$odoo_templates variants=$odoo_variants sale_orders=$odoo_sale_orders"
[[ "$products" -gt 0 ]] || { echo "restored application database has no products" >&2; exit 1; }
echo "odoo filestore files: $(tar -tzf "$DIR/odoo-filestore.tar.gz" | grep -vc '/$')"
echo "media files: $(tar -tzf "$DIR/media.tar.gz" | grep -vc '/$')"
echo "restore verification passed: $DIR"
