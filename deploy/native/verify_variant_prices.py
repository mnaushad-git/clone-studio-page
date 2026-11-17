#!/usr/bin/env python3
"""Proves every variant sells at its approved price in Odoo, PostgreSQL and the public API.

Run through `native_stack.py verify-prices [--label NAME] [--sync N]`. With --sync it first runs
N full catalogue syncs through the real worker. Exit code 1 if any price disagrees.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from app.services.catalogue.variant_pricing import (
    expected_variant_prices,
    load_canonical_products,
    to_money,
)
from app.workers.celery_app import celery_app
from sqlalchemy import create_engine, text

STATE = Path(os.environ["TB_NATIVE_STATE_DIR"])
API = "http://127.0.0.1:18020/api/v1/catalogue/products"
ODOO_URL = os.environ["ODOO_BASE_URL"] + "/jsonrpc"
DB, LOGIN, PASSWORD = (os.environ[k] for k in ("ODOO_DATABASE", "ODOO_USERNAME", "ODOO_PASSWORD"))
SYNC_TASK = "app.workers.tasks.catalogue_sync.sync_catalogue_from_odoo"
EXPECTED_PRODUCTS = 26
EXPECTED_VARIANTS = 55
EXPECTED_WITH_DELTA = 28
ACCEPTANCE_SKU = "TB-CHO-009-LARGEBOX"
ACCEPTANCE_PRICE = Decimal("14.38")

engine = create_engine(os.environ["DATABASE_URL"])


def rpc(service: str, method: str, args: list[Any]) -> Any:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
    }
    reply = httpx.post(ODOO_URL, json=body, timeout=60).json()
    if reply.get("error"):
        raise SystemExit(f"Odoo error: {reply['error']}")
    return reply["result"]


def odoo_prices() -> dict[str, Decimal]:
    uid = rpc("common", "authenticate", [DB, LOGIN, PASSWORD, {}])
    rows = rpc(
        "object",
        "execute_kw",
        [
            DB,
            uid,
            PASSWORD,
            "product.product",
            "search_read",
            [[["type", "=", "consu"]]],
            {"fields": ["default_code", "lst_price"]},
        ],
    )
    return {row["default_code"]: to_money(row["lst_price"]) for row in rows if row["default_code"]}


def postgres_prices() -> dict[str, Decimal]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "select v.sku, p.amount from catalogue_product_variants v "
                "join catalogue_product_prices p on p.product_variant_id = v.id "
                "where p.active and p.currency = 'SAR'"
            )
        ).all()
    return {sku: to_money(amount) for sku, amount in rows}


def api_prices(slugs: list[str]) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    with httpx.Client(timeout=30) as http:
        for slug in slugs:
            response = http.get(f"{API}/{slug}")
            response.raise_for_status()
            for variant in response.json()["variants"]:
                prices[variant["sku"]] = to_money(variant["price"])
    return prices


def run_syncs(times: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    query = text(
        "select id, status, counts_by_entity_json, error_summary from odoo_catalogue_sync_runs "
        "where trigger = 'MANUAL' and initiated_by = 'verify-prices' and status <> 'RUNNING' "
        "order by started_at desc limit 1"
    )
    for _ in range(times):
        with engine.connect() as conn:
            before = conn.execute(query).first()
        celery_app.send_task(
            SYNC_TASK,
            kwargs={"full_resync": True, "trigger": "MANUAL", "initiated_by": "verify-prices"},
        )
        deadline = time.monotonic() + 420
        latest = before
        while time.monotonic() < deadline:
            with engine.connect() as conn:
                latest = conn.execute(query).first()
            if latest is not None and (before is None or latest.id != before.id):
                break
            time.sleep(3)
        else:
            raise SystemExit("Timed out waiting for the worker to finish a catalogue sync")
        price_counts = (latest.counts_by_entity_json or {}).get("PRODUCT_PRICE")
        runs.append(
            {"status": latest.status, "prices": price_counts, "error": latest.error_summary}
        )
        print(f"sync: {latest.status} prices={price_counts}", flush=True)
    return runs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="check")
    parser.add_argument("--sync", type=int, default=0)
    args = parser.parse_args()

    sync_runs = run_syncs(args.sync)

    products = load_canonical_products()
    bases = {p["name_en"]: to_money(p["sales_price"]) for p in products}
    expected = expected_variant_prices(products)
    odoo, postgres, api = odoo_prices(), postgres_prices(), api_prices([p["slug"] for p in products])

    rows = [
        {
            "product": item.product_name,
            "variant": item.variant_label,
            "sku": item.sku,
            "base": str(bases[item.product_name]),
            "expected": str(item.amount),
            "odoo": str(odoo.get(item.sku)),
            "postgres": str(postgres.get(item.sku)),
            "api": str(api.get(item.sku)),
            "ok": odoo.get(item.sku) == postgres.get(item.sku) == api.get(item.sku) == item.amount,
        }
        for item in expected
    ]
    with_delta = [row for row in rows if row["expected"] != row["base"]]
    bad = [row for row in rows if not row["ok"]]
    acceptance = next(row for row in rows if row["sku"] == ACCEPTANCE_SKU)
    shape_ok = (
        len(products) == EXPECTED_PRODUCTS
        and len(rows) == EXPECTED_VARIANTS
        and len(with_delta) == EXPECTED_WITH_DELTA
    )
    sync_ok = all(run["status"] == "SUCCEEDED" for run in sync_runs)
    ok = shape_ok and sync_ok and not bad and acceptance["expected"] == str(ACCEPTANCE_PRICE)

    report = {
        "label": args.label,
        "products": len(products),
        "variants": len(rows),
        "variants_with_size_price": len(with_delta),
        "variants_matching_everywhere": len(rows) - len(bad),
        "acceptance": acceptance,
        "sync_runs": sync_runs,
        "mismatches": bad,
        "rows": rows,
        "ok": ok,
    }
    (STATE / f"price-evidence-{args.label}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    for row in bad:
        print(
            f"MISMATCH {row['product']} / {row['variant']} [{row['sku']}]: expected "
            f"{row['expected']}, odoo {row['odoo']}, postgres {row['postgres']}, api {row['api']}"
        )
    print(
        f"{args.label}: {len(products)} products, {len(rows)} variants, "
        f"{len(with_delta)} with a size price, {len(rows) - len(bad)} match everywhere. "
        f"{acceptance['variant']} of {acceptance['product']}: odoo {acceptance['odoo']}, "
        f"postgres {acceptance['postgres']}, api {acceptance['api']}. "
        f"{'PASS' if ok else 'FAIL'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
