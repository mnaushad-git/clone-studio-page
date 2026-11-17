#!/usr/bin/env python3
"""Proves storefront and Odoo agree on money, with real orders through the real worker.

Each scenario places an order through the API, pays it, waits for the Celery worker to push
it, then reads the confirmed sale order back from Odoo and compares every figure. Run through
`native_stack.py verify-financials`. Adds new orders each run, so it can be repeated.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from app.integrations.odoo.order_reconciliation import to_cents
from app.workers.celery_app import celery_app
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / ".local-integration" / "financial-results.json"
API = "http://127.0.0.1:18020"
PUSH_TASK = "app.workers.tasks.order_sync.push_paid_orders_to_odoo"
VAT_RATE = Decimal(15)

ODOO_URL = os.environ["ODOO_BASE_URL"] + "/jsonrpc"
DB, LOGIN, PASSWORD = (
    os.environ[k] for k in ("ODOO_DATABASE", "ODOO_USERNAME", "ODOO_PASSWORD")
)
engine = create_engine(os.environ["DATABASE_URL"])
http = httpx.Client(timeout=30)
checks: list[dict[str, Any]] = []
rows: list[dict[str, Any]] = []


def check(name: str, ok: bool, detail: object = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def rpc(service: str, method: str, args: list[Any]) -> Any:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
    }
    response = httpx.post(ODOO_URL, json=body, timeout=30).json()
    if "error" in response:
        raise RuntimeError(response["error"]["data"]["message"])
    return response["result"]


UID = rpc("common", "authenticate", [DB, LOGIN, PASSWORD, {}])


def odoo(model: str, method: str, args: list[Any], **kwargs: Any) -> Any:
    return rpc("object", "execute_kw", [DB, UID, PASSWORD, model, method, args, kwargs])


def sql(statement: str, **params: Any) -> list[Any]:
    with engine.begin() as connection:
        result = connection.execute(text(statement), params)
        return list(result.mappings()) if result.returns_rows else []


def admin_client() -> httpx.Client:
    client = httpx.Client(base_url=API, timeout=30)
    client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": os.environ["NATIVE_ADMIN_EMAIL"],
            "password": os.environ["NATIVE_ADMIN_PASSWORD"],
        },
    ).raise_for_status()
    client.headers["X-CSRF-Token"] = client.cookies["admin_csrf"]
    return client


def catalogue() -> list[dict[str, Any]]:
    body = http.get(
        f"{API}/api/v1/catalogue/products", params={"page_size": 100}
    ).json()
    summaries = body.get("items") or body.get("data") or body
    return [
        http.get(f"{API}/api/v1/catalogue/products/{p['slug']}").json()
        for p in summaries
    ]


def item_for(
    product: dict[str, Any], variant: dict[str, Any], **extra: Any
) -> dict[str, Any]:
    attributes = {a["code"]: a["value_label_en"] for a in variant["attributes"]}
    return {"product_slug": product["slug"], "attributes": attributes, **extra}


def create_order(
    items: list[dict[str, Any]], promo: str | None = None
) -> dict[str, Any]:
    payload = {
        "items": items,
        "promo_code": promo,
        "customer": {
            "name": "Financial Verify",
            "email": "finance-verify@example.test",
            "phone": f"+9665{uuid.uuid4().int % 100000000:08d}",
        },
        "delivery": {
            "is_gift": False,
            "recipient_name": "Financial Verify",
            "recipient_phone": "+966500000000",
            "area": "Al Olaya",
            "address": "1 Verification Street",
            "delivery_date": "Tomorrow",
            "delivery_time": "10:00am - 12:00pm",
        },
    }
    response = http.post(f"{API}/api/v1/orders", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"order rejected: {response.status_code} {response.text}")
    return response.json()


def pay(order: dict[str, Any]) -> None:
    http.post(
        f"{API}/api/v1/orders/{order['id']}/pay",
        json={"method_label": "Financial verify"},
    ).raise_for_status()


def order_state(order_id: str) -> dict[str, Any]:
    return dict(
        sql(
            "select o.odoo_sync_status, o.odoo_sale_order_id, e.status event_status, e.attempts, "
            "e.last_error from orders o join order_outbox_events e on e.order_id = o.id "
            "where o.id = :id and e.event_type = 'order.paid'",
            id=order_id,
        )[0]
    )


def wait_for(order_id: str, ready: Any, timeout: float = 150) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = order_state(order_id)
        if ready(state):
            return state
        celery_app.send_task(PUSH_TASK)
        time.sleep(3)
    return order_state(order_id)


def read_sale_order(sale_order_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    order = odoo(
        "sale.order",
        "read",
        [[sale_order_id]],
        fields=[
            "name",
            "state",
            "currency_id",
            "pricelist_id",
            "amount_untaxed",
            "amount_tax",
            "amount_total",
            "order_line",
        ],
    )[0]
    lines = odoo(
        "sale.order.line",
        "read",
        [order["order_line"]],
        fields=[
            "name",
            "product_id",
            "product_uom_qty",
            "price_unit",
            "price_total",
            "price_tax",
            "tax_ids",
        ],
    )
    return order, lines


def is_delivery(line: dict[str, Any]) -> bool:
    return line["name"] == "Delivery"


def run_scenario(
    label: str, items: list[dict[str, Any]], promo: str | None = None
) -> dict[str, Any]:
    print(f"\n--- {label}", flush=True)
    order = create_order(items, promo)
    pay(order)
    state = wait_for(order["id"], lambda s: s["odoo_sync_status"] == "synced")
    check(
        f"[{label}] worker synced the order",
        state["odoo_sync_status"] == "synced",
        state,
    )
    if state["odoo_sync_status"] != "synced":
        return order

    so, lines = read_sale_order(state["odoo_sale_order_id"])
    expected_total = to_cents(order["total_amount"])
    expected_tax = to_cents(order["tax_amount"])
    delivery_fee = to_cents(order["delivery_fee_amount"])
    discount = to_cents(order["discount_amount"])

    check(f"[{label}] sale order confirmed", so["state"] == "sale", so["name"])
    check(
        f"[{label}] currency is SAR",
        so["currency_id"][1] == "SAR",
        so["currency_id"][1],
    )
    check(
        f"[{label}] pricelist is SAR",
        so["pricelist_id"] and "SAR" in so["pricelist_id"][1],
        so["pricelist_id"],
    )
    check(
        f"[{label}] total matches",
        to_cents(so["amount_total"]) == expected_total,
        f"storefront {expected_total}, Odoo {so['amount_total']}",
    )
    check(
        f"[{label}] VAT matches",
        to_cents(so["amount_tax"]) == expected_tax,
        f"storefront {expected_tax}, Odoo {so['amount_tax']}",
    )
    check(
        f"[{label}] net plus VAT equals total",
        to_cents(so["amount_untaxed"]) + to_cents(so["amount_tax"])
        == to_cents(so["amount_total"]),
        f"{so['amount_untaxed']} + {so['amount_tax']}",
    )
    # 15% inclusive: the VAT is 15/115 of the gross, to the cent.
    check(
        f"[{label}] VAT is 15% included, not added on top",
        to_cents(expected_total * VAT_RATE / (Decimal(100) + VAT_RATE)) == expected_tax,
        f"{expected_total} x 15/115",
    )

    delivery_lines = [line for line in lines if is_delivery(line)]
    if delivery_fee > 0:
        check(
            f"[{label}] one delivery line at the fee",
            len(delivery_lines) == 1
            and to_cents(delivery_lines[0]["price_total"]) == delivery_fee,
            delivery_lines and delivery_lines[0]["price_total"],
        )
        check(
            f"[{label}] delivery line carries the VAT",
            bool(delivery_lines and delivery_lines[0]["tax_ids"]),
            delivery_lines and delivery_lines[0]["price_tax"],
        )
    else:
        check(
            f"[{label}] no delivery line for a free delivery",
            not delivery_lines,
            delivery_lines,
        )

    product_lines = [
        line for line in lines if not is_delivery(line) and line["price_unit"] > 0
    ]
    check(
        f"[{label}] product lines match the order",
        sorted((to_cents(i["unit_price"]), i["quantity"]) for i in order["items"])
        == sorted(
            (to_cents(line["price_unit"]), int(line["product_uom_qty"]))
            for line in product_lines
        ),
        [(line["product_uom_qty"], line["price_unit"]) for line in product_lines],
    )
    if discount > 0:
        discount_lines = [line for line in lines if line["price_unit"] < 0]
        check(
            f"[{label}] one negative discount line",
            len(discount_lines) == 1
            and to_cents(-discount_lines[0]["price_total"]) == discount,
            discount_lines and discount_lines[0]["price_total"],
        )
    for item in order["items"]:
        if item.get("inscription"):
            check(
                f"[{label}] inscription reaches Odoo",
                any(item["inscription"] in line["name"] for line in lines),
                item["inscription"],
            )

    rows.append(
        {
            "scenario": label,
            "storefront_order": order["order_number"],
            "odoo_order": so["name"],
            "currency": so["currency_id"][1],
            "storefront": {
                "subtotal": order["subtotal_amount"],
                "discount": order["discount_amount"],
                "delivery": order["delivery_fee_amount"],
                "vat": order["tax_amount"],
                "total": order["total_amount"],
            },
            "odoo": {
                "untaxed": so["amount_untaxed"],
                "vat": so["amount_tax"],
                "total": so["amount_total"],
            },
            "lines": [
                {
                    "name": line["name"].split("\n")[0],
                    "qty": line["product_uom_qty"],
                    "unit_price": line["price_unit"],
                    "vat": line["price_tax"],
                    "gross": line["price_total"],
                }
                for line in lines
            ],
        }
    )
    return order


def verify_fail_safe(product: dict[str, Any], variant: dict[str, Any]) -> None:
    """A VAT disagreement must leave the sale order unconfirmed, and be recoverable."""
    print("\n--- fail-safe: storefront and Odoo disagree", flush=True)
    order = create_order([item_for(product, variant, quantity=1)])
    real_tax = order["tax_amount"]
    sql("update orders set tax_amount = tax_amount + 1 where id = :id", id=order["id"])
    pay(order)
    state = wait_for(order["id"], lambda s: s["attempts"] >= 1)
    check(
        "[fail-safe] push is reported failed",
        state["odoo_sync_status"] == "failed",
        state,
    )
    check(
        "[fail-safe] the reason names the VAT difference",
        "order_reconciliation_failed" in (state["last_error"] or "")
        and "VAT" in (state["last_error"] or ""),
        state["last_error"],
    )
    found = odoo(
        "sale.order",
        "search_read",
        [[["tb_order_key", "=", order["order_number"]]]],
        fields=["state"],
    )
    check("[fail-safe] exactly one sale order exists", len(found) == 1, found)
    check(
        "[fail-safe] it stays in draft",
        bool(found) and found[0]["state"] == "draft",
        found,
    )

    sql(
        "update orders set tax_amount = :tax where id = :id",
        id=order["id"],
        tax=real_tax,
    )
    sql(
        "update order_outbox_events set status='pending', next_attempt_at=null "
        "where order_id=:id and event_type='order.paid'",
        id=order["id"],
    )
    state = wait_for(order["id"], lambda s: s["odoo_sync_status"] == "synced")
    check(
        "[fail-safe] corrected order then syncs",
        state["odoo_sync_status"] == "synced",
        state,
    )
    final = odoo(
        "sale.order",
        "search_read",
        [[["tb_order_key", "=", order["order_number"]]]],
        fields=["state"],
    )
    check(
        "[fail-safe] no second order, now confirmed",
        final and final[0]["state"] == "sale",
        final,
    )


def verify_no_double_tax_on_invoice_totals() -> None:
    """Every SAR order this script confirmed still equals what the storefront charged."""
    mismatched = [
        r
        for r in rows
        if to_cents(r["storefront"]["total"]) != to_cents(r["odoo"]["total"])
        or to_cents(r["storefront"]["vat"]) != to_cents(r["odoo"]["vat"])
    ]
    check(
        "all scenarios reconcile",
        not mismatched and len(rows) > 0,
        f"{len(rows)} orders",
    )


def main() -> int:
    # An inscription can be Arabic, which the Windows console's default encoding can't print.
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    products = catalogue()
    with_variants = [
        p for p in products if len([v for v in p["variants"] if v.get("price")]) >= 2
    ]
    plain = sorted(
        (p for p in products if p["variants"] and p["variants"][0].get("price")),
        key=lambda p: Decimal(p["variants"][0]["price"]),
    )
    cheapest = plain[0]
    dearest = plain[-1]
    parent = next(iter(with_variants))
    variants = [v for v in parent["variants"] if v.get("price")]
    settings_rows = sql(
        "select flat_delivery_fee, free_delivery_threshold, minimum_order_amount "
        "from delivery_settings limit 1"
    )
    original = dict(settings_rows[0])
    print("delivery settings:", original, flush=True)

    code = f"V{uuid.uuid4().hex[:6].upper()}"
    fixed = f"F{uuid.uuid4().hex[:6].upper()}"
    admin = admin_client()
    for promo, kind, value in ((code, "PERCENTAGE", 10), (fixed, "FIXED_AMOUNT", 17.5)):
        admin.post(
            "/api/v1/admin/promo-codes",
            json={
                "code": promo,
                "discount_type": kind,
                "discount_value": value,
                "minimum_order_amount": 0,
                "is_active": True,
            },
        ).raise_for_status()

    # A clean baseline: delivery charged, minimum order out of the way, no free-delivery rule.
    sql(
        "update delivery_settings set flat_delivery_fee = 15, free_delivery_threshold = 0, "
        "minimum_order_amount = 0"
    )
    try:
        cheap_variant = cheapest["variants"][0]
        run_scenario(
            "single item, delivery charged",
            [item_for(dearest, dearest["variants"][0], quantity=1)],
        )
        run_scenario(
            "multiple quantities with inscription",
            [
                item_for(
                    cheapest,
                    cheap_variant,
                    quantity=7,
                    inscription="Happy Birthday سارة",
                )
            ],
        )
        run_scenario(
            "mixed variants of one product",
            [
                item_for(parent, variants[0], quantity=2),
                item_for(parent, variants[1], quantity=3),
                item_for(cheapest, cheap_variant, quantity=1),
            ],
        )
        run_scenario(
            "percentage discount, odd amounts",
            [
                item_for(parent, variants[0], quantity=3),
                item_for(cheapest, cheap_variant, quantity=11),
            ],
            promo=code,
        )
        run_scenario(
            "fixed discount with delivery",
            [item_for(dearest, dearest["variants"][0], quantity=2)],
            promo=fixed,
        )
        sql("update delivery_settings set free_delivery_threshold = 1")
        run_scenario(
            "zero delivery fee",
            [item_for(dearest, dearest["variants"][0], quantity=1)],
        )
        run_scenario(
            "zero delivery with discount",
            [
                item_for(parent, variants[1], quantity=2),
                item_for(cheapest, cheap_variant, quantity=4),
            ],
            promo=code,
        )
        sql("update delivery_settings set free_delivery_threshold = 0")
        for quantity in (1, 3, 9):
            run_scenario(
                f"rounding stress, quantity {quantity}",
                [
                    item_for(cheapest, cheap_variant, quantity=quantity),
                    item_for(parent, variants[-1], quantity=quantity),
                ],
            )
        verify_no_double_tax_on_invoice_totals()
        verify_fail_safe(cheapest, cheap_variant)
    finally:
        sql(
            "update delivery_settings set flat_delivery_fee = :f, free_delivery_threshold = :t, "
            "minimum_order_amount = :m",
            f=original["flat_delivery_fee"],
            t=original["free_delivery_threshold"],
            m=original["minimum_order_amount"],
        )

    failed = [c for c in checks if not c["ok"]]
    print(f"\nSUMMARY {len(checks) - len(failed)}/{len(checks)} passed")
    print(
        f"{'scenario':38} {'storefront':>11} {'odoo':>11} {'SF VAT':>9} {'Odoo VAT':>9} {'cur':>4}"
    )
    for row in rows:
        print(
            f"{row['scenario']:38} {row['storefront']['total']:>11} "
            f"{row['odoo']['total']:>11.2f} {row['storefront']['vat']:>9} "
            f"{row['odoo']['vat']:>9.2f} {row['currency']:>4}"
        )
    RESULTS.write_text(
        json.dumps({"checks": checks, "orders": rows}, indent=1, default=str),
        encoding="utf-8",
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
