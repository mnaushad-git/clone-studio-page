#!/usr/bin/env bash
# Entry point for every Odoo container in this project. Renders the config from the
# environment, waits for PostgreSQL, then runs odoo with whatever arguments it was given.
set -euo pipefail

: "${ODOO_DB_PASSWORD:?}"
: "${ODOO_ADMIN_PASSWD:?}"
DB_HOST="${ODOO_DB_HOST:?}"

python3 - "$DB_HOST" <<'PY'
import os, sys
text = open("/etc/terrific/odoo.conf.template").read()
for key, value in {
    "__DB_HOST__": sys.argv[1],
    "__DB_PASSWORD__": os.environ["ODOO_DB_PASSWORD"],
    "__ADMIN_PASSWD__": os.environ["ODOO_ADMIN_PASSWD"],
}.items():
    text = text.replace(key, value)
fd = os.open("/tmp/odoo.conf", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as handle:
    handle.write(text)
PY

/usr/local/bin/wait-for-psql.py --db_host "$DB_HOST" --db_port 5432 \
  --db_user terrific_odoo --db_password "$ODOO_DB_PASSWORD" --timeout 60

# Odoo only recognises a subcommand when it is the first argument.
if [[ "${1:-}" == "shell" ]]; then
  shift
  exec odoo shell -c /tmp/odoo.conf "$@"
fi
exec odoo -c /tmp/odoo.conf "$@"
