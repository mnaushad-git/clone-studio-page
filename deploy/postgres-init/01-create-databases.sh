#!/usr/bin/env bash
# Runs once, when the PostgreSQL volume is first initialised. Creates two isolated
# databases on one server, each owned by its own non-superuser role. Odoo 19 supports
# PostgreSQL 13 and later, so both can share the postgres:16 server.
set -euo pipefail

: "${APP_DB_PASSWORD:?}"
: "${ODOO_DB_PASSWORD:?}"

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
  -v app_pw="$APP_DB_PASSWORD" -v odoo_pw="$ODOO_DB_PASSWORD" <<'SQL'
CREATE ROLE terrific_bites LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_pw';
CREATE DATABASE terrific_bites OWNER terrific_bites ENCODING 'UTF8' TEMPLATE template0;
REVOKE ALL ON DATABASE terrific_bites FROM PUBLIC;

CREATE ROLE terrific_odoo LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'odoo_pw';
-- LC_COLLATE C is what Odoo itself uses when it creates a database.
CREATE DATABASE terrific_odoo OWNER terrific_odoo ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C.UTF-8' TEMPLATE template0;
REVOKE ALL ON DATABASE terrific_odoo FROM PUBLIC;
SQL
