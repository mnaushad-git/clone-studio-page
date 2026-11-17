# Native integration stack (no Docker)

Runs the real integration on this Windows machine from the PostgreSQL, Odoo 19 and Memurai
binaries already installed. Everything is separate from the shared services:

| | Shared, never touched | This stack |
|---|---|---|
| PostgreSQL | `postgresql-x64-16` on 5432 | Own data directory on 55440 |
| Odoo | `odoo-server-19.0` on 8069, database `terrific_dev` | Own process on 18069, database `terrific_odoo` |
| Redis | Memurai on 6379 | Own Memurai on 16379 |
| API, frontend | None | 18020 (demo API 18021), 18081 |

A separate cluster is used because the shared Odoo has an empty `dbfilter`, so its cron threads
would also run against any new database created in the shared PostgreSQL.

All state, generated passwords and logs live in `.local-integration/`, which is git-ignored.
Stop the stack and delete that folder to start again from nothing.

## Run it

From the repository root, with `S="backend/.venv/Scripts/python deploy/native/native_stack.py"`:

```bash
$S up                                   # first run takes about 5 minutes
$S run --role migrate -- python -m app.scripts.seed_catalogue --apply
$S run --role catalogue_import -- python -m app.scripts.import_odoo_catalogue --validate
$S run --role catalogue_import -- python -m app.scripts.import_odoo_catalogue \
    --apply --confirm-import --output "$PWD/.local-integration/import-apply.json"
$S app --stage local_integration        # API, worker, Beat, frontend
$S verify                               # Odoo integration checks
$S verify-financials                    # storefront and Odoo totals, VAT and delivery lines
$S verify-prices --label x --sync 3     # every variant in Odoo, PostgreSQL and the API
$S browser                              # headless customer and admin journey
$S test -- -q                           # backend test suite, on its own database
$S stop all
```

Always pass `--output` to the importer. Without it, `--plan` and `--reconcile` overwrite tracked
reports in `data/odoo/`.

`verify` and `browser` place new orders each time, so both can be repeated. So can the import:
each imported category, product and attribute carries a `tb_import_key` with a `UNIQUE` index
(from the `terrific_order_sync` addon). A create that timed out but committed is found by that
key and adopted on the next run, and one still committing can't produce a second copy.

To prove the timeout path on an empty catalogue:

```bash
$S run --role catalogue_import -- python "$PWD/deploy/native/verify_import_idempotency.py" apply-with-timeout
$S run --role catalogue_import -- python -m app.scripts.import_odoo_catalogue     --apply --confirm-import --output "$PWD/.local-integration/import-rerun.json"
```

If the cluster on 55440 crashes and can't be restarted, for example because an orphaned PostgreSQL
child still holds the port, build a clean one beside it without touching the old one. Set these
for every command:

```bash
export TB_NATIVE_STATE="$PWD/.local-integration/<new-folder>" TB_NATIVE_PG_PORT=55441
```

## What `verify` proves

| Area | Check |
|---|---|
| Catalogue | 26 templates and 55 variants in Odoo and PostgreSQL, all mapped, and a worker sync completes |
| Least privilege | The order sync user is not an administrator and can't create products or external IDs |
| Orders | A paid order reaches a confirmed `sale.order` through the real worker |
| Duplicates | Re-delivered events reuse the order, 8 raw concurrent creates commit once, 6 concurrent pushes agree on one order, the key can't be copied or changed |
| Retries | An unsyncable order retries, dead-letters at the limit, and an operator retry syncs it |
| Downtime | With Odoo stopped the API still takes orders and sync shows `failed`, then recovers with one order |
| Demo | Demo orders from a demo API are marked `simulated` by the live worker and never reach Odoo |

`verify-financials` is described in
[odoo-order-financials.md](../integrations/odoo-order-financials.md).

## Credentials

Each process receives only what its job needs. See `role_env` in `native_stack.py` and the
matching `SERVICE_ROLE` values in the compose files.

| Process | Odoo login |
|---|---|
| API, Beat, migrations | None, and `Settings` refuses to start if one is present |
| Worker | `terrific-order-sync`: sales user and partner creation |
| Catalogue import (one-off) | `terrific-catalogue-import`: products, plus external IDs under `terrific_bites` only |

The live order pusher also refuses any account holding Odoo administrator rights.

## Order idempotency

The `terrific_order_sync` addon in `deploy/odoo/addons` adds `sale.order.tb_order_key` with a
PostgreSQL `UNIQUE` index. Every create sets it to the storefront order number, so at most one
sale order can ever commit per order, whatever workers or timeouts do. The pusher refuses to
create anything if the addon isn't installed, because the lookup on the unknown field fails first.

The addon must be installed on any Odoo that receives orders. The shared `terrific_dev` database
doesn't have it.
